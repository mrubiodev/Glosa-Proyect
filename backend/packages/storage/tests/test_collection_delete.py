import pytest

from glosa_core.domain import Scope
from glosa_core.testing import FixedClock
from glosa_core.testing_world import World
from glosa_storage.testing import make_adapters

TABLES = ("memberships", "tokens", "documents", "document_versions", "chunks", "jobs", "operations")


@pytest.fixture
def w():
    clock = FixedClock()
    return World(adapters=make_adapters(clock), clock=clock)


def rows(world, table, collection_id) -> int:
    return world.uow.conn().execute(
        f"SELECT count(*) FROM {table} WHERE collection_id = ?", (collection_id,)
    ).fetchone()[0]


def populate(world, owner, name):
    """Una colección con de todo: un documento indexado, otro en cola, un token y un registro."""
    col = world.new_collection(owner, name)
    world.upload(world.user(owner), col.id, "informe confidencial del cliente")
    world.run_jobs()  # el worker procesa lo que haya en cola, de cualquier colección
    world.upload(world.user(owner), col.id, "segundo documento pendiente", title="B")
    world.token_actor(owner, col.id, Scope.READ)
    world.search.execute(world.ctx(world.user(owner)), col.id, "confidencial")
    return col


def test_borrar_una_coleccion_elimina_todos_sus_datos(w):
    a = populate(w, "ana", "A")
    assert all(rows(w, t, a.id) > 0 for t in TABLES)  # había de todo

    w.collections.delete(a.id)

    assert w.collections.get(a.id) is None
    assert all(rows(w, t, a.id) == 0 for t in TABLES), {t: rows(w, t, a.id) for t in TABLES}
    assert w.index.search(a.id, "confidencial", 10) == []  # tampoco en el índice de texto


def test_borrar_una_coleccion_no_toca_a_las_demas(w):
    a = populate(w, "ana", "A")
    b = populate(w, "otro", "B")
    before = {t: rows(w, t, b.id) for t in TABLES}

    w.collections.delete(a.id)

    assert {t: rows(w, t, b.id) for t in TABLES} == before
    assert len(w.index.search(b.id, "confidencial", 10)) == 1
    assert w.verify_ops.execute(w.ctx(w.user("otro")), b.id).valid


def test_el_indice_de_texto_queda_consistente_tras_borrar(w):
    a = populate(w, "ana", "A")
    w.collections.delete(a.id)
    check = w.uow.conn().execute("INSERT INTO chunks_fts(chunks_fts) VALUES('integrity-check')")
    assert check is not None  # lanzaría si el índice quedara incoherente con la tabla
