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


class NotFound(DomainError):
    """El recurso no existe (o no es visible para el actor)."""


class InvalidRequest(DomainError):
    """La petición no es válida."""


class Conflict(DomainError):
    """La operación choca con el estado actual del recurso."""


class CapacityExceeded(DomainError):
    """Se superó un límite de la colección (documentos, tamaño, cola)."""


class PermanentJobError(DomainError):
    """Fallo de un trabajo que no tiene sentido reintentar."""


class UnsupportedSource(PermanentJobError):
    """Ningún extractor admite el tipo de documento."""
