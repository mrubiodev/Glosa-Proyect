from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from glosa_core.domain import Job, JobResult, JobStatus, JobType

from .codec import actor_from_json, actor_to_json, from_db, to_db
from .database import Database


def _job(row) -> Job:
    return Job(
        id=row["id"],
        collection_id=row["collection_id"],
        type=JobType(row["type"]),
        target=row["target"],
        version=row["version"],
        status=JobStatus(row["status"]),
        actor=actor_from_json(row["actor_json"]),
        correlation_id=row["correlation_id"],
        created_at=from_db(row["created_at"]),
        priority=row["priority"],
        attempts=row["attempts"],
        max_attempts=row["max_attempts"],
        run_after=from_db(row["run_after"]),
        idempotency_key=row["idempotency_key"],
        lease_until=from_db(row["lease_until"]),
        error=row["error"],
        started_at=from_db(row["started_at"]),
        finished_at=from_db(row["finished_at"]),
    )


class SqliteJobQueue:
    """Cola de trabajos sobre SQLite con las garantías de SPEC §9.4.

    - **Atomicidad entre procesos:** `claim` corre en una transacción `BEGIN IMMEDIATE`, así
      que dos workers nunca reciben el mismo trabajo.
    - **Orden por documento:** un trabajo no se entrega mientras haya otro anterior sin
      terminar (en cola o en marcha) sobre el mismo documento, incluso si está esperando un
      reintento.
    - **Lease:** un trabajo en marcha cuyo plazo vence vuelve a la cola.
    - **Idempotencia:** un índice único `(colección, clave)` lo garantiza aunque dos
      peticiones lleguen a la vez.
    """

    def __init__(self, db: Database, clock) -> None:
        self._db = db
        self._clock = clock

    def enqueue(self, job: Job) -> Job:
        with self._db.transaction():
            if job.idempotency_key:
                existing = self.find_by_key(job.collection_id, job.idempotency_key)
                if existing is not None:
                    return existing
            try:
                self._db.conn().execute(
                    "INSERT INTO jobs (id, collection_id, type, target, version, status, actor_json, "
                    "correlation_id, created_at, priority, attempts, max_attempts, run_after, "
                    "idempotency_key, lease_until, error, started_at, finished_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        job.id, job.collection_id, job.type.value, job.target, job.version,
                        job.status.value, actor_to_json(job.actor), job.correlation_id,
                        to_db(job.created_at), job.priority, job.attempts, job.max_attempts,
                        to_db(job.run_after), job.idempotency_key, to_db(job.lease_until),
                        job.error, to_db(job.started_at), to_db(job.finished_at),
                    ),
                )
            except sqlite3.IntegrityError:
                # Red de seguridad: otra petición con la misma clave ganó la carrera
                existing = job.idempotency_key and self.find_by_key(
                    job.collection_id, job.idempotency_key
                )
                if existing:
                    return existing
                raise
        return job

    def find_by_key(self, collection_id: str, key: str) -> Job | None:
        row = self._db.conn().execute(
            "SELECT * FROM jobs WHERE collection_id = ? AND idempotency_key = ?",
            (collection_id, key),
        ).fetchone()
        return _job(row) if row else None

    def claim(self, worker_id: str, lease_seconds: int) -> Job | None:
        now = self._clock.now()
        now_s = to_db(now)
        with self._db.transaction():
            conn = self._db.conn()
            # Un worker que cayó dejó su lease caducado: ese trabajo vuelve a la cola
            conn.execute(
                "UPDATE jobs SET status = 'queued', lease_until = NULL "
                "WHERE status = 'running' AND lease_until <= ?",
                (now_s,),
            )
            row = conn.execute(
                "SELECT j.id FROM jobs j WHERE j.status = 'queued' "
                "AND (j.run_after IS NULL OR j.run_after <= ?) "
                "AND NOT EXISTS (SELECT 1 FROM jobs o WHERE o.collection_id = j.collection_id "
                "  AND o.target = j.target AND o.seq < j.seq AND o.status IN ('queued', 'running')) "
                "ORDER BY j.priority, j.seq LIMIT 1",
                (now_s,),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                "UPDATE jobs SET status = 'running', attempts = attempts + 1, lease_until = ?, "
                "lease_seconds = ?, started_at = ? WHERE id = ?",
                (to_db(now + timedelta(seconds=lease_seconds)), lease_seconds, now_s, row["id"]),
            )
            claimed = conn.execute("SELECT * FROM jobs WHERE id = ?", (row["id"],)).fetchone()
        return _job(claimed)

    def heartbeat(self, job_id: str, worker_id: str) -> None:
        with self._db.transaction():
            conn = self._db.conn()
            row = conn.execute(
                "SELECT lease_seconds FROM jobs WHERE id = ? AND status = 'running'", (job_id,)
            ).fetchone()
            if row is not None:
                until = self._clock.now() + timedelta(seconds=row["lease_seconds"] or 60)
                conn.execute("UPDATE jobs SET lease_until = ? WHERE id = ?", (to_db(until), job_id))

    def ack(self, job_id: str, result: JobResult) -> None:
        with self._db.transaction():
            self._db.conn().execute(
                "UPDATE jobs SET status = 'succeeded', lease_until = NULL, error = NULL, "
                "finished_at = ? WHERE id = ? AND status = 'running'",
                (to_db(self._clock.now()), job_id),
            )

    def fail(self, job_id: str, error: str, retry_at: datetime | None) -> None:
        with self._db.transaction():
            if retry_at is not None:
                self._db.conn().execute(
                    "UPDATE jobs SET status = 'queued', run_after = ?, lease_until = NULL, error = ? "
                    "WHERE id = ? AND status = 'running'",
                    (to_db(retry_at), error, job_id),
                )
            else:
                self._db.conn().execute(
                    "UPDATE jobs SET status = 'dead', lease_until = NULL, error = ?, finished_at = ? "
                    "WHERE id = ? AND status = 'running'",
                    (error, to_db(self._clock.now()), job_id),
                )

    def cancel(self, collection_id: str, job_id: str) -> bool:
        with self._db.transaction():
            cursor = self._db.conn().execute(
                "UPDATE jobs SET status = 'cancelled', finished_at = ? "
                "WHERE collection_id = ? AND id = ? AND status = 'queued'",
                (to_db(self._clock.now()), collection_id, job_id),
            )
            return cursor.rowcount == 1

    def get(self, collection_id: str, job_id: str) -> Job | None:
        row = self._db.conn().execute(
            "SELECT * FROM jobs WHERE collection_id = ? AND id = ?", (collection_id, job_id)
        ).fetchone()
        return _job(row) if row else None

    def list(self, collection_id: str, status: str | None, limit: int) -> list[Job]:
        sql = "SELECT * FROM jobs WHERE collection_id = ?"
        params: list = [collection_id]
        if status is not None:
            sql += " AND status = ?"
            params.append(str(status))
        rows = self._db.conn().execute(sql + " ORDER BY seq LIMIT ?", (*params, limit)).fetchall()
        return [_job(r) for r in rows]
