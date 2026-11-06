"""Adaptadores de persistencia sobre SQLite."""
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
    """Registra los adaptadores por nombre. Se descubre solo, por el entry point."""
    registry.register("storage", "sqlite", SqliteStorage)
    registry.register("queue", "sqlite", SqliteJobQueue)
    registry.register("index", "sqlite-fts5", SqliteChunkIndex)
