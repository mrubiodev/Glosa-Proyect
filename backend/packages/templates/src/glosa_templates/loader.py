"""Carga de plantillas con herencia (`extends`)."""
from __future__ import annotations

from copy import deepcopy
from importlib import resources
from pathlib import Path
from typing import Any, Sequence

import yaml

from .errors import TemplateError
from .model import Template
from .schema import validate_schema


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Los objetos se fusionan; cualquier otro valor (listas incluidas) se reemplaza."""
    out = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = deepcopy(value)
    return out


def _read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TemplateError([f"{path}: el fichero debe contener un objeto YAML"])
    return data


def _find(ref: str, search_dirs: Sequence[Path]) -> Path:
    candidate = Path(ref)
    if candidate.suffix in {".yaml", ".yml"} and candidate.exists():
        return candidate
    # Los presets van primero: un fichero de cliente no puede ocultar a "profesional".
    preset = resources.files("glosa_templates") / "presets" / f"{ref}.yaml"
    if preset.is_file():
        return Path(str(preset))
    for directory in search_dirs:
        for suffix in (".yaml", ".yml"):
            path = Path(directory) / f"{ref}{suffix}"
            if path.exists():
                return path
    raise TemplateError([f"No se encuentra la plantilla '{ref}'"])


def _resolve(ref: str, search_dirs: Sequence[Path], chain: tuple[str, ...]) -> dict[str, Any]:
    path = _find(ref, search_dirs)
    key = str(path.resolve())
    if key in chain:
        raise TemplateError(["Herencia circular: " + " -> ".join((*chain, key))])
    data = _read_yaml(path)
    parent_ref = data.get("extends")
    if parent_ref:
        parent = _resolve(parent_ref, search_dirs, (*chain, key))
        data = deep_merge(parent, data)
    return data


def load_template(ref: str | Path, search_dirs: Sequence[str | Path] = ()) -> Template:
    """Carga una plantilla por nombre (preset o fichero en `search_dirs`) o por ruta.

    Aplica la herencia, valida el esquema y devuelve la plantilla resuelta.
    """
    dirs = [Path(d) for d in search_dirs]
    data = _resolve(str(ref), dirs, ())
    data.pop("extends", None)
    problems = validate_schema({**data, "extends": None})
    if problems:
        raise TemplateError(problems)
    return Template(name=data["name"], mode=data["mode"], data=data)
