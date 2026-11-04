"""Base común de los casos de uso: autoriza, registra denegaciones y fallos."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator

from ..authorization import Permission
from ..context import RequestContext
from ..domain import Outcome
from ..errors import DomainError, PermissionDenied
from ..kernel import Kernel


class UseCase:
    def __init__(self, kernel: Kernel) -> None:
        self.k = kernel

    def _require(
        self,
        ctx: RequestContext,
        collection_id: str,
        permission: Permission,
        action: str,
        target: dict[str, Any] | None = None,
    ) -> None:
        """Comprueba el permiso. Si se deniega, queda constancia en el registro."""
        try:
            self.k.authz.require(ctx.actor, collection_id, permission)
        except PermissionDenied as exc:
            self.k.recorder.record(
                ctx,
                action,
                Outcome.DENIED,
                collection_id=collection_id,
                target=target,
                details={"permission": exc.permission, "reason": exc.reason},
            )
            raise

    @contextmanager
    def _guard(
        self,
        ctx: RequestContext,
        action: str,
        collection_id: str | None,
        started: datetime,
        target: dict[str, Any] | None = None,
    ) -> Iterator[None]:
        """Registra como `failed` cualquier error del dominio y lo vuelve a lanzar."""
        try:
            yield
        except DomainError as exc:
            self.k.recorder.record(
                ctx,
                action,
                Outcome.FAILED,
                collection_id=collection_id,
                target=target,
                details={"error": str(exc), "kind": type(exc).__name__},
                started=started,
            )
            raise
