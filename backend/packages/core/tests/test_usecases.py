import dataclasses
import hashlib
import json

import pytest

from glosa_core.domain import (
    Channel,
    CollectionSettings,
    Credentials,
    DocumentStatus,
    JobStatus,
    OperationFilter,
    Outcome,
    Role,
    Scope,
)
from glosa_core.errors import (
    CapacityExceeded,
    InvalidRequest,
    NotFound,
    PermissionDenied,
)
from world import World


def actions(entries):
    return [e.action for e in entries]


def dump(entries) -> str:
    return json.dumps([dataclasses.asdict(e) for e in entries], default=str)


# --- Colecciones -----------------------------------------------------------

def test_crear_coleccion_hace_propietario_al_creador(world):
    col = world.new_collection("ana", "  Contratos  ")
    assert col.name == "Contratos"
    assert world.access.role_of("ana", col.id).value == "owner"
    assert world.collections.get(col.id) is not None
    assert actions(world.log.entries(col.id)) == ["collection.create"]


def test_un_token_no_puede_crear_colecciones(world):
    col = world.new_collection("ana")
    token = world.token_actor("ana", col.id, Scope.WRITE)
    with pytest.raises(PermissionDenied):
        world.create_collection.execute(world.ctx(token), "Otra")
    # la denegación queda registrada (sin colección asociada)
    assert world.log.entries(None)[-1].outcome is Outcome.DENIED


@pytest.mark.parametrize("name", ["", "   ", "x" * 121])
def test_nombre_de_coleccion_invalido(world, name):
    with pytest.raises(InvalidRequest):
        world.create_collection.execute(world.ctx(world.user("ana")), name)


# --- Tokens ----------------------------------------------------------------

def test_el_token_emitido_se_guarda_hasheado_y_el_valor_no_se_registra(world):
    col = world.new_collection("ana")
    issued = world.issue_token.execute(world.ctx(world.user("ana")), col.id, [Scope.READ])
    stored = world.access.find_token(hashlib.sha256(issued.raw.encode()).hexdigest())
    assert stored is not None and stored.hash != issued.raw
    assert issued.raw not in dump(world.log.entries(col.id))


def test_solo_el_propietario_emite_tokens(world):
    col = world.new_collection("ana")
    world.access.add_member("rita", col.id, Role.READER)
    with pytest.raises(PermissionDenied):
        world.issue_token.execute(world.ctx(world.user("rita")), col.id, [Scope.READ])


def test_emitir_sin_scopes_es_invalido(world):
    col = world.new_collection("ana")
    with pytest.raises(InvalidRequest):
        world.issue_token.execute(world.ctx(world.user("ana")), col.id, [])


def test_token_con_caducidad(world):
    col = world.new_collection("ana")
    issued = world.issue_token.execute(
        world.ctx(world.user("ana")), col.id, [Scope.READ], ttl_days=1
    )
    assert issued.token.expires_at is not None
    world.clock.advance(days=2)
    assert world.authenticator.identify(Credentials(issued.raw)) is None


def test_revocar_surte_efecto_inmediato(world):
    col = world.new_collection("ana")
    issued = world.issue_token.execute(world.ctx(world.user("ana")), col.id, [Scope.READ])
    assert world.authenticator.identify(Credentials(issued.raw)) is not None
    world.revoke_token.execute(world.ctx(world.user("ana")), col.id, issued.token.id)
    assert world.authenticator.identify(Credentials(issued.raw)) is None


def test_no_se_pueden_revocar_tokens_de_otra_coleccion(world):
    a = world.new_collection("ana")
    b = world.new_collection("otro")
    issued_b = world.issue_token.execute(world.ctx(world.user("otro")), b.id, [Scope.READ])
    with pytest.raises(NotFound):
        world.revoke_token.execute(world.ctx(world.user("ana")), a.id, issued_b.token.id)
    # y el token de B sigue vivo
    assert not world.access.get_token(b.id, issued_b.token.id).revoked


# --- Documentos: subida, ingesta y lectura -----------------------------------

def test_subir_encola_y_el_worker_indexa(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    res = world.upload(ana, col.id, "Las cláusulas de rescisión.\n\nEl plazo de pago es de 30 días.")

    assert res.job.status is JobStatus.QUEUED
    doc = world.documents.get(col.id, res.document_id)
    assert doc.status is DocumentStatus.PENDING and doc.current_version == 0

    assert world.run_jobs() == 1
    doc = world.documents.get(col.id, res.document_id)
    assert doc.status is DocumentStatus.READY and doc.current_version == 1
    assert len(world.index.all_chunks(col.id)) == 2
    assert world.queue.get(col.id, res.job.id).status is JobStatus.SUCCEEDED


def test_buscar_devuelve_fragmentos_con_procedencia(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    res = world.upload(ana, col.id, "Plazo de pago: 30 días.\n\nRescisión anticipada permitida.")
    world.run_jobs()
    hits = world.search.execute(world.ctx(ana), col.id, "rescisión")
    assert len(hits) == 1
    assert hits[0].chunk.document_id == res.document_id and hits[0].chunk.version == 1


def test_leer_documento_devuelve_la_version_vigente_o_una_concreta(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    res = world.upload(ana, col.id, "versión uno")
    world.run_jobs()
    world.upload(ana, col.id, "versión dos", document_id=res.document_id)
    # mientras la versión 2 no se procesa, se sirve la 1
    assert world.read.execute(world.ctx(ana), col.id, res.document_id).text == "versión uno"
    world.run_jobs()
    assert world.read.execute(world.ctx(ana), col.id, res.document_id).text == "versión dos"
    assert world.read.execute(world.ctx(ana), col.id, res.document_id, version=1).text == "versión uno"


def test_leer_un_documento_aun_no_procesado(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    res = world.upload(ana, col.id, "pendiente")
    with pytest.raises(NotFound):
        world.read.execute(world.ctx(ana), col.id, res.document_id)


def test_listar_documentos(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    world.upload(ana, col.id, "uno", title="A")
    world.upload(ana, col.id, "dos", title="B")
    assert {d.title for d in world.list_docs.execute(world.ctx(ana), col.id)} == {"A", "B"}


def test_contenido_identico_no_crea_version_nueva(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    res = world.upload(ana, col.id, "igual")
    world.run_jobs()
    again = world.upload(ana, col.id, "igual", document_id=res.document_id)
    assert again.unchanged and again.job is None
    assert len(world.documents.history(col.id, res.document_id)) == 1


def test_validaciones_de_subida(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    with pytest.raises(InvalidRequest):
        world.upload(ana, col.id, "texto", title="  ")
    with pytest.raises(InvalidRequest):
        world.submit.execute(world.ctx(ana), col.id, title="x", source_type="text", content=b"")
    with pytest.raises(InvalidRequest):
        world.submit.execute(world.ctx(ana), col.id, title="x", source_type="pdf", content=b"abc")
    with pytest.raises(NotFound):
        world.upload(ana, col.id, "texto", document_id="doc-inexistente")


def test_limites_de_la_coleccion():
    w = World(CollectionSettings(max_documents=1, max_queue_per_collection=1, max_file_mb=1))
    ana = w.user("ana")
    col = w.new_collection("ana")
    with pytest.raises(CapacityExceeded):
        w.upload(ana, col.id, "x" * (1024 * 1024 + 1))
    w.upload(ana, col.id, "uno")
    with pytest.raises(CapacityExceeded):  # cola llena
        w.upload(ana, col.id, "dos")
    w.run_jobs()
    with pytest.raises(CapacityExceeded):  # máximo de documentos
        w.upload(ana, col.id, "tres")


def test_un_documento_con_tipo_sin_extractor_acaba_en_dead(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    res = world.upload(ana, col.id, "texto")
    # Se cambia el tipo a algo que ningún extractor admite, simulando una configuración rota
    doc = world.documents.get(col.id, res.document_id)
    world.documents._docs[(col.id, doc.id)] = dataclasses.replace(doc, source_type="pdf")
    world.run_jobs()
    job = world.queue.get(col.id, res.job.id)
    assert job.status is JobStatus.DEAD and "Sin extractor" in job.error
    assert world.documents.get(col.id, doc.id).status is DocumentStatus.FAILED


# === Pruebas obligatorias (SPEC §14) ========================================

def test_1_un_token_de_a_no_toca_nada_de_b(world):  # prueba obligatoria 1
    a = world.new_collection("ana", "A")
    b = world.new_collection("otro", "B")
    ana, otro = world.user("ana"), world.user("otro")
    secret = world.upload(otro, b.id, "dato confidencial de la colección B")
    world.run_jobs()

    token_a = world.token_actor("ana", a.id, Scope.READ, Scope.WRITE)
    ctx = world.ctx(token_a)
    with pytest.raises(PermissionDenied):
        world.search.execute(ctx, b.id, "confidencial")
    with pytest.raises(PermissionDenied):
        world.read.execute(ctx, b.id, secret.document_id)
    with pytest.raises(PermissionDenied):
        world.list_docs.execute(ctx, b.id)
    with pytest.raises(PermissionDenied):
        world.submit.execute(ctx, b.id, title="x", source_type="text", content=b"hola")
    # la búsqueda en su propia colección no ve nada de B
    assert world.search.execute(ctx, a.id, "confidencial") == []


def test_2_un_token_read_no_escribe(world):  # prueba obligatoria 2
    col = world.new_collection("ana")
    token = world.token_actor("ana", col.id, Scope.READ)
    with pytest.raises(PermissionDenied):
        world.submit.execute(
            world.ctx(token), col.id, title="x", source_type="text", content=b"hola"
        )
    assert world.queue.list(col.id, None, 10) == []


def test_6_todas_las_denegaciones_quedan_registradas(world):  # prueba obligatoria 6
    a = world.new_collection("ana")
    b = world.new_collection("otro")
    world.access.add_member("rita", a.id, Role.READER)
    token_a = world.token_actor("ana", a.id, Scope.READ)

    intentos = [
        (a.id, world.user("rita"), lambda c: world.submit.execute(c, a.id, title="x", source_type="text", content=b"y")),
        (a.id, world.user("rita"), lambda c: world.issue_token.execute(c, a.id, [Scope.READ])),
        (b.id, token_a, lambda c: world.search.execute(c, b.id, "algo")),
        (b.id, world.user("ana"), lambda c: world.list_docs.execute(c, b.id)),  # no es miembro de B
    ]
    for collection_id, actor, call in intentos:
        with pytest.raises(PermissionDenied):
            call(world.ctx(actor))
        denied = [e for e in world.log.entries(collection_id) if e.outcome is Outcome.DENIED]
        assert denied, f"sin registro de denegación en {collection_id}"
        assert denied[-1].actor.id == actor.id
        assert denied[-1].details["reason"]


def test_7_la_misma_clave_de_idempotencia_no_duplica(world):  # prueba obligatoria 7
    ana = world.user("ana")
    col = world.new_collection("ana")
    first = world.upload(ana, col.id, "contenido", idempotency_key="subida-1")
    second = world.upload(ana, col.id, "contenido", idempotency_key="subida-1")
    assert second.job.id == first.job.id
    assert len(world.queue.list(col.id, None, 10)) == 1
    assert len(world.documents.list(col.id)) == 1
    assert len(world.documents.history(col.id, first.document_id)) == 1


def test_8_ejecutar_dos_veces_un_trabajo_deja_el_mismo_estado(world):  # prueba obligatoria 8
    ana = world.user("ana")
    col = world.new_collection("ana")
    res = world.upload(ana, col.id, "uno.\n\ndos.\n\ntres.")
    job = world.queue.claim("w", 60)
    ctx = world.ctx(ana, Channel.WORKER)

    world.handler.handle(ctx, job)
    after_first = world.index.all_chunks(col.id)
    doc_first = world.documents.get(col.id, res.document_id)

    world.handler.handle(ctx, job)  # segunda ejecución del mismo trabajo
    assert world.index.all_chunks(col.id) == after_first
    assert world.documents.get(col.id, res.document_id) == doc_first
    assert len(after_first) == 3


def test_9_las_escrituras_sobre_un_documento_van_en_orden(world):  # prueba obligatoria 9
    ana = world.user("ana")
    col = world.new_collection("ana")
    res = world.upload(ana, col.id, "v1")
    world.run_jobs()
    world.upload(ana, col.id, "v2", document_id=res.document_id)
    world.upload(ana, col.id, "v3", document_id=res.document_id)

    first = world.process.execute()
    second = world.process.execute()
    assert (first.version, second.version) == (2, 3)
    assert world.documents.get(col.id, res.document_id).current_version == 3
    assert world.read.execute(world.ctx(ana), col.id, res.document_id).text == "v3"


def test_10_un_worker_que_cae_no_deja_fragmentos_huerfanos(world):  # prueba obligatoria 10
    from glosa_core.domain import Chunk

    ana = world.user("ana")
    col = world.new_collection("ana")
    res = world.upload(ana, col.id, "alfa.\n\nbeta.")

    # El worker toma el trabajo, indexa un fragmento suelto y se cae sin cerrar nada
    crashed = world.queue.claim("worker-caido", 30)
    world.index.index([Chunk("huerfano", res.document_id, 1, col.id, "restos", 99)])
    assert world.process.execute() is None  # nadie más puede tomarlo todavía

    world.clock.advance(seconds=31)  # el lease caduca
    final = world.process.execute()
    assert final.status is JobStatus.SUCCEEDED and final.attempts == 2
    ids = [c.id for c in world.index.all_chunks(col.id)]
    assert ids == [f"{res.document_id}:1:0", f"{res.document_id}:1:1"]  # sin el huérfano
    assert crashed.id == final.id


def test_11_tras_modificar_solo_se_busca_en_la_version_vigente(world):  # prueba obligatoria 11
    ana = world.user("ana")
    col = world.new_collection("ana")
    res = world.upload(ana, col.id, "El precio es de cien euros.")
    world.run_jobs()
    assert world.search.execute(world.ctx(ana), col.id, "cien")

    world.upload(ana, col.id, "El precio es de doscientos euros.", document_id=res.document_id)
    world.run_jobs()
    assert world.search.execute(world.ctx(ana), col.id, "cien") == []
    hits = world.search.execute(world.ctx(ana), col.id, "doscientos")
    assert [h.chunk.version for h in hits] == [2]


def test_12_el_correlation_id_reconstruye_la_cadena_completa(world):  # prueba obligatoria 12
    ana = world.user("ana")
    col = world.new_collection("ana")
    res = world.upload(ana, col.id, "texto de prueba")
    world.run_jobs()

    chain_ = world.log.query(col.id, OperationFilter(correlation_id=res.correlation_id), 100)
    assert actions(chain_) == [
        "document.submit",   # la petición llega por la API
        "job.start",         # el worker toma el trabajo...
        "document.extract",
        "document.chunk",
        "document.index",
        "document.ingest",
        "job.succeed",
    ]
    assert [e.channel for e in chain_][0] is Channel.API
    assert {e.channel for e in chain_[1:]} == {Channel.WORKER}
    assert all(e.actor.id == "ana" for e in chain_)


def test_13_el_registro_detecta_manipulaciones(world):  # prueba obligatoria 13
    ana = world.user("ana")
    col = world.new_collection("ana")
    world.upload(ana, col.id, "algo")
    world.run_jobs()
    world.search.execute(world.ctx(ana), col.id, "algo")
    assert world.log.verify_chain(col.id).valid

    entries = world.log._by_collection[col.id]  # acceso directo para manipularlo
    entries[3] = dataclasses.replace(entries[3], outcome=Outcome.DENIED)
    report = world.log.verify_chain(col.id)
    assert not report.valid and report.broken_at == entries[3].id


def test_14_con_hash_only_el_texto_de_la_consulta_no_llega_al_registro():  # prueba obligatoria 14
    w = World(CollectionSettings(query_logging="hash_only"))
    ana = w.user("ana")
    col = w.new_collection("ana")
    w.upload(ana, col.id, "informe del caso zeta")
    w.run_jobs()
    w.search.execute(w.ctx(ana), col.id, "zeta confidencial-xyz")

    log = dump(w.log.entries(col.id))
    assert "confidencial-xyz" not in log
    entry = [e for e in w.log.entries(col.id) if e.action == "search.execute"][0]
    assert entry.details["query_hash"] == hashlib.sha256(b"zeta confidencial-xyz").hexdigest()
    assert "query" not in entry.details


def test_con_registro_completo_el_texto_si_se_guarda(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    world.search.execute(world.ctx(ana), col.id, "mi consulta")
    entry = [e for e in world.log.entries(col.id) if e.action == "search.execute"][0]
    assert entry.details["query"] == "mi consulta"


def test_fallos_de_validacion_quedan_registrados(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    with pytest.raises(InvalidRequest):
        world.search.execute(world.ctx(ana), col.id, "   ")
    failed = [e for e in world.log.entries(col.id) if e.outcome is Outcome.FAILED]
    assert failed and failed[-1].details["kind"] == "InvalidRequest"


def test_reintentos_con_espera_creciente_y_fallo_definitivo(world):
    ana = world.user("ana")
    col = world.new_collection("ana")
    res = world.upload(ana, col.id, "texto")

    class Roto:
        def handle(self, ctx, job):
            raise RuntimeError("se cayó el disco")

    from glosa_core.domain import JobType
    from glosa_core.usecases import ProcessNextJob

    process = ProcessNextJob(world.kernel, world.queue, {JobType.INGEST: Roto()}, backoff_base_seconds=30)
    job = process.execute()
    assert job.status is JobStatus.QUEUED and job.attempts == 1
    assert process.execute() is None  # aún no toca reintentar
    world.clock.advance(seconds=31)
    assert process.execute().attempts == 2
    world.clock.advance(seconds=61)  # segunda espera: 60 s
    for _ in range(5):
        world.clock.advance(seconds=1000)
        job = process.execute() or job
    assert world.queue.get(col.id, res.job.id).status is JobStatus.DEAD
    assert "job.retry" in actions(world.log.entries(col.id))
    assert "job.dead" in actions(world.log.entries(col.id))
