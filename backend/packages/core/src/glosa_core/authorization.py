"""Servicio de autorización: la ÚNICA pieza que decide permisos (SPEC §7).

API, servidor MCP y worker lo llaman antes de ejecutar un caso de uso.
"""
from __future__ import annotations

from enum import StrEnum

from .domain import Actor, ActorKind, Role, Scope
from .errors import PermissionDenied
from .ports import AccessRepository


class Permission(StrEnum):
    # Lecturas
    SEARCH = "search"
    READ_DOCUMENT = "read_document"
    LIST_DOCUMENTS = "list_documents"
    # Escrituras (se encolan)
    SUBMIT_DOCUMENT = "submit_document"
    DELETE_DOCUMENT = "delete_document"
    REINDEX_DOCUMENT = "reindex_document"
    # Seguimiento
    VIEW_HISTORY = "view_history"
    VIEW_JOBS = "view_jobs"
    CANCEL_JOB = "cancel_job"
    VIEW_TRACE = "view_trace"
    # Administración
    RETRY_JOB = "retry_job"
    ISSUE_TOKEN = "issue_token"
    REVOKE_TOKEN = "revoke_token"
    MANAGE_MEMBERS = "manage_members"
    MANAGE_SETTINGS = "manage_settings"
    DELETE_COLLECTION = "delete_collection"
    QUERY_OPERATIONS = "query_operations"
    VIEW_AUDIT = "view_audit"


_READ = frozenset(
    {Permission.SEARCH, Permission.READ_DOCUMENT, Permission.LIST_DOCUMENTS}
)
_WRITE = frozenset(
    {
        Permission.SUBMIT_DOCUMENT,
        Permission.DELETE_DOCUMENT,
        Permission.REINDEX_DOCUMENT,
    }
)
_FOLLOW_UP = frozenset(
    {
        Permission.VIEW_HISTORY,
        Permission.VIEW_JOBS,
        Permission.CANCEL_JOB,
        Permission.VIEW_TRACE,
    }
)

# SPEC §7.2 — roles de usuario
ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.READER: _READ,
    Role.EDITOR: _READ | _WRITE | _FOLLOW_UP,
    Role.OWNER: frozenset(Permission),
}

# SPEC §7.3 — scopes de token. Un token nunca administra la colección.
SCOPE_PERMISSIONS: dict[Scope, frozenset[Permission]] = {
    Scope.READ: _READ,
    Scope.WRITE: _READ | _WRITE,
}


class AuthorizationService:
    def __init__(self, access: AccessRepository) -> None:
        self._access = access

    def permissions_of(self, actor: Actor, collection_id: str) -> frozenset[Permission]:
        """Permisos que el actor tiene sobre esa colección (vacío si ninguno)."""
        if actor.kind is ActorKind.SYSTEM:
            return frozenset()  # el sistema deja constancia, pero no pasa por la autorización
        if actor.kind is ActorKind.TOKEN:
            # El token fija la colección: en cualquier otra, no puede nada.
            if actor.collection_id != collection_id:
                return frozenset()
            granted: set[Permission] = set()
            for scope in actor.scopes:
                granted |= SCOPE_PERMISSIONS.get(scope, frozenset())
            return frozenset(granted)

        role = self._access.role_of(actor.id, collection_id)
        if role is None:
            return frozenset()  # no es miembro
        return ROLE_PERMISSIONS[role]

    def allows(self, actor: Actor, collection_id: str, permission: Permission) -> bool:
        return permission in self.permissions_of(actor, collection_id)

    def require(self, actor: Actor, collection_id: str, permission: Permission) -> None:
        """Lanza PermissionDenied si el actor no tiene el permiso."""
        if self.allows(actor, collection_id, permission):
            return
        raise PermissionDenied(permission.value, self._reason(actor, collection_id))

    def require_can_grant(
        self, actor: Actor, collection_id: str, scopes: frozenset[Scope]
    ) -> None:
        """Quien emite un token no puede darle más permisos de los que tiene."""
        self.require(actor, collection_id, Permission.ISSUE_TOKEN)
        mine = self.permissions_of(actor, collection_id)
        for scope in scopes:
            missing = SCOPE_PERMISSIONS[scope] - mine
            if missing:
                raise PermissionDenied(
                    Permission.ISSUE_TOKEN.value,
                    f"el emisor no puede conceder el scope '{scope.value}'",
                )

    def _reason(self, actor: Actor, collection_id: str) -> str:
        if actor.kind is ActorKind.TOKEN:
            if actor.collection_id != collection_id:
                return "el token pertenece a otra colección"
            return "el scope del token no incluye este permiso"
        if self._access.role_of(actor.id, collection_id) is None:
            return "el usuario no es miembro de la colección"
        return "el rol del usuario no incluye este permiso"
