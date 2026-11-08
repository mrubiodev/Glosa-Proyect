"""Los datos y la cadena de hashes sobreviven a cerrar y reabrir la base de datos."""
from glosa_core.domain import Credentials, JobStatus, Scope
from glosa_core.testing import FixedClock
from glosa_core.system import UuidIds
from glosa_core.testing_world import World
from glosa_storage import SqliteStorage, register
from glosa_storage.testing import make_adapters


def open_world(path) -> World:
    clock = FixedClock()
    # Ids aleatorios: con un contador que vuelve a empezar, chocarían con los ya guardados
    return World(adapters=make_adapters(clock, str(path)), clock=clock, ids=UuidIds())


def test_todo_sobrevive_a_reabrir_la_base(tmp_path):
    path = tmp_path / "glosa.db"
    first = open_world(path)
    ana = first.user("ana")
    col = first.new_collection("ana", "Contratos")
    res = first.upload(ana, col.id, "Cláusula de rescisión anticipada.", title="Contrato")
    first.run_jobs()
    issued = first.issue_token.execute(first.ctx(ana), col.id, [Scope.READ])
    first.uow.close()

    second = open_world(path)
    ctx = second.ctx(second.user("ana"))  # ana sigue siendo propietaria
    assert second.collections.get(col.id).name == "Contratos"
    assert second.read.execute(ctx, col.id, res.document_id).text == "Cláusula de rescisión anticipada."
    assert len(second.search.execute(ctx, col.id, "rescision")) == 1  # sin tilde
    assert second.queue.get(col.id, res.job.id).status is JobStatus.SUCCEEDED
    # el token emitido antes sigue siendo válido y conserva sus permisos
    actor = second.authenticator.identify(Credentials(issued.raw))
    assert actor is not None and actor.scopes == frozenset({Scope.READ})
    # y la cadena de hashes sigue siendo válida y continúa donde se quedó
    assert second.verify_ops.execute(ctx, col.id).valid
    second.search.execute(ctx, col.id, "contrato")
    assert second.verify_ops.execute(ctx, col.id).valid
    second.uow.close()


def test_un_trabajo_a_medias_lo_recoge_otro_proceso_tras_caducar_el_lease(tmp_path):
    path = tmp_path / "glosa.db"
    first = open_world(path)
    ana = first.user("ana")
    col = first.new_collection("ana")
    res = first.upload(ana, col.id, "texto en cola")
    taken = first.queue.claim("proceso-caido", 30)  # lo toma y se cae
    assert taken.id == res.job.id
    first.uow.close()

    second = open_world(path)
    assert second.process.execute() is None  # el lease sigue vigente (el reloj de `second` es el mismo instante)
    second.clock.advance(seconds=31)
    done = second.process.execute()
    assert done.status is JobStatus.SUCCEEDED and done.attempts == 2
    second.uow.close()


class FakeRegistry:
    def __init__(self):
        self.items = {}

    def register(self, kind, name, factory):
        self.items[(kind, name)] = factory


def test_se_registra_con_los_nombres_de_las_plantillas():
    registry = FakeRegistry()
    register(registry)
    assert set(registry.items) == {("storage", "sqlite"), ("queue", "sqlite"), ("index", "sqlite-fts5")}


def test_sqlite_storage_agrupa_los_adaptadores_sobre_una_misma_base(tmp_path):
    storage = SqliteStorage(tmp_path / "g.db")
    assert storage.uow is storage.db
    assert storage.collections._db is storage.access._db is storage.documents._db is storage.log._db
    storage.close()


def test_las_fabricas_registradas_construyen_adaptadores_que_comparten_la_base(tmp_path):
    from glosa_core.testing import FixedClock

    registry = FakeRegistry()
    register(registry)
    storage = registry.items[("storage", "sqlite")](tmp_path)  # recibe la carpeta de datos
    queue = registry.items[("queue", "sqlite")](storage, FixedClock())
    index = registry.items[("index", "sqlite-fts5")](storage)
    assert (tmp_path / "glosa.db").exists()
    assert queue._db is storage.db and index._db is storage.db
    storage.close()
