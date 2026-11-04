"""Escribe entradas en el registro de operaciones (SPEC §10)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .context import RequestContext
from .domain import OperationEntry, Outcome
from .ports import Clock, IdGenerator, OperationLog


class OperationRecorder:
    def __init__(self, log: OperationLog, clock: Clock, ids: IdGenerator) -> None:
        self._log = log
        self._clock = clock
        self._ids = ids

    def record(
        self,
        ctx: RequestContext,
        action: str,
        outcome: Outcome,
        *,
        collection_id: str | None = None,
        target: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
        started: datetime | None = None,
    ) -> OperationEntry:
        now = self._clock.now()
        duration = None if started is None else int((now - started).total_seconds() * 1000)
        entry = OperationEntry(
            id=self._ids.new_id("op"),
            at=now,
            correlation_id=ctx.correlation_id,
            actor=ctx.actor,
            channel=ctx.channel,
            action=action,
            collection_id=collection_id,
            outcome=outcome,
            target=target or {},
            duration_ms=duration,
            details=details or {},
        )
        self._log.record(entry)
        return entry
