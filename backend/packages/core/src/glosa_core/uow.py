"""Unidad de trabajo sin transacciones, para los dobles en memoria."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator


class NoTransaction:
    """Implementa UnitOfWork sin hacer nada: los dobles en memoria no tienen rollback."""

    @contextmanager
    def transaction(self) -> Iterator[None]:
        yield
