"""Tokens de colección: generación, hash y autenticación (SPEC §7.4-7.5)."""
from __future__ import annotations

import hashlib
import secrets

from .domain import Actor, ActorKind, Credentials
from .ports import AccessRepository, Clock

TOKEN_PREFIX = "glosa_"


def generate_token() -> str:
    """Valor en claro del token. Solo se muestra una vez al crearlo."""
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    """Lo único que se guarda del token."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class TokenAuthenticator:
    """Implementa el puerto Authenticator para tokens de colección."""

    def __init__(self, access: AccessRepository, clock: Clock) -> None:
        self._access = access
        self._clock = clock

    def identify(self, credentials: Credentials) -> Actor | None:
        raw = credentials.bearer
        if not raw or not raw.startswith(TOKEN_PREFIX):
            return None
        token = self._access.find_token(hash_token(raw))
        if token is None or token.revoked:
            return None
        if token.expires_at is not None and token.expires_at <= self._clock.now():
            return None
        return Actor(
            kind=ActorKind.TOKEN,
            id=token.id,
            collection_id=token.collection_id,
            scopes=frozenset(token.scopes),
        )
