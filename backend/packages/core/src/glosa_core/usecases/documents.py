from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Sequence

from ..authorization import Permission
from ..context import RequestContext
from ..domain import (
    Document,
    DocumentStatus,
    DocumentVersion,
    Job,
    JobStatus,
    JobType,
    Outcome,
)
from ..errors import CapacityExceeded, InvalidRequest, NotFound
from ..kernel import Kernel
from ..ports import CollectionRepository, DocumentRepository, JobQueue, TextExtractor
from .base import UseCase


@dataclass(frozen=True)
class SubmitResult:
    document_id: str
    version: int | None
    job: Job | None
    unchanged: bool
    correlation_id: str


class SubmitDocument(UseCase):
    """Sube un documento nuevo o una versión nueva de uno existente. Siempre se encola."""

    action = "document.submit"

    def __init__(
        self,
        kernel: Kernel,
        collections: CollectionRepository,
        documents: DocumentRepository,
        queue: JobQueue,
        extractors: Sequence[TextExtractor],
        max_attempts: int = 5,
    ) -> None:
        super().__init__(kernel)
        self._collections = collections
        self._documents = documents
        self._queue = queue
        self._extractors = extractors
        self._max_attempts = max_attempts

    def execute(
        self,
        ctx: RequestContext,
        collection_id: str,
        *,
        title: str,
        source_type: str,
        content: bytes,
        document_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> SubmitResult:
        started = self.k.clock.now()
        self._require(ctx, collection_id, Permission.SUBMIT_DOCUMENT, self.action)

        with self._guard(ctx, self.action, collection_id, started):
            collection = self._collections.get(collection_id)
            if collection is None:
                raise NotFound("Colección no encontrada")
            settings = collection.settings

            # 1. Idempotencia: la misma clave devuelve el mismo trabajo, sin duplicar nada
            if idempotency_key:
                existing = self._queue.find_by_key(collection_id, idempotency_key)
                if existing is not None:
                    self.k.recorder.record(
                        ctx,
                        self.action,
                        Outcome.SUCCEEDED,
                        collection_id=collection_id,
                        target={"document_id": existing.target, "job_id": existing.id},
                        details={"deduplicated": True},
                        started=started,
                    )
                    return SubmitResult(
                        existing.target, existing.version, existing, False, ctx.correlation_id
                    )

            # 2. Validación y límites
            if not (title or "").strip():
                raise InvalidRequest("El documento necesita un título")
            if not content:
                raise InvalidRequest("El documento está vacío")
            if len(content) > settings.max_file_mb * 1024 * 1024:
                raise CapacityExceeded(f"El archivo supera {settings.max_file_mb} MB")
            if not any(e.supports(source_type) for e in self._extractors):
                raise InvalidRequest(f"Tipo de documento no soportado: {source_type}")
            queued = self._queue.list(
                collection_id, JobStatus.QUEUED.value, settings.max_queue_per_collection + 1
            )
            if len(queued) >= settings.max_queue_per_collection:
                raise CapacityExceeded("La cola de la colección está llena")

            content_hash = hashlib.sha256(content).hexdigest()
            now = self.k.clock.now()

            # 3. Todo lo que cambia (documento, versión, trabajo y registro) se confirma junto
            with self.k.uow.transaction():
                if document_id is None:
                    # 3a. Documento nuevo
                    if len(self._documents.list(collection_id)) >= settings.max_documents:
                        raise CapacityExceeded("La colección alcanzó su máximo de documentos")
                    doc_id = self.k.ids.new_id("doc")
                    version = 1
                    job_type = JobType.INGEST
                    doc = Document(
                        id=doc_id,
                        collection_id=collection_id,
                        title=title.strip(),
                        source_type=source_type,
                        current_version=0,
                        status=DocumentStatus.PENDING,
                    )
                    self._documents.add(
                        doc, self._version(doc_id, version, content_hash, content, ctx, now), content
                    )
                else:
                    # 3b. Versión nueva de un documento existente
                    doc = self._documents.get(collection_id, document_id)
                    if doc is None:
                        raise NotFound("Documento no encontrado")
                    doc_id = doc.id
                    history = self._documents.history(collection_id, doc_id)
                    # "Sin cambios" se decide frente a la versión VIGENTE (la indexada), no frente
                    # a la última subida: si esa se canceló o falló, el contenido sigue sin indexar.
                    current = next((v for v in history if v.version == doc.current_version), None)
                    if current is not None and current.content_hash == content_hash:
                        self.k.recorder.record(
                            ctx,
                            self.action,
                            Outcome.SUCCEEDED,
                            collection_id=collection_id,
                            target={"document_id": doc_id, "version": current.version},
                            details={"unchanged": True},
                            started=started,
                        )
                        return SubmitResult(doc_id, current.version, None, True, ctx.correlation_id)
                    version = history[-1].version + 1
                    job_type = JobType.MODIFY
                    self._documents.add_version(
                        collection_id,
                        doc_id,
                        self._version(doc_id, version, content_hash, content, ctx, now),
                        content,
                    )

                job = self._queue.enqueue(
                    Job(
                        id=self.k.ids.new_id("job"),
                        collection_id=collection_id,
                        type=job_type,
                        target=doc_id,
                        version=version,
                        status=JobStatus.QUEUED,
                        actor=ctx.actor,
                        correlation_id=ctx.correlation_id,
                        created_at=now,
                        idempotency_key=idempotency_key,
                        max_attempts=self._max_attempts,
                    )
                )
                self.k.recorder.record(
                    ctx,
                    self.action,
                    Outcome.SUCCEEDED,
                    collection_id=collection_id,
                    target={"document_id": doc_id, "version": version, "job_id": job.id},
                    details={
                        "content_hash": content_hash,
                        "size": len(content),
                        "job_type": job_type.value,
                    },
                    started=started,
                )
            return SubmitResult(doc_id, version, job, False, ctx.correlation_id)

    def _version(self, doc_id, version, content_hash, content, ctx, now) -> DocumentVersion:
        return DocumentVersion(
            document_id=doc_id,
            version=version,
            content_hash=content_hash,
            size=len(content),
            created_by=ctx.actor.id,
            created_at=now,
        )


@dataclass(frozen=True)
class DocumentView:
    document: Document
    version: int
    text: str


class ReadDocument(UseCase):
    action = "document.read"

    def __init__(self, kernel: Kernel, documents: DocumentRepository) -> None:
        super().__init__(kernel)
        self._documents = documents

    def execute(
        self,
        ctx: RequestContext,
        collection_id: str,
        document_id: str,
        version: int | None = None,
    ) -> DocumentView:
        started = self.k.clock.now()
        target = {"document_id": document_id, "version": version}
        self._require(ctx, collection_id, Permission.READ_DOCUMENT, self.action, target)
        with self._guard(ctx, self.action, collection_id, started, target):
            doc = self._documents.get(collection_id, document_id)
            if doc is None or doc.deleted_at is not None:
                raise NotFound("Documento no encontrado")
            wanted = version if version is not None else doc.current_version
            if wanted == 0:
                raise NotFound("El documento todavía no está disponible")
            raw = self._documents.get_content(collection_id, document_id, wanted)
            if raw is None:
                raise NotFound("Versión no encontrada")
        self.k.recorder.record(
            ctx,
            self.action,
            Outcome.SUCCEEDED,
            collection_id=collection_id,
            target={"document_id": document_id, "version": wanted},
            started=started,
        )
        return DocumentView(doc, wanted, raw.decode("utf-8", errors="replace"))


class ListDocuments(UseCase):
    action = "documents.list"

    def __init__(self, kernel: Kernel, documents: DocumentRepository) -> None:
        super().__init__(kernel)
        self._documents = documents

    def execute(self, ctx: RequestContext, collection_id: str) -> list[Document]:
        started = self.k.clock.now()
        self._require(ctx, collection_id, Permission.LIST_DOCUMENTS, self.action)
        docs = self._documents.list(collection_id)
        self.k.recorder.record(
            ctx,
            self.action,
            Outcome.SUCCEEDED,
            collection_id=collection_id,
            details={"count": len(docs)},
            started=started,
        )
        return docs
