"""Errores del dominio."""
from __future__ import annotations


class DomainError(Exception):
    """Base de los errores del dominio."""


class PermissionDenied(DomainError):
    """El actor no tiene permiso para la acción pedida."""

    def __init__(self, permission: str, reason: str) -> None:
        super().__init__(f"Permiso denegado ({permission}): {reason}")
        self.permission = permission
        self.reason = reason


class AuthenticationFailed(DomainError):
    """Las credenciales no son válidas."""
