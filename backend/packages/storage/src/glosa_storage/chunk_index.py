from __future__ import annotations

import re

from glosa_core.domain import Chunk, SearchHit, Strategy

from .codec import dumps, loads
from .database import Database

_WORD = re.compile(r"\w+", re.UNICODE)
MAX_QUERY_WORDS = 32


def fts_query(text: str) -> str:
    """Convierte texto libre en una consulta FTS5 segura.

    Cada palabra va entre comillas (así `AND`, `OR`, `*` o `"` del usuario no se interpretan
    como sintaxis) y se unen con OR: basta con que aparezca alguna; el ordenamiento por
    relevancia (bm25) pone arriba los fragmentos que contienen más palabras.
    """
    words = list(dict.fromkeys(w.lower() for w in _WORD.findall(text)))[:MAX_QUERY_WORDS]
    return " OR ".join(f'"{w}"' for w in words)


def _chunk(row) -> Chunk:
    return Chunk(
        id=row["id"],
        document_id=row["document_id"],
        version=row["version"],
        collection_id=row["collection_id"],
        text=row["text"],
        position=row["position"],
        metadata=loads(row["metadata_json"]),
    )


class SqliteChunkIndex:
    """Índice de texto completo con FTS5. Toda consulta filtra por colección en SQL."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def index(self, chunks: list[Chunk]) -> None:
        with self._db.transaction():
            conn = self._db.conn()
            for c in chunks:
                # Indexar dos veces el mismo fragmento lo reemplaza: es idempotente
                conn.execute(
                    "DELETE FROM chunks WHERE collection_id = ? AND id = ?", (c.collection_id, c.id)
                )
                conn.execute(
                    "INSERT INTO chunks (id, collection_id, document_id, version, position, text, "
                    "metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (c.id, c.collection_id, c.document_id, c.version, c.position, c.text,
                     dumps(c.metadata)),
                )

    def search(self, collection_id: str, query: str, limit: int) -> list[SearchHit]:
        match = fts_query(query)
        if not match:
            return []
        rows = self._db.conn().execute(
            "SELECT c.*, bm25(chunks_fts) AS rank FROM chunks_fts "
            "JOIN chunks c ON c.seq = chunks_fts.rowid "
            "WHERE chunks_fts MATCH ? AND c.collection_id = ? "
            "ORDER BY rank, c.seq LIMIT ?",
            (match, collection_id, limit),
        ).fetchall()
        # bm25 devuelve valores más negativos cuanto más relevante: se invierte el signo
        return [SearchHit(_chunk(r), -float(r["rank"]), Strategy.TEXT) for r in rows]

    def remove_version(self, collection_id: str, doc_id: str, version: int) -> None:
        with self._db.transaction():
            self._db.conn().execute(
                "DELETE FROM chunks WHERE collection_id = ? AND document_id = ? AND version = ?",
                (collection_id, doc_id, version),
            )

    def remove_document(self, collection_id: str, doc_id: str) -> None:
        with self._db.transaction():
            self._db.conn().execute(
                "DELETE FROM chunks WHERE collection_id = ? AND document_id = ?",
                (collection_id, doc_id),
            )
