"""Hace cumplir las reglas de dependencia de SPEC §5.

Si un paquete importa algo que no le toca, este test falla.
"""
import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

# módulo Python -> carpeta del componente
COMPONENTS = {
    "glosa_core": "packages/core",
    "glosa_ingest": "packages/ingest",
    "glosa_retrieval": "packages/retrieval",
    "glosa_storage": "packages/storage",
    "glosa_explain": "packages/explain",
    "glosa_templates": "packages/templates",
    "glosa_http_api": "adapters/http-api",
    "glosa_mcp_server": "adapters/mcp-server",
    "glosa_worker": "adapters/worker",
    "glosa_app": "app",
}

# Qué puede importar cada componente (aparte de sí mismo y la librería estándar)
ALLOWED = {
    "glosa_core": set(),
    "glosa_ingest": {"glosa_core"},
    "glosa_retrieval": {"glosa_core"},
    "glosa_storage": {"glosa_core"},
    "glosa_explain": {"glosa_core"},
    "glosa_templates": {"glosa_core"},
    "glosa_http_api": {"glosa_core"},
    "glosa_mcp_server": {"glosa_core"},
    "glosa_worker": {"glosa_core"},
    "glosa_app": set(COMPONENTS),  # la composición puede importar todo
}


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module.split(".")[0])
    return found


def test_las_dependencias_respetan_la_arquitectura():
    violations = []
    for module, folder in COMPONENTS.items():
        for py in (BACKEND / folder / "src").rglob("*.py"):
            for imported in imported_modules(py):
                if not imported.startswith("glosa_") or imported == module:
                    continue
                if imported not in ALLOWED[module]:
                    violations.append(f"{py.relative_to(BACKEND)} importa {imported}")
    assert not violations, "\n".join(violations)


def test_core_no_importa_nada_externo():
    external = set()
    for py in (BACKEND / "packages/core/src").rglob("*.py"):
        external |= {m for m in imported_modules(py) if not m.startswith("glosa_")}
    stdlib = {
        "__future__", "dataclasses", "datetime", "enum", "typing", "hashlib",
        "json", "secrets",
    }
    assert external <= stdlib, f"core importa fuera de la librería estándar: {external - stdlib}"
