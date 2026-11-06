import pytest

from glosa_core.authorization import Permission as P
from glosa_core.domain import Actor, ActorKind, Scope
from glosa_core.errors import PermissionDenied

from glosa_core.testing import COL_A, COL_B


def user(uid: str) -> Actor:
    return Actor(ActorKind.USER, uid)


def token(collection: str, *scopes: Scope) -> Actor:
    return Actor(ActorKind.TOKEN, "tok-1", collection, frozenset(scopes))


# --- Roles de usuario (SPEC §7.2) ---------------------------------------

def test_reader_puede_leer_pero_no_escribir(authz):
    rita = user("rita")
    for p in (P.SEARCH, P.READ_DOCUMENT, P.LIST_DOCUMENTS):
        assert authz.allows(rita, COL_A, p)
    for p in (P.SUBMIT_DOCUMENT, P.DELETE_DOCUMENT, P.VIEW_TRACE, P.ISSUE_TOKEN):
        assert not authz.allows(rita, COL_A, p)


def test_editor_escribe_y_sigue_trabajos_pero_no_administra(authz):
    edu = user("edu")
    for p in (P.SUBMIT_DOCUMENT, P.DELETE_DOCUMENT, P.VIEW_JOBS, P.VIEW_HISTORY, P.VIEW_TRACE):
        assert authz.allows(edu, COL_A, p)
    for p in (P.ISSUE_TOKEN, P.QUERY_OPERATIONS, P.VIEW_AUDIT, P.MANAGE_MEMBERS, P.RETRY_JOB):
        assert not authz.allows(edu, COL_A, p)


def test_owner_tiene_todos_los_permisos(authz):
    ana = user("ana")
    assert all(authz.allows(ana, COL_A, p) for p in P)


def test_no_miembro_no_puede_nada(authz):
    assert authz.permissions_of(user("ana"), COL_B) == frozenset()


def test_require_lanza_permission_denied_con_motivo(authz):
    with pytest.raises(PermissionDenied) as exc:
        authz.require(user("rita"), COL_A, P.SUBMIT_DOCUMENT)
    assert exc.value.permission == "submit_document"
    assert "rol" in exc.value.reason


# --- Scopes de token (SPEC §7.3) ----------------------------------------

def test_token_read_lee_su_coleccion(authz):
    t = token(COL_A, Scope.READ)
    assert authz.allows(t, COL_A, P.SEARCH)


def test_token_nunca_accede_a_otra_coleccion(authz):  # prueba obligatoria 1
    t = token(COL_A, Scope.READ, Scope.WRITE)
    assert authz.permissions_of(t, COL_B) == frozenset()


def test_token_read_no_puede_escribir(authz):  # prueba obligatoria 2
    t = token(COL_A, Scope.READ)
    for p in (P.SUBMIT_DOCUMENT, P.DELETE_DOCUMENT, P.REINDEX_DOCUMENT):
        assert not authz.allows(t, COL_A, p)


def test_token_write_escribe_pero_no_administra(authz):
    t = token(COL_A, Scope.WRITE)
    assert authz.allows(t, COL_A, P.SUBMIT_DOCUMENT)
    for p in (P.ISSUE_TOKEN, P.QUERY_OPERATIONS, P.MANAGE_MEMBERS, P.VIEW_AUDIT):
        assert not authz.allows(t, COL_A, p)


# --- Emisión de tokens (prueba obligatoria 4 y 5) ------------------------

def test_reader_no_puede_emitir_tokens(authz):  # prueba obligatoria 4
    with pytest.raises(PermissionDenied):
        authz.require_can_grant(user("rita"), COL_A, frozenset({Scope.READ}))


def test_editor_no_puede_emitir_tokens(authz):
    with pytest.raises(PermissionDenied):
        authz.require_can_grant(user("edu"), COL_A, frozenset({Scope.READ}))


def test_owner_puede_emitir_read_y_write(authz):
    authz.require_can_grant(user("ana"), COL_A, frozenset({Scope.READ, Scope.WRITE}))


def test_un_token_no_puede_emitir_tokens(authz):
    t = token(COL_A, Scope.WRITE)
    with pytest.raises(PermissionDenied):
        authz.require_can_grant(t, COL_A, frozenset({Scope.READ}))
