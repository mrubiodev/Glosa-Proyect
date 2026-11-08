from __future__ import annotations

import hashlib

from ..authorization import Permission
from ..context import RequestContext
from ..domain import Outcome, SearchHit
from ..errors import InvalidRequest, NotFound
from ..kernel import Kernel
from ..ports import ChunkIndex, CollectionRepository
from .base import UseCase

MAX_LIMIT = 50
MAX_QUERY_LENGTH = 1000


class SearchCollection(UseCase):
    """Búsqueda síncrona. Siempre queda registrada; el texto de la consulta depende
    del ajuste `query_logging` de la colección (SPEC §10.6)."""

    action = "search.execute"

    def __init__(
        self,
        kernel: Kernel,
        collections: CollectionRepository,
        index: ChunkIndex,
        strategy: str = "text",
        default_limit: int = 5,
    ) -> None:
        super().__init__(kernel)
        self._collections = collections
        self._index = index
        self._strategy = strategy
        self._default_limit = default_limit

    def execute(
        self, ctx: RequestContext, collection_id: str, query: str, limit: int | None = None
    ) -> list[SearchHit]:
        limit = self._default_limit if limit is None else limit
        started = self.k.clock.now()
        self._require(ctx, collection_id, Permission.SEARCH, self.action)
        with self._guard(ctx, self.action, collection_id, started):
            collection = self._collections.get(collection_id)
            if collection is None:
                raise NotFound("Colección no encontrada")
            clean = (query or "").strip()
            if not clean or len(clean) > MAX_QUERY_LENGTH:
                raise InvalidRequest(f"La consulta debe tener entre 1 y {MAX_QUERY_LENGTH} caracteres")
            if not 1 <= limit <= MAX_LIMIT:
                raise InvalidRequest(f"El límite debe estar entre 1 y {MAX_LIMIT}")

        hits = self._index.search(collection_id, clean, limit)

        details: dict = {
            "strategy": self._strategy,
            "limit": limit,
            "hits": [
                {
                    "chunk_id": h.chunk.id,
                    "document_id": h.chunk.document_id,
                    "version": h.chunk.version,
                    "score": h.score,
                }
                for h in hits
            ],
        }
        if collection.settings.query_logging == "full":
            details["query"] = clean
        else:  # hash_only: el texto nunca llega al registro
            details["query_hash"] = hashlib.sha256(clean.encode("utf-8")).hexdigest()
        self.k.recorder.record(
            ctx,
            self.action,
            Outcome.SUCCEEDED,
            collection_id=collection_id,
            details=details,
            started=started,
        )
        return hits
