"""Entidades y tipos del dominio (SPEC §6). Sin dependencias externas."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


# --- Enumeraciones -------------------------------------------------------

class Role(StrEnum):
    READER = "reader"
    EDITOR = "editor"
    OWNER = "owner"


class Scope(StrEnum):
    READ = "read"
    WRITE = "write"


class ActorKind(StrEnum):
    USER = "user"
    TOKEN = "token"


class DocumentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class JobType(StrEnum):
    INGEST = "ingest"
    MODIFY = "modify"
    REINDEX = "reindex"
    DELETE = "delete"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEAD = "dead"
    CANCELLED = "cancelled"


class Outcome(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Channel(StrEnum):
    API = "api"
    MCP = "mcp"
    WORKER = "worker"


class Strategy(StrEnum):
    TEXT = "text"
    VECTOR = "vector"
    HYBRID = "hybrid"


# --- Actores -------------------------------------------------------------

@dataclass(frozen=True)
class Actor:
    """Quién realiza una acción: un usuario o un token de colección."""

    kind: ActorKind
    id: str  # user_id o token_id (nunca el valor del token)
    collection_id: str | None = None  # solo para tokens
    scopes: frozenset[Scope] = frozenset()  # solo para tokens


@dataclass(frozen=True)
class Credentials:
    bearer: str | None = None


# --- Entidades -----------------------------------------------------------

@dataclass(frozen=True)
class User:
    id: str
    email: str
    created_at: datetime


@dataclass(frozen=True)
class Collection:
    id: str
    name: str
    created_at: datetime
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Membership:
    user_id: str
    collection_id: str
    role: Role


@dataclass(frozen=True)
class Document:
    id: str
    collection_id: str
    title: str
    source_type: str
    current_version: int
    status: DocumentStatus
    metadata: dict[str, Any] = field(default_factory=dict)
    deleted_at: datetime | None = None


@dataclass(frozen=True)
class DocumentVersion:
    """Una versión nunca se modifica: un cambio crea una versión nueva."""

    document_id: str
    version: int
    content_hash: str
    size: int
    created_by: str
    created_at: datetime
    content_ref: str | None = None


@dataclass(frozen=True)
class ChunkDraft:
    text: str
    position: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Chunk:
    id: str
    document_id: str
    version: int
    collection_id: str
    text: str
    position: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchHit:
    chunk: Chunk
    score: float
    strategy: Strategy


@dataclass(frozen=True)
class AccessToken:
    id: str
    collection_id: str
    created_by: str
    hash: str
    scopes: frozenset[Scope]
    expires_at: datetime | None = None
    revoked: bool = False


@dataclass(frozen=True)
class Job:
    id: str
    collection_id: str
    type: JobType
    target: str
    status: JobStatus
    actor: Actor
    correlation_id: str
    created_at: datetime
    priority: int = 100
    attempts: int = 0
    max_attempts: int = 5
    run_after: datetime | None = None
    idempotency_key: str | None = None
    lease_until: datetime | None = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass(frozen=True)
class JobResult:
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationEntry:
    """Entrada del registro de operaciones (SPEC §10). Solo se añade."""

    id: str
    at: datetime
    correlation_id: str
    actor: Actor
    channel: Channel
    action: str
    collection_id: str | None
    outcome: Outcome
    target: dict[str, Any] = field(default_factory=dict)
    duration_ms: int | None = None
    details: dict[str, Any] = field(default_factory=dict)
    prev_hash: str | None = None
    hash: str | None = None


@dataclass(frozen=True)
class OperationFilter:
    action: str | None = None
    actor_id: str | None = None
    correlation_id: str | None = None
    outcome: Outcome | None = None
    since: datetime | None = None
    until: datetime | None = None


@dataclass(frozen=True)
class ChainReport:
    valid: bool
    checked: int
    broken_at: str | None = None  # id de la primera entrada inconsistente
