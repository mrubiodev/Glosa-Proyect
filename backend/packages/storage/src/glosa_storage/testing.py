"""Utilidades para probar con SQLite.

`make_adapters` es lo que usa `GLOSA_TEST_ADAPTERS=glosa_storage.testing:make_adapters` para
ejecutar toda la batería de tests de `core` contra estos adaptadores en lugar de los dobles en
memoria. Las clases `...WithHooks` solo añaden lo que los tests necesitan para inspeccionar o
manipular el estado; el código de producción no las usa.
"""
from __future__ import annotations

from glosa_core.domain import Chunk, OperationEntry, OperationFilter

from . import (
    Database,
    SqliteAccessRepository,
    SqliteChunkIndex,
    SqliteCollectionRepository,
    SqliteDocumentRepository,
    SqliteJobQueue,
    SqliteOperationLog,
)
from .chunk_index import _chunk


class ChunkIndexWithHooks(SqliteChunkIndex):
    def all_chunks(self, collection_id: str) -> list[Chunk]:
        rows = self._db.conn().execute(
            "SELECT * FROM chunks WHERE collection_id = ? ORDER BY id", (collection_id,)
        ).fetchall()
        return [_chunk(r) for r in rows]


class OperationLogWithHooks(SqliteOperationLog):
    def entries(self, collection_id: str | None) -> list[OperationEntry]:
        return self.query(collection_id, OperationFilter(), 10**9)

    def tamper(self, collection_id: str, index: int, **changes) -> str:
        """Altera una entrada ya guardada saltándose el adaptador, como haría un atacante."""
        allowed = {"outcome", "action"}
        if not set(changes) <= allowed:
            raise ValueError(f"Solo se pueden manipular {allowed}")
        entry = self.entries(collection_id)[index]
        for column, value in changes.items():
            self._db.conn().execute(
                f"UPDATE operations SET {column} = ? WHERE id = ?", (getattr(value, "value", value), entry.id)
            )
        return entry.id


class DocumentRepositoryWithHooks(SqliteDocumentRepository):
    def force_source_type(self, collection_id: str, doc_id: str, source_type: str) -> None:
        self._db.conn().execute(
            "UPDATE documents SET source_type = ? WHERE collection_id = ? AND id = ?",
            (source_type, collection_id, doc_id),
        )


def make_adapters(clock, path: str = ":memory:") -> dict:
    db = Database(path)
    return {
        "access": SqliteAccessRepository(db),
        "collections": SqliteCollectionRepository(db),
        "documents": DocumentRepositoryWithHooks(db),
        "index": ChunkIndexWithHooks(db),
        "queue": SqliteJobQueue(db, clock),
        "log": OperationLogWithHooks(db),
        "uow": db,
    }
