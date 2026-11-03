"""Registro de adaptadores por nombre (plugins).

Un cliente con un caso especial añade su paquete y lo registra aquí, sin
bifurcar el núcleo. Los paquetes externos se descubren por entry points del
grupo `glosa.adapters`: cada uno es una función `register(registry)`.
"""
from __future__ import annotations

from importlib.metadata import entry_points
from typing import Any, Callable

from .model import Template

# Tipos de adaptador y la clave de la plantilla donde se eligen.
KINDS = ("storage", "queue", "index", "embedder", "extractors", "chunker", "authenticator")


class Registry:
    def __init__(self) -> None:
        self._factories: dict[str, dict[str, Callable[..., Any]]] = {k: {} for k in KINDS}

    def register(self, kind: str, name: str, factory: Callable[..., Any]) -> None:
        if kind not in self._factories:
            raise ValueError(f"Tipo de adaptador desconocido: {kind}")
        self._factories[kind][name] = factory

    def names(self, kind: str) -> list[str]:
        return sorted(self._factories[kind])

    def get(self, kind: str, name: str) -> Callable[..., Any]:
        return self._factories[kind][name]

    def load_entry_points(self) -> None:
        for ep in entry_points(group="glosa.adapters"):
            ep.load()(self)

    def missing(self, template: Template) -> list[str]:
        """Adaptadores que la plantilla pide y no están registrados."""
        out: list[str] = []
        for kind in KINDS:
            wanted = template.get(f"adapters.{kind}")
            names = wanted if isinstance(wanted, list) else [wanted]
            for name in names:
                if name not in self._factories[kind]:
                    out.append(f"adapters.{kind}: '{name}' no está registrado")
        return out
