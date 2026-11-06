"""Conexión a SQLite, migraciones y transacciones.

`Database` implementa el puerto UnitOfWork de `core`: todos los adaptadores comparten la
misma base de datos, así que una transacción abarca documento, versión, índice, cola y
registro a la vez.
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .schema import MIGRATIONS


def _statements(script: str) -> Iterator[str]:
    """Separa un guion SQL en sentencias, respetando los `;` dentro de los triggers."""
    buffer = ""
    for line in script.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            if buffer.strip():
                yield buffer.strip()
            buffer = ""
    if buffer.strip():
        yield buffer.strip()


class Database:
    def __init__(self, path: str | Path = ":memory:", busy_timeout_ms: int = 5000) -> None:
        self._path = str(path)
        self._memory = self._path == ":memory:"
        self._busy_timeout_ms = busy_timeout_ms
        self._local = threading.local()
        # En memoria cada conexión sería una base distinta: se comparte una sola
        self._shared = self._connect() if self._memory else None
        self.migrate()

    # --- conexiones ---------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self._path,
            isolation_level=None,  # las transacciones las gestionamos nosotros
            check_same_thread=not self._memory,
        )
        conn.row_factory = sqlite3.Row
        conn.execute(f"PRAGMA busy_timeout = {int(self._busy_timeout_ms)}")
        conn.execute("PRAGMA foreign_keys = ON")
        if not self._memory:
            conn.execute("PRAGMA journal_mode = WAL")  # lectores y escritor a la vez
            conn.execute("PRAGMA synchronous = NORMAL")
        return conn

    def conn(self) -> sqlite3.Connection:
        """Conexión de este hilo (una por hilo, porque SQLite no las comparte)."""
        if self._shared is not None:
            return self._shared
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = self._local.conn = self._connect()
        return conn

    def close(self) -> None:
        conn = self._shared or getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None
            self._shared = None if self._memory else self._shared

    # --- migraciones ------------------------------------------------------------

    def migrate(self) -> None:
        conn = self.conn()
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version > len(MIGRATIONS):
            raise RuntimeError(
                f"La base de datos es de una versión más nueva ({version}) que este programa "
                f"({len(MIGRATIONS)})"
            )
        for number in range(version, len(MIGRATIONS)):
            conn.execute("BEGIN IMMEDIATE")
            try:
                for statement in _statements(MIGRATIONS[number]):
                    conn.execute(statement)
                conn.execute(f"PRAGMA user_version = {number + 1}")
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    # --- transacciones (puerto UnitOfWork) -----------------------------------------

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Todo lo de dentro se confirma junto o no se confirma. Las anidadas se unen."""
        depth = getattr(self._local, "depth", 0)
        if depth > 0:
            self._local.depth = depth + 1
            try:
                yield
            finally:
                self._local.depth -= 1
            return

        conn = self.conn()
        conn.execute("BEGIN IMMEDIATE")  # toma el bloqueo de escritura desde el principio
        self._local.depth = 1
        try:
            yield
            try:
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            self._local.depth = 0
