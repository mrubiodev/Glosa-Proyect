from pathlib import Path

import pytest

from glosa_app.cli import main

EXAMPLES = str(Path(__file__).resolve().parents[2] / "examples" / "templates")


def test_didactico_es_valido_por_defecto(capsys):
    assert main(["check"], env={}) == 0
    out = capsys.readouterr().out
    assert "didactico" in out and "Plantilla válida" in out


def test_profesional_pasa_la_guardia(capsys):
    assert main(["check"], env={"GLOSA_TEMPLATE": "profesional"}) == 0
    assert "production" in capsys.readouterr().out


def test_plantilla_de_cliente_desde_una_carpeta(capsys):
    env = {"GLOSA_TEMPLATE": "acme-legal", "GLOSA_TEMPLATE_DIRS": EXAMPLES}
    assert main(["check"], env=env) == 0
    assert "acme-legal" in capsys.readouterr().out


def test_plantilla_inexistente_falla_con_mensaje(capsys):
    assert main(["check"], env={"GLOSA_TEMPLATE": "no-existe"}) == 1
    assert "No se encuentra" in capsys.readouterr().err


def test_produccion_insegura_no_arranca(tmp_path, capsys):
    (tmp_path / "insegura.yaml").write_text(
        "name: insegura\nextends: profesional\npolicy:\n  query_logging: full\n", encoding="utf-8"
    )
    env = {"GLOSA_TEMPLATE": "insegura", "GLOSA_TEMPLATE_DIRS": str(tmp_path)}
    assert main(["check"], env=env) == 1
    assert "query_logging" in capsys.readouterr().err


def test_strict_falla_mientras_no_haya_adaptadores(capsys):
    assert main(["check", "--strict"], env={}) == 1
    assert "no está registrado" in capsys.readouterr().err


def test_sin_orden_el_parser_exige_una(capsys):
    with pytest.raises(SystemExit):
        main([], env={})
