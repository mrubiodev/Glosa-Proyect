from __future__ import annotations

from glosa_core.domain import Collection, CollectionSettings

from .codec import from_db, settings_from_json, settings_to_json, to_db
from .database import Database

# Tablas con datos de una colección, para borrarla por completo
_TABLES_BY_COLLECTION = (
    "memberships",
    "tokens",
    "document_versions",
    "documents",
    "chunks",  # los triggers limpian también el índice de texto
    "jobs",
    "operations",
)


class SqliteCollectionRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, collection: Collection) -> None:
        with self._db.transaction():
            self._db.conn().execute(
                "INSERT INTO collections (id, name, created_at, settings_json) VALUES (?, ?, ?, ?)",
                (
                    collection.id,
                    collection.name,
                    to_db(collection.created_at),
                    settings_to_json(collection.settings),
                ),
            )

    def get(self, collection_id: str) -> Collection | None:
        row = self._db.conn().execute(
            "SELECT * FROM collections WHERE id = ?", (collection_id,)
        ).fetchone()
        if row is None:
            return None
        return Collection(
            id=row["id"],
            name=row["name"],
            created_at=from_db(row["created_at"]),
            settings=settings_from_json(row["settings_json"]),
        )

    def update_settings(self, collection_id: str, settings: CollectionSettings) -> None:
        with self._db.transaction():
            self._db.conn().execute(
                "UPDATE collections SET settings_json = ? WHERE id = ?",
                (settings_to_json(settings), collection_id),
            )

    def delete(self, collection_id: str) -> None:
        """Borra la colección y TODOS sus datos, incluido su registro de operaciones."""
        with self._db.transaction():
            conn = self._db.conn()
            for table in _TABLES_BY_COLLECTION:
                conn.execute(f"DELETE FROM {table} WHERE collection_id = ?", (collection_id,))
            conn.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
