"""Encadenado de hashes del registro de operaciones (SPEC §10.2).

Cada entrada incluye el hash de la anterior: alterar una invalida las siguientes.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from typing import Any

from .domain import ChainReport, OperationEntry

GENESIS_HASH = "0" * 64


def _payload(entry: OperationEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "at": entry.at.isoformat(),
        "correlation_id": entry.correlation_id,
        "actor": {
            "kind": entry.actor.kind.value,
            "id": entry.actor.id,
            "collection_id": entry.actor.collection_id,
        },
        "channel": entry.channel.value,
        "action": entry.action,
        "collection_id": entry.collection_id,
        "outcome": entry.outcome.value,
        "target": entry.target,
        "duration_ms": entry.duration_ms,
        "details": entry.details,
    }


def compute_hash(prev_hash: str, entry: OperationEntry) -> str:
    canonical = json.dumps(
        _payload(entry), sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256((prev_hash + canonical).encode("utf-8")).hexdigest()


def seal(entry: OperationEntry, prev_hash: str | None) -> OperationEntry:
    """Devuelve la entrada con su prev_hash y su hash calculados."""
    prev = prev_hash or GENESIS_HASH
    return replace(entry, prev_hash=prev, hash=compute_hash(prev, entry))


def verify(entries: list[OperationEntry]) -> ChainReport:
    """Comprueba una secuencia de entradas ordenadas de antigua a reciente.

    La primera sirve de ancla: si el registro se purgó por retención, su
    prev_hash no será el génesis y aun así la cadena restante se valida.
    """
    previous: OperationEntry | None = None
    for entry in entries:
        if entry.hash is None or entry.prev_hash is None:
            return ChainReport(False, 0 if previous is None else entries.index(entry), entry.id)
        if entry.hash != compute_hash(entry.prev_hash, entry):
            return ChainReport(False, entries.index(entry), entry.id)
        if previous is not None and entry.prev_hash != previous.hash:
            return ChainReport(False, entries.index(entry), entry.id)
        previous = entry
    return ChainReport(True, len(entries))
