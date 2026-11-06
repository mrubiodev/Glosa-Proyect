from __future__ import annotations

from datetime import datetime

from glosa_core.domain import Document, DocumentStatus, DocumentVersion

from .codec import dumps, from_db, loads, to_db
from .database import Database


def _document(row) -> Document:
    return Document(
        id=row["id"],
        collection_id=row["collection_id"],
        title=row["title"],
        source_type=row["source_type"],
        current_version=row["current_version"],
        status=DocumentStatus(row["status"]),
        metadata=loads(row["metadata_json"]),
        deleted_at=from_db(row["deleted_at"]),
    )


def _version(row) -> DocumentVersion:
    return DocumentVersion(
        document_id=row["document_id"],
        version=row["version"],
        content_hash=row["content_hash"],
        size=row["size"],
        created_by=row["created_by"],
        created_at=from_db(row["created_at"]),
    )


class SqliteDocumentRepository:
    """Los documentos y el contenido de cada versión viven en la misma base de datos,
    así que subir un documento es atómico con el resto de la transacción."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def _insert_version(self, collection_id: str, version: DocumentVersion, content: bytes) -> None:
        self._db.conn().execute(
            "INSERT INTO document_versions (collection_id, document_id, version, content_hash, "
            "size, created_by, created_at, content) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                collection_id,
                version.document_id,
                version.version,
                version.content_hash,
                version.size,
                version.created_by,
                to_db(version.created_at),
                content,
            ),
        )

    def add(self, doc: Document, version: DocumentVersion, content: bytes) -> None:
        with self._db.transaction():
            self._db.conn().execute(
                "INSERT INTO documents (collection_id, id, title, source_type, current_version, "
                "status, metadata_json, deleted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    doc.collection_id,
                    doc.id,
                    doc.title,
                    doc.source_type,
                    doc.current_version,
                    doc.status.value,
                    dumps(doc.metadata),
                    to_db(doc.deleted_at),
                ),
            )
            self._insert_version(doc.collection_id, version, content)

    def add_version(
        self, collection_id: str, doc_id: str, version: DocumentVersion, content: bytes
    ) -> None:
        with self._db.transaction():
            if self.get(collection_id, doc_id) is None:
                raise KeyError(f"No existe el documento {doc_id} en la colección")
            self._insert_version(collection_id, version, content)

    def get(self, collection_id: str, doc_id: str) -> Document | None:
        row = self._db.conn().execute(
            "SELECT * FROM documents WHERE collection_id = ? AND id = ?", (collection_id, doc_id)
        ).fetchone()
        return _document(row) if row else None

    def get_content(self, collection_id: str, doc_id: str, version: int | None) -> bytes | None:
        doc = self.get(collection_id, doc_id)
        if doc is None:
            return None
        row = self._db.conn().execute(
            "SELECT content FROM document_versions "
            "WHERE collection_id = ? AND document_id = ? AND version = ?",
            (collection_id, doc_id, version or doc.current_version),
        ).fetchone()
        return bytes(row["content"]) if row else None

    def history(self, collection_id: str, doc_id: str) -> list[DocumentVersion]:
        rows = self._db.conn().execute(
            "SELECT document_id, version, content_hash, size, created_by, created_at "
            "FROM document_versions WHERE collection_id = ? AND document_id = ? ORDER BY version",
            (collection_id, doc_id),
        ).fetchall()
        return [_version(r) for r in rows]

    def list(self, collection_id: str) -> list[Document]:
        rows = self._db.conn().execute(
            "SELECT * FROM documents WHERE collection_id = ? AND deleted_at IS NULL ORDER BY seq",
            (collection_id,),
        ).fetchall()
        return [_document(r) for r in rows]

    def update_status(
        self,
        collection_id: str,
        doc_id: str,
        status: DocumentStatus,
        current_version: int | None = None,
    ) -> None:
        with self._db.transaction():
            self._db.conn().execute(
                "UPDATE documents SET status = ?, current_version = COALESCE(?, current_version) "
                "WHERE collection_id = ? AND id = ?",
                (status.value, current_version, collection_id, doc_id),
            )

    def mark_deleted(self, collection_id: str, doc_id: str, at: datetime) -> None:
        with self._db.transaction():
            self._db.conn().execute(
                "UPDATE documents SET deleted_at = ? WHERE collection_id = ? AND id = ?",
                (to_db(at), collection_id, doc_id),
            )
