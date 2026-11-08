from dataclasses import replace
from datetime import timedelta

import pytest

from glosa_core.domain import CollectionSettings, JobType, OperationFilter, Role, Scope
from glosa_core.errors import PermissionDenied
from glosa_core.testing_world import World
from glosa_core.usecases import ProcessNextJob
from glosa_explain import build_trace, describe


def trace_of(world, ctx_user, col, correlation_id):
    entries = world.view_trace.execute(world.ctx(world.user(ctx_user)), col.id, correlation_id)
    return build_trace(entries)


def test_la_traza_de_una_subida_cuenta_toda_la_historia(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    res = world.upload(ana, col.id, "Un párrafo.\n\nOtro párrafo.")
    world.clock.advance(milliseconds=40)
    world.run_jobs()

    trace = trace_of(world, "ana", col, res.correlation_id)

    assert [s.action for s in trace.steps] == [
        "document.submit", "job.start", "document.extract", "document.chunk",
        "document.index", "document.ingest", "job.succeed",
    ]
    assert [s.index for s in trace.steps] == [1, 2, 3, 4, 5, 6, 7]
    assert trace.outcome == "succeeded"
    assert trace.channels == ("api", "worker")  # cruzó de la API al worker
    assert trace.actors == ("ana",)
    assert trace.collection_id == col.id
    assert trace.duration_ms == 40
    titles = [s.title for s in trace.steps]
    assert titles[0] == "Se recibió el documento" and titles[-1] == "Trabajo terminado"
    assert "2 fragmentos" in trace.steps[3].detail
    assert "Versión 1 con 2 fragmentos" in trace.steps[5].detail


def test_una_subida_que_aun_no_se_ha_procesado_esta_en_curso(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    res = world.upload(ana, col.id, "texto")
    trace = trace_of(world, "ana", col, res.correlation_id)
    assert trace.outcome == "in_progress" and len(trace.steps) == 1
    assert "en cola" in trace.steps[0].detail


def test_un_trabajo_con_un_reintento_pendiente_sigue_en_curso(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    res = world.upload(ana, col.id, "texto")

    class Roto:
        def handle(self, ctx, job):
            raise RuntimeError("disco lleno")

    ProcessNextJob(world.kernel, world.queue, {JobType.INGEST: Roto()}).execute()
    trace = trace_of(world, "ana", col, res.correlation_id)
    assert trace.outcome == "in_progress"
    retry = trace.steps[-1]
    assert retry.title == "El trabajo falló y se reintentará" and "disco lleno" in retry.detail


def test_un_reintento_que_acaba_bien_es_correcto_y_conserva_el_fallo_en_la_historia(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    res = world.upload(ana, col.id, "texto")

    class Roto:
        def handle(self, ctx, job):
            raise RuntimeError("fallo transitorio")

    ProcessNextJob(world.kernel, world.queue, {JobType.INGEST: Roto()}).execute()
    world.clock.advance(seconds=31)
    world.run_jobs()
    trace = trace_of(world, "ana", col, res.correlation_id)
    assert trace.outcome == "succeeded"
    assert "job.retry" in [s.action for s in trace.steps]  # el fallo no se borra


def test_un_trabajo_muerto_es_fallido(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    res = world.upload(ana, col.id, "   \n  ")  # sin texto indexable
    world.run_jobs()
    trace = trace_of(world, "ana", col, res.correlation_id)
    assert trace.outcome == "failed"
    assert trace.steps[-1].title == "El trabajo falló definitivamente"
    assert "indexable" in trace.steps[-1].detail
    failed_ingest = [s for s in trace.steps if s.action == "document.ingest"][0]
    assert failed_ingest.title.endswith("— falló")


def test_una_denegacion_se_muestra_con_el_permiso_que_faltaba(world):
    col = world.new_collection("ana")
    world.access.add_member("rita", col.id, Role.READER)
    ctx = world.ctx(world.user("rita"))
    with pytest.raises(PermissionDenied):
        world.submit.execute(ctx, col.id, title="x", source_type="text", content=b"hola")

    entries = world.query_ops.execute(world.ctx(world.user("ana")), col.id,
                                      OperationFilter(correlation_id=ctx.correlation_id))
    trace = build_trace(entries)
    assert trace.outcome == "denied"
    assert trace.steps[0].title == "Acceso denegado"
    assert "submit_document" in trace.steps[0].detail and "rol" in trace.steps[0].detail


def test_la_busqueda_muestra_la_consulta_o_su_ausencia_segun_el_ajuste(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    world.upload(ana, col.id, "informe zeta")
    world.run_jobs()
    ctx = world.ctx(ana)
    world.search.execute(ctx, col.id, "zeta")
    full = build_trace(world.query_ops.execute(world.ctx(ana), col.id, OperationFilter(correlation_id=ctx.correlation_id)))
    assert "«zeta»" in full.steps[0].detail and "1 resultado" in full.steps[0].detail
    assert "1 resultados" not in full.steps[0].detail

    hidden = World(CollectionSettings(query_logging="hash_only"))
    h_ana = hidden.user("ana")
    h_col = hidden.new_collection("ana")
    hidden.upload(h_ana, h_col.id, "informe zeta")
    hidden.run_jobs()
    h_ctx = hidden.ctx(h_ana)
    hidden.search.execute(h_ctx, h_col.id, "zeta")
    trace = build_trace(hidden.query_ops.execute(hidden.ctx(h_ana), h_col.id, OperationFilter(correlation_id=h_ctx.correlation_id)))
    assert "zeta" not in trace.steps[0].detail and "solo su huella" in trace.steps[0].detail


def test_cada_accion_conocida_tiene_una_descripcion_en_lenguaje_llano(world):
    """Un recorrido que toca todas las acciones del sistema: ninguna debe salir con su
    nombre técnico como título."""
    ana = world.user("ana")
    col = world.new_collection("ana")
    res = world.upload(ana, col.id, "texto del documento")
    world.get_job.execute(world.ctx(ana), col.id, res.job.id)
    world.list_jobs.execute(world.ctx(ana), col.id)
    world.run_jobs()
    world.read.execute(world.ctx(ana), col.id, res.document_id)
    world.list_docs.execute(world.ctx(ana), col.id)
    world.search.execute(world.ctx(ana), col.id, "texto")
    other = world.upload(ana, col.id, "otro", title="B")
    world.cancel_job.execute(world.ctx(ana), col.id, other.job.id)
    issued = world.issue_token.execute(world.ctx(ana), col.id, [Scope.READ])
    world.revoke_token.execute(world.ctx(ana), col.id, issued.token.id)
    world.verify_ops.execute(world.ctx(ana), col.id)
    world.query_ops.execute(world.ctx(ana), col.id)
    world.view_trace.execute(world.ctx(ana), col.id, res.correlation_id)

    for entry in world.log.entries(col.id) + world.log.entries(None):
        title, _ = describe(entry)
        assert title != entry.action, f"sin descripción: {entry.action}"


def test_el_texto_de_la_traza_se_lee_paso_a_paso(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    res = world.upload(ana, col.id, "Un párrafo.")
    world.run_jobs()
    text = trace_of(world, "ana", col, res.correlation_id).to_text()
    lines = text.splitlines()
    assert lines[0].startswith(f"Traza {res.correlation_id} · resultado: correcto · 7 pasos")
    assert " 1. " in lines[1] and "[api] ana — Se recibió el documento" in lines[1]
    assert any("[worker] ana — Trabajo terminado" in l for l in lines)


def test_no_se_pueden_mezclar_operaciones_ni_construir_una_traza_vacia(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    a = world.upload(ana, col.id, "uno", title="A")
    b = world.upload(ana, col.id, "dos", title="B")
    mixed = (
        world.log.query(col.id, OperationFilter(correlation_id=a.correlation_id), 10)
        + world.log.query(col.id, OperationFilter(correlation_id=b.correlation_id), 10)
    )
    with pytest.raises(ValueError, match="mezclan"):
        build_trace(mixed)
    with pytest.raises(ValueError, match="No hay entradas"):
        build_trace([])


def test_una_accion_desconocida_no_rompe_la_traza(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    entry = replace(world.log.entries(col.id)[0], action="algo.futuro", details={})
    assert describe(entry) == ("algo.futuro", "")


def test_la_concordancia_de_singular_y_plural_es_correcta(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    res = world.upload(ana, col.id, "x")  # un solo carácter y un solo fragmento
    world.run_jobs()
    steps = trace_of(world, "ana", col, res.correlation_id).steps
    by_action = {s.action: s.detail for s in steps}
    assert by_action["document.extract"] == "1 carácter"
    assert by_action["document.chunk"] == "1 fragmento"
    assert by_action["document.index"] == "1 fragmento"
    assert "1 byte;" in by_action["document.submit"]
    assert "1 fragmento" in by_action["document.ingest"] and "fragmentos" not in by_action["document.ingest"]
    many = world.upload(ana, col.id, "uno.\n\ndos.\n\ntres.", title="B")
    world.run_jobs()
    detail = {s.action: s.detail for s in trace_of(world, "ana", col, many.correlation_id).steps}
    assert detail["document.chunk"] == "3 fragmentos"


def test_la_cabecera_concuerda_con_un_solo_paso(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    res = world.upload(ana, col.id, "texto")
    head = trace_of(world, "ana", col, res.correlation_id).to_text().splitlines()[0]
    assert "1 paso ·" in head and "1 pasos" not in head
