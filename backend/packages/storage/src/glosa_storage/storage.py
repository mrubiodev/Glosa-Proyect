from __future__ import annotations

from pathlib import Path

from .access_repo import SqliteAccessRepository
from .collection_repo import SqliteCollectionRepository
from .database import Database
from .document_repo import SqliteDocumentRepository
from .operation_log import SqliteOperationLog


class SqliteStorage:
    """Paquete de adaptadores de persistencia sobre una misma base de datos.

    La plantilla lo pide con `adapters.storage: sqlite`. La cola y el índice de texto se piden
    por separado (`queue: sqlite`, `index: sqlite-fts5`) y se construyen con `storage.db`.
    """

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.db = Database(path)
        self.collections = SqliteCollectionRepository(self.db)
        self.access = SqliteAccessRepository(self.db)
        self.documents = SqliteDocumentRepository(self.db)
        self.log = SqliteOperationLog(self.db)
        self.uow = self.db  # Database implementa UnitOfWork

    def close(self) -> None:
        self.db.close()
