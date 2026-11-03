"""Dobles en memoria para tests. Reutilizables por otros paquetes."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

from .domain import AccessToken, Role


class FixedClock:
    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime(2026, 1, 1, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs: float) -> None:
        self._now += timedelta(**kwargs)


class InMemoryAccessRepository:
    def __init__(self) -> None:
        self._roles: dict[tuple[str, str], Role] = {}
        self._tokens_by_id: dict[str, AccessToken] = {}

    def add_member(self, user_id: str, collection_id: str, role: Role) -> None:
        self._roles[(user_id, collection_id)] = role

    def role_of(self, user_id: str, collection_id: str) -> Role | None:
        return self._roles.get((user_id, collection_id))

    def find_token(self, token_hash: str) -> AccessToken | None:
        for token in self._tokens_by_id.values():
            if token.hash == token_hash:
                return token
        return None

    def save_token(self, token: AccessToken) -> None:
        self._tokens_by_id[token.id] = token

    def revoke_token(self, token_id: str) -> None:
        token = self._tokens_by_id[token_id]
        self._tokens_by_id[token_id] = replace(token, revoked=True)
