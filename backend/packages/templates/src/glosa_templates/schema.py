"""Esquema de las plantillas.

Todo lo que no esté aquí es una clave desconocida y se rechaza. Los
invariantes de seguridad (aislamiento por colección, autorización única,
registro de solo añadir) NO aparecen a propósito: no son configurables.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Choice:
    options: tuple[str, ...]


@dataclass(frozen=True)
class ListOf:
    item: type


@dataclass(frozen=True)
class MapOf:
    """Diccionario con claves permitidas y valores de un tipo."""

    keys: tuple[str, ...]
    value: type


@dataclass(frozen=True)
class Optional:
    inner: Any


@dataclass(frozen=True)
class Pattern:
    regex: str


SCHEMA: dict[str, Any] = {
    "name": str,
    "extends": Optional(str),
    "mode": Choice(("didactic", "production")),
    "adapters": {
        "storage": str,
        "queue": str,
        "index": str,
        "embedder": str,
        "extractors": ListOf(str),
        "chunker": str,
        "authenticator": str,
    },
    "retrieval": {
        "strategy": Choice(("text", "vector", "hybrid")),
        "k": int,
        "reranker": Optional(str),
    },
    "mcp": {
        "language": str,
        # Solo se puede cambiar la descripción; el nombre de las herramientas es fijo.
        "tools": MapOf(("buscar", "leer_documento", "listar_documentos"), str),
    },
    "policy": {
        "query_logging": Choice(("full", "hash_only")),
        "retention_days": Optional(int),
        "version_retention": Choice(("all", "last_n")),
        "version_keep": Optional(int),
        "hash_chain": bool,
        "token_default_ttl_days": Optional(int),
        "limits": {
            "max_file_mb": int,
            "max_documents": int,
            "max_queue_per_collection": int,
        },
    },
    "metadata": ListOf(str),
    "branding": {
        "name": str,
        "logo": Optional(str),
        "primary_color": Pattern(r"^#[0-9a-fA-F]{6}$"),
        "language": str,
        "didactic_panels": bool,
    },
    "evaluation": {"dataset": Optional(str)},
    "demo": {"seed_data": bool, "demo_token": bool},
}


def validate_schema(data: dict[str, Any]) -> list[str]:
    """Devuelve la lista de problemas (vacía si es válida)."""
    problems: list[str] = []
    _check(data, SCHEMA, "", problems)
    return problems


def _check(value: Any, spec: Any, path: str, problems: list[str]) -> None:
    where = path or "(raíz)"
    if isinstance(spec, dict):
        if not isinstance(value, dict):
            problems.append(f"{where}: debe ser un objeto")
            return
        for key in value:
            if key not in spec:
                problems.append(f"{_join(path, key)}: clave desconocida")
        for key, sub in spec.items():
            if key in value:
                _check(value[key], sub, _join(path, key), problems)
        return
    if isinstance(spec, Optional):
        if value is not None:
            _check(value, spec.inner, path, problems)
        return
    if isinstance(spec, Choice):
        if value not in spec.options:
            problems.append(f"{where}: debe ser uno de {list(spec.options)}, no {value!r}")
        return
    if isinstance(spec, Pattern):
        if not isinstance(value, str) or not re.match(spec.regex, value):
            problems.append(f"{where}: formato inválido ({value!r})")
        return
    if isinstance(spec, ListOf):
        if not isinstance(value, list) or not all(isinstance(v, spec.item) for v in value):
            problems.append(f"{where}: debe ser una lista de {spec.item.__name__}")
        return
    if isinstance(spec, MapOf):
        if not isinstance(value, dict):
            problems.append(f"{where}: debe ser un objeto")
            return
        for key, v in value.items():
            if key not in spec.keys:
                problems.append(f"{_join(path, key)}: clave desconocida (permitidas: {list(spec.keys)})")
            elif not isinstance(v, spec.value):
                problems.append(f"{_join(path, key)}: debe ser {spec.value.__name__}")
        return
    # tipo simple (bool es subclase de int: se distingue a mano)
    if spec is int and isinstance(value, bool):
        problems.append(f"{where}: debe ser int")
    elif not isinstance(value, spec):
        problems.append(f"{where}: debe ser {spec.__name__}")


def _join(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key
