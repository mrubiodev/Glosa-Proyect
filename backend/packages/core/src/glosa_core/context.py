"""Contexto de una petición: quién, por qué canal y bajo qué correlation_id."""
from __future__ import annotations

from dataclasses import dataclass

from .domain import Actor, Channel
from .ports import IdGenerator


@dataclass(frozen=True)
class RequestContext:
    actor: Actor
    channel: Channel
    correlation_id: str

    @classmethod
    def new(cls, actor: Actor, channel: Channel, ids: IdGenerator) -> "RequestContext":
        """Contexto nuevo, con un correlation_id recién generado (API y MCP)."""
        return cls(actor, channel, ids.new_id("corr"))
