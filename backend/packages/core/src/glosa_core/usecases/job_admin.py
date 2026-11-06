"""Consulta y cancelación de trabajos (SPEC §9 y §11)."""
from __future__ import annotations

from ..authorization import Permission
from ..context import RequestContext
from ..domain import DocumentStatus, Job, JobStatus, JobType, Outcome
from ..errors import Conflict, InvalidRequest, NotFound
from ..kernel import Kernel
from ..ports import DocumentRepository, JobQueue
from .base import UseCase

MAX_LIST_LIMIT = 200


class GetJob(UseCase):
    action = "job.get"

    def __init__(self, kernel: Kernel, queue: JobQueue) -> None:
        super().__init__(kernel)
        self._queue = queue

    def execute(self, ctx: RequestContext, collection_id: str, job_id: str) -> Job:
        started = self.k.clock.now()
        target = {"job_id": job_id}
        self._require(ctx, collection_id, Permission.VIEW_JOBS, self.action, target)
        with self._guard(ctx, self.action, collection_id, started, target):
            # La cola exige la colección: un trabajo de otra no es visible
            job = self._queue.get(collection_id, job_id)
            if job is None:
                raise NotFound("Trabajo no encontrado")
        self.k.recorder.record(
            ctx, self.action, Outcome.SUCCEEDED, collection_id=collection_id,
            target=target, details={"status": job.status.value}, started=started,
        )
        return job


class ListJobs(UseCase):
    action = "jobs.list"

    def __init__(self, kernel: Kernel, queue: JobQueue) -> None:
        super().__init__(kernel)
        self._queue = queue

    def execute(
        self,
        ctx: RequestContext,
        collection_id: str,
        status: JobStatus | None = None,
        limit: int = 50,
    ) -> list[Job]:
        started = self.k.clock.now()
        self._require(ctx, collection_id, Permission.VIEW_JOBS, self.action)
        with self._guard(ctx, self.action, collection_id, started):
            if not 1 <= limit <= MAX_LIST_LIMIT:
                raise InvalidRequest(f"El límite debe estar entre 1 y {MAX_LIST_LIMIT}")
        jobs = self._queue.list(collection_id, status.value if status else None, limit)
        self.k.recorder.record(
            ctx, self.action, Outcome.SUCCEEDED, collection_id=collection_id,
            details={"status": status.value if status else None, "count": len(jobs)},
            started=started,
        )
        return jobs


class CancelJob(UseCase):
    """Cancela un trabajo que sigue en cola. Uno ya en marcha no se puede cancelar."""

    action = "job.cancel"

    def __init__(self, kernel: Kernel, queue: JobQueue, documents: DocumentRepository) -> None:
        super().__init__(kernel)
        self._queue = queue
        self._documents = documents

    def execute(self, ctx: RequestContext, collection_id: str, job_id: str) -> Job:
        started = self.k.clock.now()
        target = {"job_id": job_id}
        self._require(ctx, collection_id, Permission.CANCEL_JOB, self.action, target)
        with self._guard(ctx, self.action, collection_id, started, target):
            with self.k.uow.transaction():
                job = self._queue.get(collection_id, job_id)
                if job is None:
                    raise NotFound("Trabajo no encontrado")
                if job.status is not JobStatus.QUEUED:
                    raise Conflict(
                        f"Solo se puede cancelar un trabajo en cola (estado actual: {job.status.value})"
                    )
                if not self._queue.cancel(collection_id, job_id):
                    raise Conflict("El trabajo ya no está en cola")

                # Un documento nuevo cuya ingesta se cancela no llegó a indexarse nunca: queda
                # `failed`. En una modificación el documento sigue sirviendo su versión vigente.
                document_status = None
                if job.type is JobType.INGEST:
                    self._documents.update_status(collection_id, job.target, DocumentStatus.FAILED)
                    document_status = DocumentStatus.FAILED.value
                self.k.recorder.record(
                    ctx, self.action, Outcome.SUCCEEDED, collection_id=collection_id,
                    target={"job_id": job_id, "document_id": job.target, "version": job.version},
                    details={"type": job.type.value, "document_status": document_status},
                    started=started,
                )
        return self._queue.get(collection_id, job_id)
