"""Guardia del modo producción (SPEC §18.4).

Una plantilla en modo `production` se niega a arrancar si trae credenciales de
demo, registro completo de consultas, secretos escritos en el fichero, etc.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from .errors import TemplateError
from .model import Template

_SECRET_KEY = re.compile(r"(secret|password|passwd|token|api_?key)", re.IGNORECASE)
_ENV_REF = re.compile(r"^\$\{[A-Z_][A-Z0-9_]*\}$")


def find_inline_secrets(data: Mapping[str, Any], path: str = "") -> list[str]:
    """Claves que parecen secretos con un valor literal (no `${VARIABLE}`)."""
    found: list[str] = []
    for key, value in data.items():
        here = f"{path}.{key}" if path else key
        if isinstance(value, Mapping):
            found += find_inline_secrets(value, here)
        elif isinstance(value, str) and _SECRET_KEY.search(key) and not _ENV_REF.match(value):
            found.append(here)
    return found


def validate_production(template: Template) -> None:
    """Lanza TemplateError con todos los problemas. No hace nada en modo didáctico."""
    if not template.is_production:
        return
    t = template
    problems: list[str] = []

    if t.get("demo.seed_data"):
        problems.append("demo.seed_data debe ser false en producción")
    if t.get("demo.demo_token"):
        problems.append("demo.demo_token debe ser false en producción")
    if t.get("policy.query_logging") != "hash_only":
        problems.append("policy.query_logging debe ser 'hash_only' en producción")
    if t.get("policy.hash_chain") is not True:
        problems.append("policy.hash_chain debe ser true en producción")
    retention = t.get("policy.retention_days")
    if not isinstance(retention, int) or isinstance(retention, bool) or retention <= 0:
        problems.append("policy.retention_days debe ser un número de días mayor que 0")
    for path in find_inline_secrets(t.data):
        problems.append(f"{path}: los secretos van en variables de entorno (${{NOMBRE}}), no en la plantilla")

    if problems:
        raise TemplateError(problems)
