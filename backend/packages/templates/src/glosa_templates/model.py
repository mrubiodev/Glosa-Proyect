from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class Template:
    """Plantilla ya resuelta (herencia aplicada) y validada."""

    name: str
    mode: str  # "didactic" | "production"
    data: Mapping[str, Any]

    def get(self, path: str, default: Any = None) -> Any:
        """Acceso por ruta con puntos: `t.get("policy.query_logging")`."""
        node: Any = self.data
        for part in path.split("."):
            if not isinstance(node, Mapping) or part not in node:
                return default
            node = node[part]
        return node

    @property
    def is_production(self) -> bool:
        return self.mode == "production"
