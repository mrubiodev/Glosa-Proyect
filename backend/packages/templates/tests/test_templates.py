from pathlib import Path

import pytest
import yaml

from glosa_templates import Registry, TemplateError, load_template, validate_production
from glosa_templates.guard import find_inline_secrets
from glosa_templates.loader import deep_merge

EXAMPLES = Path(__file__).resolve().parents[3] / "examples" / "templates"


def write(tmp_path: Path, name: str, content: dict) -> Path:
    path = tmp_path / f"{name}.yaml"
    path.write_text(yaml.safe_dump(content, allow_unicode=True), encoding="utf-8")
    return path


# --- Presets y herencia ---------------------------------------------------

def test_didactico_se_carga_y_es_modo_didactico():
    t = load_template("didactico")
    assert t.mode == "didactic"
    assert t.get("policy.query_logging") == "full"
    assert t.get("branding.didactic_panels") is True
    assert t.get("demo.demo_token") is True


def test_profesional_hereda_y_endurece():
    t = load_template("profesional")
    assert t.is_production
    assert t.get("policy.query_logging") == "hash_only"
    assert t.get("demo.demo_token") is False
    # lo no tocado se hereda
    assert t.get("adapters.chunker") == "headings"
    assert t.get("policy.limits.max_file_mb") == 25


def test_el_preset_profesional_pasa_la_guardia_de_produccion():
    validate_production(load_template("profesional"))


def test_plantilla_de_cliente_hereda_de_profesional(tmp_path):
    write(tmp_path, "acme", {
        "name": "acme-legal",
        "extends": "profesional",
        "mcp": {"tools": {"buscar": "Busca cláusulas en los contratos de Acme"}},
        "metadata": ["fecha_contrato", "jurisdiccion"],
    })
    t = load_template("acme", search_dirs=[tmp_path])
    assert t.name == "acme-legal"
    assert t.get("mcp.tools.buscar").startswith("Busca cláusulas")
    # el resto de herramientas conserva su descripción heredada
    assert t.get("mcp.tools.listar_documentos").lower().startswith("lista")
    assert t.get("metadata") == ["fecha_contrato", "jurisdiccion"]
    assert t.get("policy.query_logging") == "hash_only"
    validate_production(t)


def test_las_listas_se_reemplazan_no_se_concatenan():
    merged = deep_merge({"a": [1, 2], "b": {"x": 1, "y": 2}}, {"a": [3], "b": {"y": 9}})
    assert merged == {"a": [3], "b": {"x": 1, "y": 9}}


def test_herencia_circular_se_detecta(tmp_path):
    write(tmp_path, "a", {"name": "a", "extends": "b"})
    write(tmp_path, "b", {"name": "b", "extends": "a"})
    with pytest.raises(TemplateError, match="circular"):
        load_template("a", search_dirs=[tmp_path])


def test_plantilla_inexistente(tmp_path):
    with pytest.raises(TemplateError, match="No se encuentra"):
        load_template("no-existe", search_dirs=[tmp_path])


def test_un_fichero_de_cliente_no_puede_ocultar_un_preset(tmp_path):
    write(tmp_path, "profesional", {"name": "falso", "mode": "didactic"})
    assert load_template("profesional", search_dirs=[tmp_path]).name == "profesional"


# --- Esquema: lo no declarado no existe -----------------------------------

def test_los_invariantes_de_seguridad_no_son_configurables(tmp_path):
    write(tmp_path, "mala", {
        "name": "mala",
        "extends": "profesional",
        "security": {"collection_isolation": False},
        "policy": {"append_only_log": False},
    })
    with pytest.raises(TemplateError) as exc:
        load_template("mala", search_dirs=[tmp_path])
    assert any("security" in p for p in exc.value.problems)
    assert any("policy.append_only_log" in p for p in exc.value.problems)


def test_valores_invalidos_se_listan_todos_juntos(tmp_path):
    write(tmp_path, "rota", {
        "name": "rota",
        "extends": "didactico",
        "retrieval": {"strategy": "magia", "k": "cinco"},
        "branding": {"primary_color": "azul"},
        "mcp": {"tools": {"borrar_todo": "no"}},
    })
    with pytest.raises(TemplateError) as exc:
        load_template("rota", search_dirs=[tmp_path])
    text = "\n".join(exc.value.problems)
    assert "retrieval.strategy" in text
    assert "retrieval.k" in text
    assert "branding.primary_color" in text
    assert "mcp.tools.borrar_todo" in text


# --- Guardia de producción ------------------------------------------------

def production(tmp_path, **overrides):
    content = {"name": "cli", "extends": "profesional", **overrides}
    write(tmp_path, "cli", content)
    return load_template("cli", search_dirs=[tmp_path])


def test_produccion_rechaza_registro_completo_de_consultas(tmp_path):
    t = production(tmp_path, policy={"query_logging": "full"})
    with pytest.raises(TemplateError, match="query_logging"):
        validate_production(t)


def test_produccion_rechaza_credenciales_de_demo(tmp_path):
    t = production(tmp_path, demo={"demo_token": True, "seed_data": True})
    with pytest.raises(TemplateError) as exc:
        validate_production(t)
    assert len(exc.value.problems) == 2


def test_produccion_exige_retencion_y_cadena_de_hashes(tmp_path):
    t = production(tmp_path, policy={"retention_days": None, "hash_chain": False})
    with pytest.raises(TemplateError) as exc:
        validate_production(t)
    text = "\n".join(exc.value.problems)
    assert "retention_days" in text and "hash_chain" in text


def test_la_guardia_no_aplica_en_modo_didactico():
    validate_production(load_template("didactico"))  # registro completo + demo: permitido


def test_detecta_secretos_escritos_en_el_fichero():
    data = {"auth": {"client_secret": "abc123", "api_key": "${API_KEY}", "name": "x"}}
    assert find_inline_secrets(data) == ["auth.client_secret"]


# --- Registro de adaptadores ----------------------------------------------

def test_registro_detecta_adaptadores_no_registrados():
    reg = Registry()
    t = load_template("didactico")
    missing = reg.missing(t)
    assert any("adapters.storage: 'sqlite'" in m for m in missing)


def test_registro_sin_faltantes_cuando_todo_esta_registrado():
    reg = Registry()
    t = load_template("didactico")
    reg.register("storage", "sqlite", object)
    reg.register("queue", "sqlite", object)
    reg.register("index", "sqlite-fts5", object)
    reg.register("embedder", "none", object)
    reg.register("extractors", "markdown", object)
    reg.register("extractors", "text", object)
    reg.register("chunker", "headings", object)
    reg.register("authenticator", "token", object)
    assert reg.missing(t) == []


def test_registro_rechaza_tipos_desconocidos():
    with pytest.raises(ValueError):
        Registry().register("inventado", "x", object)


# --- Ejemplo incluido en el repositorio -----------------------------------

def test_la_plantilla_de_ejemplo_es_valida_y_pasa_la_guardia():
    t = load_template("acme-legal", search_dirs=[EXAMPLES])
    assert t.is_production
    validate_production(t)
