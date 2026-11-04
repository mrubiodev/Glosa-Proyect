"""Implementaciones reales de los puertos Clock e IdGenerator (solo librería estándar)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class UuidIds:
    """Identificadores con prefijo legible y parte aleatoria: `doc-3f9a1c0b7d2e`."""

    def new_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4().hex[:12]}"
