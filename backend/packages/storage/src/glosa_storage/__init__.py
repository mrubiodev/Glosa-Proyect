"""Adaptadores de persistencia sobre SQLite."""
from pathlib import Path

from .access_repo import SqliteAccessRepository
from .chunk_index import SqliteChunkIndex, fts_query
from .collection_repo import SqliteCollectionRepository
from .database import Database
from .document_repo import SqliteDocumentRepository
from .job_queue import SqliteJobQueue
from .operation_log import SqliteOperationLog
from .storage import SqliteStorage

__all__ = [
    "Database",
    "SqliteAccessRepository",
    "SqliteChunkIndex",
    "SqliteCollectionRepository",
    "SqliteDocumentRepository",
    "SqliteJobQueue",
    "SqliteOperationLog",
    "SqliteStorage",
    "fts_query",
    "register",
]


def register(registry) -> None:
    """Registra los adaptadores por nombre. Se descubre solo, por el entry point.

    Convención de las fábricas, que sigue cualquier adaptador de estos tipos:
    `storage(data_dir)`, `queue(storage, clock)` e `index(storage)`.
    """
    registry.register(
        "storage", "sqlite", lambda data_dir: SqliteStorage(Path(data_dir) / "glosa.db")
    )
    registry.register("queue", "sqlite", lambda storage, clock: SqliteJobQueue(storage.db, clock))
    registry.register("index", "sqlite-fts5", lambda storage: SqliteChunkIndex(storage.db))
