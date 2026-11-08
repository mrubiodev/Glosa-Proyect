"""ViewTrace, el actor del sistema y el límite de búsqueda por defecto."""
import pytest

from glosa_core.domain import (
    Actor, ActorKind, Channel, CollectionSettings, Outcome, Role, Scope,
)
from glosa_core.authorization import Permission
from glosa_core.errors import InvalidRequest, NotFound, PermissionDenied
from glosa_core.testing_world import World


def actions(entries):
    return [e.action for e in entries]


def setup(world):
    col = world.new_collection("ana", "Equipo")
    world.access.add_member("edu", col.id, Role.EDITOR)
    world.access.add_member("rita", col.id, Role.READER)
    res = world.upload(world.user("edu"), col.id, "texto de prueba")
    world.run_jobs()
    return col, res


def test_el_editor_ve_la_traza_completa_de_una_operacion(world):
    col, res = setup(world)
    trace = world.view_trace.execute(world.ctx(world.user("edu")), col.id, res.correlation_id)
    assert actions(trace) == [
        "document.submit", "job.start", "document.extract", "document.chunk",
        "document.index", "document.ingest", "job.succeed",
    ]


def test_el_propietario_tambien_la_ve_y_el_lector_no(world):
    col, res = setup(world)
    world.view_trace.execute(world.ctx(world.user("ana")), col.id, res.correlation_id)
    with pytest.raises(PermissionDenied):
        world.view_trace.execute(world.ctx(world.user("rita")), col.id, res.correlation_id)


def test_un_token_no_ve_trazas(world):
    col, res = setup(world)
    token = world.token_actor("ana", col.id, Scope.READ, Scope.WRITE)
    with pytest.raises(PermissionDenied):
        world.view_trace.execute(world.ctx(token), col.id, res.correlation_id)


def test_la_denegacion_de_una_traza_queda_registrada(world):  # prueba obligatoria 6
    col, res = setup(world)
    with pytest.raises(PermissionDenied):
        world.view_trace.execute(world.ctx(world.user("rita")), col.id, res.correlation_id)
    denied = [e for e in world.log.entries(col.id) if e.action == "trace.view" and e.outcome is Outcome.DENIED]
    assert denied and denied[-1].actor.id == "rita"


def test_una_traza_de_otra_coleccion_no_existe(world):  # prueba obligatoria 1
    a, res_a = setup(world)
    b = world.new_collection("otro", "B")
    # el propietario de B pide, bajo B, la traza de una operación de A
    with pytest.raises(NotFound):
        world.view_trace.execute(world.ctx(world.user("otro")), b.id, res_a.correlation_id)
    # y quien no es miembro de A ni siquiera la pide
    with pytest.raises(PermissionDenied):
        world.view_trace.execute(world.ctx(world.user("otro")), a.id, res_a.correlation_id)


def test_traza_inexistente_o_vacia(world):
    col, _ = setup(world)
    ctx = world.ctx(world.user("ana"))
    with pytest.raises(NotFound):
        world.view_trace.execute(ctx, col.id, "corr-inventada")
    with pytest.raises(InvalidRequest):
        world.view_trace.execute(ctx, col.id, "  ")


def test_consultar_una_traza_queda_registrado_pero_no_aparece_en_ella(world):
    col, res = setup(world)
    trace = world.view_trace.execute(world.ctx(world.user("ana")), col.id, res.correlation_id)
    assert "trace.view" not in actions(trace)
    last = world.log.entries(col.id)[-1]
    assert last.action == "trace.view" and last.details == {"steps": 7}


def test_el_actor_del_sistema_no_tiene_ningun_permiso(world):
    col = world.new_collection("ana")
    system = Actor(ActorKind.SYSTEM, "system")
    assert world.kernel.authz.permissions_of(system, col.id) == frozenset()
    with pytest.raises(PermissionDenied):
        world.kernel.authz.require(system, col.id, Permission.SEARCH)


def test_el_limite_de_busqueda_por_defecto_es_configurable():
    from glosa_core.usecases import SearchCollection

    w = World()
    ana = w.user("ana")
    col = w.new_collection("ana")
    for i in range(6):
        w.upload(ana, col.id, f"palabra comun {i}", title=f"D{i}")
    w.run_jobs()
    assert len(w.search.execute(w.ctx(ana), col.id, "palabra")) == 5  # por defecto, 5
    custom = SearchCollection(w.kernel, w.collections, w.index, default_limit=2)
    assert len(custom.execute(w.ctx(ana), col.id, "palabra")) == 2
    assert len(custom.execute(w.ctx(ana), col.id, "palabra", limit=4)) == 4  # lo explícito manda
