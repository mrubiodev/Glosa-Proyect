"""Pruebas de contrato de JobQueue (SPEC §9.4).

Funciones sin dependencia de pytest: cada adaptador de cola (en memoria, SQLite...)
las ejecuta pasando una fábrica `make_queue(clock)`.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .domain import Actor, ActorKind, Job, JobStatus, JobType
from .testing import FixedClock


def _job(job_id: str, doc: str, key: str | None = None, collection: str = "col-a") -> Job:
    return Job(
        id=job_id,
        collection_id=collection,
        type=JobType.INGEST,
        target=doc,
        version=1,
        status=JobStatus.QUEUED,
        actor=Actor(ActorKind.USER, "ana"),
        correlation_id=f"corr-{job_id}",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        idempotency_key=key,
    )


def check_idempotency(make_queue) -> None:
    q = make_queue(FixedClock())
    first = q.enqueue(_job("j1", "d1", key="k"))
    again = q.enqueue(_job("j2", "d1", key="k"))
    assert again.id == first.id
    assert len(q.list("col-a", None, 10)) == 1
    # la misma clave en otra colección es otra petición distinta
    assert q.enqueue(_job("j3", "d1", key="k", collection="col-b")).id == "j3"


def check_order_per_document(make_queue) -> None:
    q = make_queue(FixedClock())
    q.enqueue(_job("j1", "d1"))
    q.enqueue(_job("j2", "d1"))
    q.enqueue(_job("j3", "d2"))

    first = q.claim("w", 60)
    assert first.id == "j1"
    # d1 está ocupado: j2 espera, pero d2 sí puede avanzar
    assert q.claim("w", 60).id == "j3"
    assert q.claim("w", 60) is None
    q.ack("j1", None)
    assert q.claim("w", 60).id == "j2"


def check_retry_keeps_order(make_queue) -> None:
    clock = FixedClock()
    q = make_queue(clock)
    q.enqueue(_job("j1", "d1"))
    q.enqueue(_job("j2", "d1"))

    q.claim("w", 60)
    q.fail("j1", "error transitorio", retry_at=clock.now() + timedelta(seconds=60))
    # j1 espera su reintento: j2 NO puede adelantarse
    assert q.claim("w", 60) is None
    clock.advance(seconds=61)
    assert q.claim("w", 60).id == "j1"


def check_lease_recovery(make_queue) -> None:
    clock = FixedClock()
    q = make_queue(clock)
    q.enqueue(_job("j1", "d1"))

    assert q.claim("w1", 30).id == "j1"
    assert q.claim("w2", 30) is None  # w1 lo tiene
    clock.advance(seconds=31)  # w1 cayó: su lease caducó
    recovered = q.claim("w2", 30)
    assert recovered.id == "j1"
    assert recovered.attempts == 2


def check_cancel_only_when_queued(make_queue) -> None:
    q = make_queue(FixedClock())
    q.enqueue(_job("j1", "d1"))
    q.enqueue(_job("j2", "d2"))
    q.claim("w", 60)  # j1 pasa a running
    assert q.cancel("col-a", "j1") is False
    assert q.cancel("col-a", "j2") is True
    assert q.get("col-a", "j2").status is JobStatus.CANCELLED


ALL_CHECKS = (
    check_idempotency,
    check_order_per_document,
    check_retry_keeps_order,
    check_lease_recovery,
    check_cancel_only_when_queued,
)
