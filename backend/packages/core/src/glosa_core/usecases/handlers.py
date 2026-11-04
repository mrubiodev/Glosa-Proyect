"""Manejadores del worker (SPEC §11). Son idempotentes: ejecutarlos dos veces
deja el mismo estado final."""
from __future__ import annotations

from typing import Sequence

from ..context import RequestContext
from ..domain import Chunk, DocumentStatus, Job, JobResult, Outcome
from ..errors import PermanentJobError, UnsupportedSource
from ..kernel import Kernel
from ..ports import Chunker, ChunkIndex, DocumentRepository, TextExtractor


class HandleIngest:
    """Procesa los trabajos `ingest` y `modify`.

    Pasos (cada uno deja una entrada en el registro): extraer → trocear → indexar →
    retirar versiones anteriores → marcar `ready`.
    """

    def __init__(
        self,
        kernel: Kernel,
        documents: DocumentRepository,
        index: ChunkIndex,
        extractors: Sequence[TextExtractor],
        chunker: Chunker,
    ) -> None:
        self.k = kernel
        self._documents = documents
        self._index = index
        self._extractors = extractors
        self._chunker = chunker

    def handle(self, ctx: RequestContext, job: Job) -> JobResult:
        started = self.k.clock.now()
        doc = self._documents.get(job.collection_id, job.target)
        if doc is None or doc.deleted_at is not None or job.version is None:
            raise PermanentJobError("El documento del trabajo ya no existe")
        version = job.version
        target = {"document_id": doc.id, "version": version, "job_id": job.id}
        previously_current = doc.current_version

        self._documents.update_status(
            job.collection_id, doc.id, DocumentStatus.PROCESSING
        )
        try:
            raw = self._documents.get_content(job.collection_id, doc.id, version)
            if raw is None:
                raise PermanentJobError("No se encuentra el contenido de la versión")
            extractor = next((e for e in self._extractors if e.supports(doc.source_type)), None)
            if extractor is None:
                raise UnsupportedSource(f"Sin extractor para '{doc.source_type}'")

            text = extractor.extract(raw)
            self._step(ctx, "document.extract", job, target, {"chars": len(text)})

            drafts = self._chunker.split(text)
            self._step(ctx, "document.chunk", job, target, {"chunks": len(drafts)})

            chunks = [
                Chunk(
                    # id determinista: reintentar no genera fragmentos nuevos
                    id=f"{doc.id}:{version}:{d.position}",
                    document_id=doc.id,
                    version=version,
                    collection_id=job.collection_id,
                    text=d.text,
                    position=d.position,
                    metadata={**d.metadata, "title": doc.title},
                )
                for d in drafts
            ]
            # Limpia lo que dejara un intento anterior que se interrumpió
            self._index.remove_version(job.collection_id, doc.id, version)
            self._index.index(chunks)
            self._step(ctx, "document.index", job, target, {"chunks": len(chunks)})

            # Solo la versión vigente queda indexada
            retired = []
            for old in self._documents.history(job.collection_id, doc.id):
                if old.version != version:
                    self._index.remove_version(job.collection_id, doc.id, old.version)
                    retired.append(old.version)

            self._documents.update_status(
                job.collection_id, doc.id, DocumentStatus.READY, current_version=version
            )
        except Exception as exc:
            # Si ya había una versión vigente sigue sirviéndose; si no, el documento falla
            if previously_current:
                self._documents.update_status(
                    job.collection_id, doc.id, DocumentStatus.READY, current_version=previously_current
                )
            else:
                self._documents.update_status(job.collection_id, doc.id, DocumentStatus.FAILED)
            self.k.recorder.record(
                ctx,
                "document.ingest",
                Outcome.FAILED,
                collection_id=job.collection_id,
                target=target,
                details={"error": str(exc), "kind": type(exc).__name__},
                started=started,
            )
            raise

        self.k.recorder.record(
            ctx,
            "document.ingest",
            Outcome.SUCCEEDED,
            collection_id=job.collection_id,
            target=target,
            details={"chunks": len(chunks), "retired_versions": retired},
            started=started,
        )
        return JobResult({"chunks": len(chunks), "version": version})

    def _step(self, ctx, action, job, target, details) -> None:
        self.k.recorder.record(
            ctx,
            action,
            Outcome.SUCCEEDED,
            collection_id=job.collection_id,
            target=target,
            details=details,
        )
