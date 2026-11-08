"""Consulta de la traza de una operación (SPEC §10.4 y §15)."""
from __future__ import annotations

from ..authorization import Permission
from ..context import RequestContext
from ..domain import OperationEntry, OperationFilter, Outcome
from ..errors import InvalidRequest, NotFound
from ..kernel import Kernel
from ..ports import OperationLog
from .base import UseCase

MAX_TRACE_ENTRIES = 1000


class ViewTrace(UseCase):
    """Devuelve todas las entradas del registro que comparten un `correlation_id`, de la
    petición al resultado. La presentación paso a paso la hace el paquete `explain`.

    Lo puede ver quien tenga permiso de editor o superior. Como en `QueryOperations`, la
    propia consulta se anota después de leer, para que no aparezca en su resultado.
    """

    action = "trace.view"

    def __init__(self, kernel: Kernel, log: OperationLog) -> None:
        super().__init__(kernel)
        self._log = log

    def execute(
        self, ctx: RequestContext, collection_id: str, correlation_id: str
    ) -> list[OperationEntry]:
        started = self.k.clock.now()
        target = {"correlation_id": correlation_id}
        self._require(ctx, collection_id, Permission.VIEW_TRACE, self.action, target)
        with self._guard(ctx, self.action, collection_id, started, target):
            if not (correlation_id or "").strip():
                raise InvalidRequest("Falta el identificador de la traza")
            # El registro se consulta por colección: una traza de otra no existe aquí
            entries = self._log.query(
                collection_id, OperationFilter(correlation_id=correlation_id), MAX_TRACE_ENTRIES
            )
            if not entries:
                raise NotFound("No hay ninguna traza con ese identificador")
        self.k.recorder.record(
            ctx, self.action, Outcome.SUCCEEDED, collection_id=collection_id,
            target=target, details={"steps": len(entries)}, started=started,
        )
        return entries
