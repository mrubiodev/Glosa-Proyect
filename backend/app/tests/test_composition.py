"""La composición: de una plantilla a un sistema que funciona."""
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from glosa_app.cli import main, worker
from glosa_app.composition import (
    ConfigurationError, build_app, build_from_env, default_registry, settings_from_template,
)
from glosa_core.domain import (
    Actor, ActorKind, Channel, Credentials, JobStatus, OperationFilter, Scope,
)
from glosa_explain import build_trace
from glosa_templates import Registry, TemplateError, load_template

EXAMPLES = str(Path(__file__).resolve().parents[2] / "examples" / "templates")
CONTRATO = "# Contrato\n\n## Rescisión\n\nCualquiera de las partes podrá rescindir con preaviso."
ANA = Actor(ActorKind.USER, "ana")


def env_for(tmp_path, template="didactico", **extra):
    return {"GLOSA_TEMPLATE": template, "GLOSA_DATA_DIR": str(tmp_path / "data"), **extra}


@pytest.fixture
def app(tmp_path):
    glosa = build_from_env(env_for(tmp_path))
    yield glosa
    glosa.close()


def upload(app, collection_id, text=CONTRATO, **kw):
    return app.submit.execute(
        app.context(ANA), collection_id, title="Contrato", source_type="markdown",
        content=text.encode(), **kw,
    )


# --- Construcción -----------------------------------------------------------------

def test_se_construye_y_crea_la_base_en_la_carpeta_de_datos(tmp_path):
    glosa = build_from_env(env_for(tmp_path))
    assert (tmp_path / "data" / "glosa.db").exists()
    assert glosa.template.name == "didactico"
    glosa.close()


def test_los_ajustes_de_las_colecciones_salen_de_la_politica_de_la_plantilla(tmp_path):
    glosa = build_from_env(env_for(tmp_path, "profesional"))
    s = glosa.settings
    assert (s.query_logging, s.retention_days, s.hash_chain) == ("hash_only", 365, True)
    assert (s.max_file_mb, s.max_documents, s.max_queue_per_collection) == (25, 10000, 500)
    col = glosa.create_collection.execute(glosa.context(ANA), "Docs")
    assert glosa.storage.collections.get(col.id).settings == s  # la colección nace con ellos
    glosa.close()


def test_los_ajustes_dependen_de_la_plantilla_elegida(tmp_path):
    didactico = settings_from_template(load_template("didactico"))
    profesional = settings_from_template(load_template("profesional"))
    assert didactico.query_logging == "full" and profesional.query_logging == "hash_only"


def test_una_plantilla_de_cliente_aplica_sus_propios_valores(tmp_path):
    env = env_for(tmp_path, "acme-legal", GLOSA_TEMPLATE_DIRS=EXAMPLES)
    glosa = build_from_env(env)
    assert glosa.template.name == "acme-legal" and glosa.settings.retention_days == 730
    glosa.close()


def test_una_plantilla_de_produccion_insegura_no_arranca(tmp_path):
    bad = tmp_path / "templates"
    bad.mkdir()
    (bad / "insegura.yaml").write_text(
        "name: insegura\nextends: profesional\ndemo:\n  demo_token: true\n", encoding="utf-8"
    )
    env = env_for(tmp_path, "insegura", GLOSA_TEMPLATE_DIRS=str(bad))
    with pytest.raises(TemplateError, match="demo_token"):
        build_from_env(env)
    assert not (tmp_path / "data" / "glosa.db").exists()  # ni siquiera creó la base


def test_si_falta_un_adaptador_se_dice_cual(tmp_path):
    with pytest.raises(ConfigurationError) as exc:
        build_app(load_template("didactico"), data_dir=tmp_path, registry=Registry())
    assert any("'sqlite'" in p for p in exc.value.problems)
    assert any("'markdown'" in p for p in exc.value.problems)


def test_el_registro_por_defecto_trae_todos_los_adaptadores_de_los_presets():
    for preset in ("didactico", "profesional"):
        assert default_registry().missing(load_template(preset)) == []


def test_el_k_de_la_plantilla_es_el_limite_de_busqueda_por_defecto(tmp_path):
    custom = tmp_path / "templates"
    custom.mkdir()
    (custom / "dos.yaml").write_text("name: dos\nextends: didactico\nretrieval:\n  k: 2\n", encoding="utf-8")
    glosa = build_from_env(env_for(tmp_path, "dos", GLOSA_TEMPLATE_DIRS=str(custom)))
    col = glosa.create_collection.execute(glosa.context(ANA), "Docs")
    for i in range(4):
        glosa.submit.execute(
            glosa.context(ANA), col.id, title=f"D{i}", source_type="text",
            content=f"palabra comun {i}".encode(),
        )
    while glosa.process_next_job.execute():
        pass
    assert len(glosa.search.execute(glosa.context(ANA), col.id, "palabra")) == 2
    glosa.close()


def test_la_caducidad_de_los_tokens_sale_de_la_plantilla(tmp_path):
    glosa = build_from_env(env_for(tmp_path, "profesional"))  # 90 días
    col = glosa.create_collection.execute(glosa.context(ANA), "Docs")
    issued = glosa.issue_token.execute(glosa.context(ANA), col.id, [Scope.READ])
    days = (issued.token.expires_at - datetime.now(timezone.utc)).total_seconds() / 86400
    assert 89.99 < days < 90.01
    glosa.close()


# --- Registro de arranque ---------------------------------------------------------

def test_el_arranque_deja_constancia_de_la_plantilla_activa(tmp_path):
    glosa = build_from_env(env_for(tmp_path, "profesional"))
    entries = glosa.storage.log.query(None, OperationFilter(), 10)
    glosa.close()
    assert [e.action for e in entries] == ["template.applied"]
    entry = entries[0]
    assert entry.actor.kind is ActorKind.SYSTEM and entry.channel is Channel.SYSTEM
    assert entry.details == {
        "name": "profesional", "mode": "production",
        "fingerprint": load_template("profesional").fingerprint(),
    }


def test_cada_arranque_se_anota_y_la_cadena_sigue_siendo_valida(tmp_path):
    env = env_for(tmp_path)
    for _ in range(3):
        build_from_env(env).close()
    glosa = build_from_env(env)
    assert len(glosa.storage.log.query(None, OperationFilter(), 10)) == 4
    assert glosa.storage.log.verify_chain(None).valid
    glosa.close()


def test_cambiar_de_plantilla_cambia_la_huella_que_queda_escrita(tmp_path):
    a = build_from_env(env_for(tmp_path, "didactico"))
    a.close()
    b = build_from_env(env_for(tmp_path, "profesional"))
    prints = [e.details["fingerprint"] for e in b.storage.log.query(None, OperationFilter(), 10)]
    b.close()
    assert len(prints) == 2 and prints[0] != prints[1]


def test_el_sistema_no_tiene_permisos_sobre_ninguna_coleccion(app):
    col = app.create_collection.execute(app.context(ANA), "Docs")
    from glosa_core.authorization import Permission
    system = Actor(ActorKind.SYSTEM, "system")
    assert app.kernel.authz.permissions_of(system, col.id) == frozenset()
    assert Permission.SEARCH not in app.kernel.authz.permissions_of(system, col.id)


# --- Recorrido completo con el sistema compuesto ----------------------------------------

def test_subir_procesar_buscar_y_ver_la_traza(app):
    col = app.create_collection.execute(app.context(ANA), "Contratos")
    res = upload(app, col.id)
    assert app.process_next_job.execute().status is JobStatus.SUCCEEDED

    hits = app.search.execute(app.context(ANA), col.id, "RESCISION")  # sin tilde
    assert hits and hits[0].chunk.metadata["heading_path"] == "Contrato > Rescisión"

    trace = build_trace(app.view_trace.execute(app.context(ANA), col.id, res.correlation_id))
    assert trace.outcome == "succeeded" and trace.channels == ("api", "worker")
    assert trace.steps[0].title == "Se recibió el documento"
    assert app.verify_operations.execute(app.context(ANA), col.id).valid


def test_un_token_emitido_funciona_con_el_autenticador_de_la_plantilla(app):
    col = app.create_collection.execute(app.context(ANA), "Docs")
    upload(app, col.id)
    app.process_next_job.execute()
    issued = app.issue_token.execute(app.context(ANA), col.id, [Scope.READ])
    actor = app.authenticator.identify(Credentials(issued.raw))
    assert actor is not None
    assert app.search.execute(app.context(actor, Channel.MCP), col.id, "rescindir")


# --- El worker como proceso aparte ----------------------------------------------------------

def test_worker_once_procesa_lo_que_otro_proceso_dejo_en_cola(tmp_path, capsys):
    env = env_for(tmp_path)
    api = build_from_env(env)  # "la API": sube el documento y se cierra
    col = api.create_collection.execute(api.context(ANA), "Contratos")
    res = upload(api, col.id)
    assert api.get_job.execute(api.context(ANA), col.id, res.job.id).status is JobStatus.QUEUED
    api.close()

    assert main(["worker", "--once"], env=env) == 0  # "el worker": otra instancia sobre la misma base
    out = capsys.readouterr().out
    assert "Trabajos procesados: 1" in out and "plantilla didactico" in out

    after = build_from_env(env)
    assert after.get_job.execute(after.context(ANA), col.id, res.job.id).status is JobStatus.SUCCEEDED
    assert after.search.execute(after.context(ANA), col.id, "preaviso")
    trace = build_trace(after.view_trace.execute(after.context(ANA), col.id, res.correlation_id))
    assert trace.outcome == "succeeded" and trace.channels == ("api", "worker")
    after.close()


def test_worker_once_sin_trabajos_termina_enseguida(tmp_path, capsys):
    assert main(["worker", "--once"], env=env_for(tmp_path)) == 0
    assert "Trabajos procesados: 0" in capsys.readouterr().out


def test_worker_con_una_plantilla_invalida_sale_con_error_y_mensaje(tmp_path, capsys):
    assert main(["worker", "--once"], env=env_for(tmp_path, "no-existe")) == 1
    assert "No se encuentra" in capsys.readouterr().err


def test_el_worker_se_queda_esperando_procesa_lo_nuevo_y_para_ordenadamente(tmp_path, capsys):
    env = env_for(tmp_path)
    api = build_from_env(env)
    col = api.create_collection.execute(api.context(ANA), "Docs")

    stop = threading.Event()
    result: list[int] = []
    t = threading.Thread(
        target=lambda: result.append(
            worker(env, idle_seconds=0.01, stop=stop, install_signals=False)
        )
    )
    t.start()
    try:
        time.sleep(0.1)  # el worker ya está vivo y esperando
        res = upload(api, col.id)  # llega trabajo mientras espera
        deadline = time.monotonic() + 5
        status = None
        while time.monotonic() < deadline:
            status = api.get_job.execute(api.context(ANA), col.id, res.job.id).status
            if status is JobStatus.SUCCEEDED:
                break
            time.sleep(0.02)
        assert status is JobStatus.SUCCEEDED
    finally:
        stop.set()
        t.join(timeout=5)
    assert not t.is_alive() and result == [0]
    assert "Trabajos procesados: 1" in capsys.readouterr().out
    api.close()
