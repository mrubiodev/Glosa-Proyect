from __future__ import annotations

import hashlib
import json
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

    def fingerprint(self) -> str:
        """Huella estable de la plantilla ya resuelta (herencia aplicada).

        Sirve para dejar en el registro QUÉ configuración estaba activa al arrancar: dos
        plantillas con los mismos valores dan la misma huella, y cualquier cambio la altera.
        """
        canonical = json.dumps(
            self.data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @property
    def is_production(self) -> bool:
        return self.mode == "production"
