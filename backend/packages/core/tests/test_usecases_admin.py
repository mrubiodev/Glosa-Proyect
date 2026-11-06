"""Trabajos y registro de operaciones: consulta, cancelación y verificación.

Incluye la ampliación de las pruebas obligatorias 1, 4 y 6 con estos casos de uso.
"""
import dataclasses

import pytest

from glosa_core.domain import (
    DocumentStatus,
    JobStatus,
    OperationFilter,
    Outcome,
    Role,
    Scope,
)
from glosa_core.errors import Conflict, InvalidRequest, NotFound, PermissionDenied


def actions(entries):
    return [e.action for e in entries]


def team(world):
    """ana (owner), edu (editor) y rita (reader) en una colección."""
    col = world.new_collection("ana", "Equipo")
    world.access.add_member("edu", col.id, Role.EDITOR)
    world.access.add_member("rita", col.id, Role.READER)
    return col


# --- GetJob / ListJobs -------------------------------------------------------

def test_el_editor_ve_el_estado_de_un_trabajo(world):
    col = team(world)
    res = world.upload(world.user("edu"), col.id, "contenido")
    job = world.get_job.execute(world.ctx(world.user("edu")), col.id, res.job.id)
    assert job.status is JobStatus.QUEUED
    world.run_jobs()
    job = world.get_job.execute(world.ctx(world.user("edu")), col.id, res.job.id)
    assert job.status is JobStatus.SUCCEEDED


def test_listar_trabajos_filtra_por_estado(world):
    col = team(world)
    ana = world.user("ana")
    world.upload(ana, col.id, "uno", title="A")
    world.upload(ana, col.id, "dos", title="B")
    world.process.execute()  # procesa el primero
    ctx = world.ctx(ana)
    assert len(world.list_jobs.execute(ctx, col.id)) == 2
    assert len(world.list_jobs.execute(ctx, col.id, JobStatus.QUEUED)) == 1
    assert len(world.list_jobs.execute(ctx, col.id, JobStatus.SUCCEEDED)) == 1


def test_limite_de_listado_invalido(world):
    col = team(world)
    for limit in (0, 201):
        with pytest.raises(InvalidRequest):
            world.list_jobs.execute(world.ctx(world.user("ana")), col.id, limit=limit)


def test_un_trabajo_inexistente_o_de_otra_coleccion_no_existe(world):
    a = world.new_collection("ana", "A")
    b = world.new_collection("otro", "B")
    res_b = world.upload(world.user("otro"), b.id, "secreto de B")
    # ana es propietaria de A y pide el trabajo de B *bajo la colección A*: no debe verlo
    with pytest.raises(NotFound):
        world.get_job.execute(world.ctx(world.user("ana")), a.id, res_b.job.id)
    with pytest.raises(NotFound):
        world.get_job.execute(world.ctx(world.user("ana")), a.id, "job-inventado")


# --- CancelJob ---------------------------------------------------------------

def test_cancelar_un_trabajo_en_cola(world):
    col = team(world)
    edu = world.user("edu")
    res = world.upload(edu, col.id, "contenido")
    job = world.cancel_job.execute(world.ctx(edu), col.id, res.job.id)
    assert job.status is JobStatus.CANCELLED
    assert world.run_jobs() == 0  # el worker ya no lo encuentra
    # una ingesta nueva cancelada nunca llegó a indexarse
    assert world.documents.get(col.id, res.document_id).status is DocumentStatus.FAILED
    assert world.index.all_chunks(col.id) == []


def test_cancelar_una_modificacion_deja_la_version_vigente(world):
    col = team(world)
    ana = world.user("ana")
    res = world.upload(ana, col.id, "versión uno")
    world.run_jobs()
    mod = world.upload(ana, col.id, "versión dos", document_id=res.document_id)
    world.cancel_job.execute(world.ctx(ana), col.id, mod.job.id)
    doc = world.documents.get(col.id, res.document_id)
    assert doc.status is DocumentStatus.READY and doc.current_version == 1
    assert world.read.execute(world.ctx(ana), col.id, res.document_id).text == "versión uno"


def test_tras_cancelar_se_puede_volver_a_subir_el_mismo_contenido(world):
    """Antes se comparaba con la última versión subida y el contenido nunca se indexaba."""
    col = team(world)
    ana = world.user("ana")
    res = world.upload(ana, col.id, "versión uno")
    world.run_jobs()
    mod = world.upload(ana, col.id, "versión dos", document_id=res.document_id)
    world.cancel_job.execute(world.ctx(ana), col.id, mod.job.id)

    again = world.upload(ana, col.id, "versión dos", document_id=res.document_id)
    assert not again.unchanged and again.job is not None
    world.run_jobs()
    assert world.read.execute(world.ctx(ana), col.id, res.document_id).text == "versión dos"


def test_no_se_puede_cancelar_un_trabajo_en_marcha_ni_terminado(world):
    col = team(world)
    ana = world.user("ana")
    first = world.upload(ana, col.id, "uno", title="A")
    second = world.upload(ana, col.id, "dos", title="B")
    world.queue.claim("w", 60)  # `first` pasa a running
    with pytest.raises(Conflict):
        world.cancel_job.execute(world.ctx(ana), col.id, first.job.id)
    world.run_jobs()
    with pytest.raises(Conflict):
        world.cancel_job.execute(world.ctx(ana), col.id, second.job.id)
    # los conflictos quedan registrados como fallos
    failed = [e for e in world.log.entries(col.id) if e.action == "job.cancel" and e.outcome is Outcome.FAILED]
    assert len(failed) == 2 and failed[0].details["kind"] == "Conflict"


def test_cancelar_un_trabajo_que_no_existe(world):
    col = team(world)
    with pytest.raises(NotFound):
        world.cancel_job.execute(world.ctx(world.user("ana")), col.id, "job-9999")


# --- QueryOperations / VerifyOperationLog -------------------------------------

def test_el_propietario_consulta_el_registro_con_filtros(world):
    col = team(world)
    ana = world.user("ana")
    res = world.upload(ana, col.id, "texto")
    world.run_jobs()
    world.search.execute(world.ctx(ana), col.id, "texto")

    ctx = world.ctx(ana)
    todo = world.query_ops.execute(ctx, col.id)
    assert "document.submit" in actions(todo) and "search.execute" in actions(todo)

    por_accion = world.query_ops.execute(ctx, col.id, OperationFilter(action="search.execute"))
    assert actions(por_accion) == ["search.execute"]

    por_corr = world.query_ops.execute(
        ctx, col.id, OperationFilter(correlation_id=res.correlation_id)
    )
    assert actions(por_corr)[0] == "document.submit" and actions(por_corr)[-1] == "job.succeed"

    assert world.query_ops.execute(ctx, col.id, limit=2) == todo[:2]


def test_la_consulta_del_registro_queda_registrada_pero_no_se_ve_a_si_misma(world):
    col = team(world)
    ctx = world.ctx(world.user("ana"))
    result = world.query_ops.execute(ctx, col.id, OperationFilter(action="collection.create"))
    assert "operations.query" not in actions(result)
    last = world.log.entries(col.id)[-1]
    assert last.action == "operations.query"
    assert last.details["filters"] == {"action": "collection.create"}
    assert last.details["count"] == 1


def test_limite_del_registro_invalido(world):
    col = team(world)
    with pytest.raises(InvalidRequest):
        world.query_ops.execute(world.ctx(world.user("ana")), col.id, limit=501)


def test_verificar_el_registro_detecta_manipulaciones(world):
    col = team(world)
    ana = world.user("ana")
    world.upload(ana, col.id, "texto")
    world.run_jobs()
    ctx = world.ctx(ana)
    assert world.verify_ops.execute(ctx, col.id).valid

    tampered_id = world.tamper_log(col.id, 1, outcome=Outcome.DENIED)
    report = world.verify_ops.execute(ctx, col.id)
    assert not report.valid and report.broken_at == tampered_id


# === Ampliación de las pruebas obligatorias ===================================

def test_1_ampliada_ningun_actor_de_a_ve_trabajos_ni_registro_de_b(world):  # prueba obligatoria 1
    a = world.new_collection("ana", "A")
    b = world.new_collection("otro", "B")
    res_b = world.upload(world.user("otro"), b.id, "dato de B")

    token_a = world.token_actor("ana", a.id, Scope.READ, Scope.WRITE)
    for actor in (world.user("ana"), token_a):
        ctx = world.ctx(actor)
        with pytest.raises(PermissionDenied):
            world.get_job.execute(ctx, b.id, res_b.job.id)
        with pytest.raises(PermissionDenied):
            world.list_jobs.execute(ctx, b.id)
        with pytest.raises(PermissionDenied):
            world.cancel_job.execute(ctx, b.id, res_b.job.id)
        with pytest.raises(PermissionDenied):
            world.query_ops.execute(ctx, b.id)
        with pytest.raises(PermissionDenied):
            world.verify_ops.execute(ctx, b.id)
    # y el trabajo de B sigue intacto
    assert world.queue.get(b.id, res_b.job.id).status is JobStatus.QUEUED


def test_4_ampliada_solo_el_propietario_ve_el_registro(world):  # prueba obligatoria 4
    col = team(world)
    for uid in ("rita", "edu"):  # lector y editor
        ctx = world.ctx(world.user(uid))
        with pytest.raises(PermissionDenied):
            world.query_ops.execute(ctx, col.id)
        with pytest.raises(PermissionDenied):
            world.verify_ops.execute(ctx, col.id)
    # el lector tampoco ve trabajos; el editor sí
    with pytest.raises(PermissionDenied):
        world.list_jobs.execute(world.ctx(world.user("rita")), col.id)
    world.list_jobs.execute(world.ctx(world.user("edu")), col.id)
    # un token (aunque sea write) no ve trabajos ni registro
    token = world.token_actor("ana", col.id, Scope.WRITE)
    with pytest.raises(PermissionDenied):
        world.list_jobs.execute(world.ctx(token), col.id)
    with pytest.raises(PermissionDenied):
        world.query_ops.execute(world.ctx(token), col.id)


def test_6_ampliada_las_denegaciones_de_trabajos_y_registro_quedan_registradas(world):  # prueba obligatoria 6
    col = team(world)
    res = world.upload(world.user("ana"), col.id, "x")
    intentos = [
        ("rita", lambda c: world.get_job.execute(c, col.id, res.job.id), "job.get"),
        ("rita", lambda c: world.list_jobs.execute(c, col.id), "jobs.list"),
        ("rita", lambda c: world.cancel_job.execute(c, col.id, res.job.id), "job.cancel"),
        ("edu", lambda c: world.query_ops.execute(c, col.id), "operations.query"),
        ("edu", lambda c: world.verify_ops.execute(c, col.id), "operations.verify"),
    ]
    for uid, call, action in intentos:
        with pytest.raises(PermissionDenied):
            call(world.ctx(world.user(uid)))
        denied = [e for e in world.log.entries(col.id) if e.outcome is Outcome.DENIED and e.action == action]
        assert denied and denied[-1].actor.id == uid and denied[-1].details["reason"]
    # y la cancelación denegada no tocó el trabajo
    assert world.queue.get(col.id, res.job.id).status is JobStatus.QUEUED


# --- Manejador ------------------------------------------------------------------

def test_un_documento_sin_texto_indexable_acaba_en_dead(world):
    col = team(world)
    res = world.upload(world.user("ana"), col.id, "   \n  \n")  # solo espacios
    world.run_jobs()
    job = world.queue.get(col.id, res.job.id)
    assert job.status is JobStatus.DEAD and "indexable" in job.error
    assert world.documents.get(col.id, res.document_id).status is DocumentStatus.FAILED
