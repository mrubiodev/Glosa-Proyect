from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable

from ..authorization import Permission
from ..context import RequestContext
from ..domain import AccessToken, Outcome, Scope
from ..errors import InvalidRequest, NotFound, PermissionDenied
from ..kernel import Kernel
from ..ports import AccessRepository
from ..tokens import generate_token, hash_token
from .base import UseCase


@dataclass(frozen=True)
class IssuedToken:
    token: AccessToken
    raw: str  # valor en claro: solo existe aquí, no se guarda ni se registra


class IssueToken(UseCase):
    action = "token.issue"

    def __init__(
        self, kernel: Kernel, access: AccessRepository, default_ttl_days: int | None = None
    ) -> None:
        super().__init__(kernel)
        self._access = access
        self._default_ttl_days = default_ttl_days

    def execute(
        self,
        ctx: RequestContext,
        collection_id: str,
        scopes: Iterable[Scope] = (Scope.READ,),
        ttl_days: int | None = None,
    ) -> IssuedToken:
        started = self.k.clock.now()
        wanted = frozenset(scopes)
        try:
            self.k.authz.require_can_grant(ctx.actor, collection_id, wanted)
        except PermissionDenied as exc:
            self.k.recorder.record(
                ctx,
                self.action,
                Outcome.DENIED,
                collection_id=collection_id,
                details={"permission": exc.permission, "reason": exc.reason},
            )
            raise

        with self._guard(ctx, self.action, collection_id, started):
            if not wanted:
                raise InvalidRequest("Un token necesita al menos un scope")
            ttl = ttl_days if ttl_days is not None else self._default_ttl_days
            if ttl is not None and ttl <= 0:
                raise InvalidRequest("La caducidad debe ser mayor que 0 días")

        raw = generate_token()
        expires = self.k.clock.now() + timedelta(days=ttl) if ttl else None
        token = AccessToken(
            id=self.k.ids.new_id("tok"),
            collection_id=collection_id,
            created_by=ctx.actor.id,
            hash=hash_token(raw),
            scopes=wanted,
            expires_at=expires,
        )
        self._access.save_token(token)
        self.k.recorder.record(
            ctx,
            self.action,
            Outcome.SUCCEEDED,
            collection_id=collection_id,
            target={"token_id": token.id},
            details={
                "scopes": sorted(s.value for s in wanted),
                "expires_at": expires.isoformat() if expires else None,
            },
            started=started,
        )
        return IssuedToken(token, raw)


class RevokeToken(UseCase):
    action = "token.revoke"

    def __init__(self, kernel: Kernel, access: AccessRepository) -> None:
        super().__init__(kernel)
        self._access = access

    def execute(self, ctx: RequestContext, collection_id: str, token_id: str) -> None:
        started = self.k.clock.now()
        target = {"token_id": token_id}
        self._require(ctx, collection_id, Permission.REVOKE_TOKEN, self.action, target)
        with self._guard(ctx, self.action, collection_id, started, target):
            # get_token exige la colección: no se pueden revocar tokens de otra
            if self._access.get_token(collection_id, token_id) is None:
                raise NotFound("Token no encontrado")
        self._access.revoke_token(token_id)
        self.k.recorder.record(
            ctx,
            self.action,
            Outcome.SUCCEEDED,
            collection_id=collection_id,
            target=target,
            started=started,
        )
