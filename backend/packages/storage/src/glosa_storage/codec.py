"""Conversión entre el dominio y las columnas de SQLite."""
from __future__ import annotations

import json
from dataclasses import asdict, fields
from datetime import datetime, timezone
from typing import Any

from glosa_core.domain import Actor, ActorKind, CollectionSettings, Scope

# Formato fijo y en UTC: así las fechas se pueden comparar como texto en las consultas.
_FORMAT = "%Y-%m-%dT%H:%M:%S.%f+00:00"


def to_db(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        raise ValueError("Las fechas deben llevar zona horaria")
    return value.astimezone(timezone.utc).strftime(_FORMAT)


def from_db(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.strptime(value, _FORMAT).replace(tzinfo=timezone.utc)


def dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def loads(value: str) -> Any:
    return json.loads(value)


def actor_to_json(actor: Actor) -> str:
    return dumps(
        {
            "kind": actor.kind.value,
            "id": actor.id,
            "collection_id": actor.collection_id,
            "scopes": sorted(s.value for s in actor.scopes),
        }
    )


def actor_from_json(value: str) -> Actor:
    data = loads(value)
    return Actor(
        kind=ActorKind(data["kind"]),
        id=data["id"],
        collection_id=data["collection_id"],
        scopes=frozenset(Scope(s) for s in data["scopes"]),
    )


def settings_to_json(settings: CollectionSettings) -> str:
    return dumps(asdict(settings))


def settings_from_json(value: str) -> CollectionSettings:
    known = {f.name for f in fields(CollectionSettings)}
    # Se ignoran claves que ya no existan; las nuevas toman su valor por defecto
    return CollectionSettings(**{k: v for k, v in loads(value).items() if k in known})
