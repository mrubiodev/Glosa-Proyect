"""Consulta del registro de operaciones (SPEC §10)."""
from __future__ import annotations

from dataclasses import asdict

from ..authorization import Permission
from ..context import RequestContext
from ..domain import ChainReport, OperationEntry, OperationFilter, Outcome
from ..errors import InvalidRequest
from ..kernel import Kernel
from ..ports import OperationLog
from .base import UseCase

MAX_OPERATIONS_LIMIT = 500


def _describe(filters: OperationFilter) -> dict[str, str]:
    """Filtros no vacíos, como texto, para dejarlos en el registro."""
    out: dict[str, str] = {}
    for key, value in asdict(filters).items():
        if value is not None:
            out[key] = value.isoformat() if hasattr(value, "isoformat") else str(value)
    return out


class QueryOperations(UseCase):
    """Solo el propietario. Devuelve las entradas de la colección, de antigua a reciente.

    Consultar el registro también queda registrado, y se anota después de leerlo para que
    la propia consulta no aparezca en su resultado.
    """

    action = "operations.query"

    def __init__(self, kernel: Kernel, log: OperationLog) -> None:
        super().__init__(kernel)
        self._log = log

    def execute(
        self,
        ctx: RequestContext,
        collection_id: str,
        filters: OperationFilter | None = None,
        limit: int = 100,
    ) -> list[OperationEntry]:
        started = self.k.clock.now()
        self._require(ctx, collection_id, Permission.QUERY_OPERATIONS, self.action)
        with self._guard(ctx, self.action, collection_id, started):
            if not 1 <= limit <= MAX_OPERATIONS_LIMIT:
                raise InvalidRequest(f"El límite debe estar entre 1 y {MAX_OPERATIONS_LIMIT}")
        applied = filters or OperationFilter()
        entries = self._log.query(collection_id, applied, limit)
        self.k.recorder.record(
            ctx, self.action, Outcome.SUCCEEDED, collection_id=collection_id,
            details={"filters": _describe(applied), "limit": limit, "count": len(entries)},
            started=started,
        )
        return entries


class VerifyOperationLog(UseCase):
    """Comprueba el encadenado de hashes del registro de la colección."""

    action = "operations.verify"

    def __init__(self, kernel: Kernel, log: OperationLog) -> None:
        super().__init__(kernel)
        self._log = log

    def execute(self, ctx: RequestContext, collection_id: str) -> ChainReport:
        started = self.k.clock.now()
        self._require(ctx, collection_id, Permission.QUERY_OPERATIONS, self.action)
        report = self._log.verify_chain(collection_id)
        self.k.recorder.record(
            ctx, self.action, Outcome.SUCCEEDED, collection_id=collection_id,
            details={"valid": report.valid, "checked": report.checked, "broken_at": report.broken_at},
            started=started,
        )
        return report
