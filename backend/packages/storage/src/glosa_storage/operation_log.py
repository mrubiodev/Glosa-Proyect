from __future__ import annotations

from dataclasses import replace
from datetime import timezone

from glosa_core import chain
from glosa_core.domain import (
    ChainReport,
    Channel,
    OperationEntry,
    OperationFilter,
    Outcome,
)

from .codec import actor_from_json, actor_to_json, dumps, from_db, loads, to_db
from .database import Database


def _entry(row) -> OperationEntry:
    return OperationEntry(
        id=row["id"],
        at=from_db(row["at"]),
        correlation_id=row["correlation_id"],
        actor=actor_from_json(row["actor_json"]),
        channel=Channel(row["channel"]),
        action=row["action"],
        collection_id=row["collection_id"],
        outcome=Outcome(row["outcome"]),
        target=loads(row["target_json"]),
        duration_ms=row["duration_ms"],
        details=loads(row["details_json"]),
        prev_hash=row["prev_hash"],
        hash=row["hash"],
    )


class SqliteOperationLog:
    """Registro de solo añadir con la cadena de hashes por colección.

    Leer el último hash y añadir la entrada ocurren en una transacción que toma el bloqueo de
    escritura, así que dos procesos nunca sellan dos entradas con el mismo `prev_hash`.
    Esta clase no ofrece ninguna operación para editar o borrar entradas.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    def record(self, entry: OperationEntry) -> None:
        # En UTC, para que el hash se calcule igual antes y después de pasar por la base
        entry = replace(entry, at=entry.at.astimezone(timezone.utc))
        with self._db.transaction():
            conn = self._db.conn()
            last = conn.execute(
                "SELECT hash FROM operations WHERE collection_id IS ? ORDER BY seq DESC LIMIT 1",
                (entry.collection_id,),
            ).fetchone()
            sealed = chain.seal(entry, last["hash"] if last else None)
            conn.execute(
                "INSERT INTO operations (id, collection_id, at, correlation_id, actor_id, "
                "actor_json, channel, action, outcome, target_json, duration_ms, details_json, "
                "prev_hash, hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    sealed.id, sealed.collection_id, to_db(sealed.at), sealed.correlation_id,
                    sealed.actor.id, actor_to_json(sealed.actor), sealed.channel.value,
                    sealed.action, sealed.outcome.value, dumps(sealed.target),
                    sealed.duration_ms, dumps(sealed.details), sealed.prev_hash, sealed.hash,
                ),
            )

    def query(
        self, collection_id: str | None, filters: OperationFilter, limit: int
    ) -> list[OperationEntry]:
        """Entradas de antigua a reciente."""
        clauses = ["collection_id IS ?"]
        params: list = [collection_id]
        if filters.action:
            clauses.append("action = ?")
            params.append(filters.action)
        if filters.actor_id:
            clauses.append("actor_id = ?")
            params.append(filters.actor_id)
        if filters.correlation_id:
            clauses.append("correlation_id = ?")
            params.append(filters.correlation_id)
        if filters.outcome:
            clauses.append("outcome = ?")
            params.append(Outcome(filters.outcome).value)
        if filters.since:
            clauses.append("at >= ?")
            params.append(to_db(filters.since))
        if filters.until:
            clauses.append("at <= ?")
            params.append(to_db(filters.until))
        rows = self._db.conn().execute(
            f"SELECT * FROM operations WHERE {' AND '.join(clauses)} ORDER BY seq LIMIT ?",
            (*params, limit),
        ).fetchall()
        return [_entry(r) for r in rows]

    def verify_chain(self, collection_id: str) -> ChainReport:
        rows = self._db.conn().execute(
            "SELECT * FROM operations WHERE collection_id IS ? ORDER BY seq", (collection_id,)
        ).fetchall()
        return chain.verify([_entry(r) for r in rows])
