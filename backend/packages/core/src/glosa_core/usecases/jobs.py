"""Ejecución de la cola: toma un trabajo, lo despacha y decide reintento o fallo."""
from __future__ import annotations

from datetime import timedelta
from typing import Mapping, Protocol

from ..context import RequestContext
from ..domain import Channel, Job, JobResult, JobType, Outcome
from ..errors import PermanentJobError
from ..kernel import Kernel
from ..ports import JobQueue


class JobHandler(Protocol):
    def handle(self, ctx: RequestContext, job: Job) -> JobResult: ...


class ProcessNextJob:
    """Lo que hace un worker en cada vuelta. El adaptador `worker` solo lo llama en bucle."""

    def __init__(
        self,
        kernel: Kernel,
        queue: JobQueue,
        handlers: Mapping[JobType, JobHandler],
        worker_id: str = "worker-1",
        lease_seconds: int = 60,
        backoff_base_seconds: int = 30,
    ) -> None:
        self.k = kernel
        self._queue = queue
        self._handlers = handlers
        self._worker_id = worker_id
        self._lease = lease_seconds
        self._backoff = backoff_base_seconds

    def execute(self) -> Job | None:
        """Procesa un trabajo. Devuelve su estado final, o None si no había ninguno listo."""
        job = self._queue.claim(self._worker_id, self._lease)
        if job is None:
            return None

        # El worker actúa con la identidad y el correlation_id de quien encoló el trabajo
        ctx = RequestContext(job.actor, Channel.WORKER, job.correlation_id)
        target = {"job_id": job.id, "document_id": job.target, "version": job.version}
        record = self.k.recorder.record
        record(ctx, "job.start", Outcome.SUCCEEDED, collection_id=job.collection_id,
               target=target, details={"type": job.type.value, "attempt": job.attempts})

        try:
            handler = self._handlers.get(job.type)
            if handler is None:
                raise PermanentJobError(f"No hay manejador para '{job.type.value}'")
            result = handler.handle(ctx, job)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            permanent = isinstance(exc, PermanentJobError) or job.attempts >= job.max_attempts
            with self.k.uow.transaction():  # el cambio de estado y su registro, juntos
                if permanent:
                    self._queue.fail(job.id, error, None)
                    record(ctx, "job.dead", Outcome.FAILED, collection_id=job.collection_id,
                           target=target, details={"error": error, "attempts": job.attempts})
                else:
                    retry_at = self.k.clock.now() + timedelta(
                        seconds=self._backoff * 2 ** (job.attempts - 1)
                    )
                    self._queue.fail(job.id, error, retry_at)
                    record(ctx, "job.retry", Outcome.FAILED, collection_id=job.collection_id,
                           target=target,
                           details={"error": error, "attempts": job.attempts,
                                    "retry_at": retry_at.isoformat()})
        else:
            with self.k.uow.transaction():
                self._queue.ack(job.id, result)
                record(ctx, "job.succeed", Outcome.SUCCEEDED, collection_id=job.collection_id,
                       target=target, details=result.summary)
        return self._queue.get(job.collection_id, job.id)
