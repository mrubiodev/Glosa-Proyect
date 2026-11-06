"""Dobles en memoria para tests. Reutilizables por otros paquetes."""
from __future__ import annotations

import itertools
import re
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from . import chain
from .domain import (
    AccessToken,
    ChainReport,
    Chunk,
    ChunkDraft,
    Collection,
    CollectionSettings,
    Document,
    DocumentStatus,
    DocumentVersion,
    Job,
    JobResult,
    JobStatus,
    Membership,
    OperationEntry,
    OperationFilter,
    Role,
    SearchHit,
    Strategy,
)


# Identificadores de colección de uso común en los tests
COL_A = "col-a"
COL_B = "col-b"


class FixedClock:
    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime(2026, 1, 1, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs: float) -> None:
        self._now += timedelta(**kwargs)


class SequentialIds:
    """Identificadores predecibles: `col-1`, `doc-2`..."""

    def __init__(self) -> None:
        self._counter = itertools.count(1)

    def new_id(self, prefix: str) -> str:
        return f"{prefix}-{next(self._counter)}"


class InMemoryAccessRepository:
    def __init__(self) -> None:
        self._roles: dict[tuple[str, str], Role] = {}
        self._tokens_by_id: dict[str, AccessToken] = {}

    def add_member(self, user_id: str, collection_id: str, role: Role) -> None:
        self._roles[(user_id, collection_id)] = role

    def remove_member(self, user_id: str, collection_id: str) -> None:
        self._roles.pop((user_id, collection_id), None)

    def role_of(self, user_id: str, collection_id: str) -> Role | None:
        return self._roles.get((user_id, collection_id))

    def members(self, collection_id: str) -> list[Membership]:
        return [
            Membership(user, col, role)
            for (user, col), role in self._roles.items()
            if col == collection_id
        ]

    def collections_of(self, user_id: str) -> list[str]:
        return [col for (user, col) in self._roles if user == user_id]

    def find_token(self, token_hash: str) -> AccessToken | None:
        for token in self._tokens_by_id.values():
            if token.hash == token_hash:
                return token
        return None

    def get_token(self, collection_id: str, token_id: str) -> AccessToken | None:
        token = self._tokens_by_id.get(token_id)
        return token if token and token.collection_id == collection_id else None

    def list_tokens(self, collection_id: str) -> list[AccessToken]:
        return [t for t in self._tokens_by_id.values() if t.collection_id == collection_id]

    def save_token(self, token: AccessToken) -> None:
        self._tokens_by_id[token.id] = token

    def revoke_token(self, token_id: str) -> None:
        token = self._tokens_by_id[token_id]
        self._tokens_by_id[token_id] = replace(token, revoked=True)


class InMemoryCollectionRepository:
    def __init__(self) -> None:
        self._items: dict[str, Collection] = {}

    def add(self, collection: Collection) -> None:
        self._items[collection.id] = collection

    def get(self, collection_id: str) -> Collection | None:
        return self._items.get(collection_id)

    def delete(self, collection_id: str) -> None:
        self._items.pop(collection_id, None)

    def update_settings(self, collection_id: str, settings: CollectionSettings) -> None:
        self._items[collection_id] = replace(self._items[collection_id], settings=settings)


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self._docs: dict[tuple[str, str], Document] = {}
        self._versions: dict[tuple[str, str], list[DocumentVersion]] = {}
        self._content: dict[tuple[str, str, int], bytes] = {}

    def add(self, doc: Document, version: DocumentVersion, content: bytes) -> None:
        key = (doc.collection_id, doc.id)
        self._docs[key] = doc
        self._versions[key] = [version]
        self._content[(doc.collection_id, doc.id, version.version)] = content

    def add_version(
        self, collection_id: str, doc_id: str, version: DocumentVersion, content: bytes
    ) -> None:
        self._versions[(collection_id, doc_id)].append(version)
        self._content[(collection_id, doc_id, version.version)] = content

    def get(self, collection_id: str, doc_id: str) -> Document | None:
        return self._docs.get((collection_id, doc_id))

    def force_source_type(self, collection_id: str, doc_id: str, source_type: str) -> None:
        """Solo para tests: simula un documento cuyo tipo ya no tiene extractor."""
        doc = self._docs[(collection_id, doc_id)]
        self._docs[(collection_id, doc_id)] = replace(doc, source_type=source_type)

    def get_content(self, collection_id: str, doc_id: str, version: int | None) -> bytes | None:
        doc = self.get(collection_id, doc_id)
        if doc is None:
            return None
        return self._content.get((collection_id, doc_id, version or doc.current_version))

    def history(self, collection_id: str, doc_id: str) -> list[DocumentVersion]:
        return list(self._versions.get((collection_id, doc_id), []))

    def list(self, collection_id: str) -> list[Document]:
        return [
            d for (col, _), d in self._docs.items() if col == collection_id and d.deleted_at is None
        ]

    def update_status(
        self,
        collection_id: str,
        doc_id: str,
        status: DocumentStatus,
        current_version: int | None = None,
    ) -> None:
        doc = self._docs[(collection_id, doc_id)]
        changes: dict = {"status": status}
        if current_version is not None:
            changes["current_version"] = current_version
        self._docs[(collection_id, doc_id)] = replace(doc, **changes)

    def mark_deleted(self, collection_id: str, doc_id: str, at: datetime) -> None:
        doc = self._docs[(collection_id, doc_id)]
        self._docs[(collection_id, doc_id)] = replace(doc, deleted_at=at)


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


class InMemoryChunkIndex:
    """Índice de juguete: puntúa por número de palabras de la consulta que aparecen."""

    def __init__(self) -> None:
        self._chunks: dict[str, dict[str, Chunk]] = {}

    def index(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            self._chunks.setdefault(chunk.collection_id, {})[chunk.id] = chunk

    def search(self, collection_id: str, query: str, limit: int) -> list[SearchHit]:
        wanted = set(_words(query))
        hits: list[SearchHit] = []
        for chunk in self._chunks.get(collection_id, {}).values():
            score = float(len(wanted & set(_words(chunk.text))))
            if score > 0:
                hits.append(SearchHit(chunk, score, Strategy.TEXT))
        hits.sort(key=lambda h: -h.score)
        return hits[:limit]

    def remove_version(self, collection_id: str, doc_id: str, version: int) -> None:
        bucket = self._chunks.get(collection_id, {})
        for cid in [c.id for c in bucket.values() if c.document_id == doc_id and c.version == version]:
            del bucket[cid]

    def remove_document(self, collection_id: str, doc_id: str) -> None:
        bucket = self._chunks.get(collection_id, {})
        for cid in [c.id for c in bucket.values() if c.document_id == doc_id]:
            del bucket[cid]

    def all_chunks(self, collection_id: str) -> list[Chunk]:
        return sorted(self._chunks.get(collection_id, {}).values(), key=lambda c: c.id)


class InMemoryJobQueue:
    """Cola con las garantías de SPEC §9.4: orden por documento, lease, idempotencia."""

    def __init__(self, clock) -> None:
        self._clock = clock
        self._jobs: dict[str, Job] = {}
        self._order: list[str] = []
        self._lease_seconds: dict[str, int] = {}

    def enqueue(self, job: Job) -> Job:
        if job.idempotency_key:
            existing = self.find_by_key(job.collection_id, job.idempotency_key)
            if existing is not None:
                return existing
        self._jobs[job.id] = job
        self._order.append(job.id)
        return job

    def find_by_key(self, collection_id: str, key: str) -> Job | None:
        for job in self._jobs.values():
            if job.collection_id == collection_id and job.idempotency_key == key:
                return job
        return None

    def _reclaim_expired(self) -> None:
        now = self._clock.now()
        for job_id, job in list(self._jobs.items()):
            if job.status is JobStatus.RUNNING and job.lease_until and job.lease_until <= now:
                self._jobs[job_id] = replace(job, status=JobStatus.QUEUED, lease_until=None)

    def _blocked(self, job: Job) -> bool:
        """Hay un trabajo anterior sin terminar sobre el mismo documento."""
        position = self._order.index(job.id)
        for other_id in self._order[:position]:
            other = self._jobs[other_id]
            same = (other.collection_id, other.target) == (job.collection_id, job.target)
            if same and other.status in (JobStatus.QUEUED, JobStatus.RUNNING):
                return True
        return False

    def claim(self, worker_id: str, lease_seconds: int) -> Job | None:
        self._reclaim_expired()
        now = self._clock.now()
        candidates = [
            self._jobs[jid]
            for jid in self._order
            if self._jobs[jid].status is JobStatus.QUEUED
            and (self._jobs[jid].run_after is None or self._jobs[jid].run_after <= now)
            and not self._blocked(self._jobs[jid])
        ]
        if not candidates:
            return None
        chosen = min(candidates, key=lambda j: (j.priority, self._order.index(j.id)))
        claimed = replace(
            chosen,
            status=JobStatus.RUNNING,
            attempts=chosen.attempts + 1,
            lease_until=now + timedelta(seconds=lease_seconds),
            started_at=now,
        )
        self._jobs[chosen.id] = claimed
        self._lease_seconds[chosen.id] = lease_seconds
        return claimed

    def heartbeat(self, job_id: str, worker_id: str) -> None:
        job = self._jobs[job_id]
        seconds = self._lease_seconds.get(job_id, 60)
        self._jobs[job_id] = replace(job, lease_until=self._clock.now() + timedelta(seconds=seconds))

    def ack(self, job_id: str, result: JobResult) -> None:
        self._jobs[job_id] = replace(
            self._jobs[job_id],
            status=JobStatus.SUCCEEDED,
            lease_until=None,
            finished_at=self._clock.now(),
            error=None,
        )

    def fail(self, job_id: str, error: str, retry_at: datetime | None) -> None:
        job = self._jobs[job_id]
        if retry_at is not None:
            self._jobs[job_id] = replace(
                job, status=JobStatus.QUEUED, run_after=retry_at, lease_until=None, error=error
            )
        else:
            self._jobs[job_id] = replace(
                job,
                status=JobStatus.DEAD,
                lease_until=None,
                finished_at=self._clock.now(),
                error=error,
            )

    def cancel(self, collection_id: str, job_id: str) -> bool:
        job = self.get(collection_id, job_id)
        if job is None or job.status is not JobStatus.QUEUED:
            return False
        self._jobs[job_id] = replace(job, status=JobStatus.CANCELLED, finished_at=self._clock.now())
        return True

    def get(self, collection_id: str, job_id: str) -> Job | None:
        job = self._jobs.get(job_id)
        return job if job and job.collection_id == collection_id else None

    def list(self, collection_id: str, status: str | None, limit: int) -> list[Job]:
        out = [
            self._jobs[jid]
            for jid in self._order
            if self._jobs[jid].collection_id == collection_id
            and (status is None or self._jobs[jid].status == status)
        ]
        return out[:limit]


class InMemoryOperationLog:
    """Registro que sella cada entrada con la cadena de hashes de su colección."""

    def __init__(self) -> None:
        self._by_collection: dict[str | None, list[OperationEntry]] = {}

    def record(self, entry: OperationEntry) -> None:
        entries = self._by_collection.setdefault(entry.collection_id, [])
        previous = entries[-1].hash if entries else None
        entries.append(chain.seal(entry, previous))

    def entries(self, collection_id: str | None) -> list[OperationEntry]:
        return list(self._by_collection.get(collection_id, []))

    def tamper(self, collection_id: str, index: int, **changes) -> str:
        """Solo para tests: altera una entrada ya guardada. Devuelve su id."""
        entries = self._by_collection[collection_id]
        entries[index] = replace(entries[index], **changes)
        return entries[index].id

    def query(
        self, collection_id: str, filters: OperationFilter, limit: int
    ) -> list[OperationEntry]:
        out = []
        for e in self.entries(collection_id):
            if filters.action and e.action != filters.action:
                continue
            if filters.actor_id and e.actor.id != filters.actor_id:
                continue
            if filters.correlation_id and e.correlation_id != filters.correlation_id:
                continue
            if filters.outcome and e.outcome != filters.outcome:
                continue
            if filters.since and e.at < filters.since:
                continue
            if filters.until and e.at > filters.until:
                continue
            out.append(e)
        return out[:limit]

    def verify_chain(self, collection_id: str) -> ChainReport:
        return chain.verify(self.entries(collection_id))


class FakeExtractor:
    def supports(self, source_type: str) -> bool:
        return source_type in {"text", "markdown"}

    def extract(self, raw: bytes) -> str:
        return raw.decode("utf-8")


class FakeChunker:
    """Un fragmento por párrafo (separados por línea en blanco)."""

    def split(self, text: str) -> list[ChunkDraft]:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        return [ChunkDraft(text=p, position=i) for i, p in enumerate(paragraphs)]
