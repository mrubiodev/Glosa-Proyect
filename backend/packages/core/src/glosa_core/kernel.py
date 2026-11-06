"""Servicios transversales que comparten todos los casos de uso."""
from __future__ import annotations

from dataclasses import dataclass, field

from .authorization import AuthorizationService
from .ports import Clock, IdGenerator, UnitOfWork
from .recorder import OperationRecorder
from .uow import NoTransaction


@dataclass(frozen=True)
class Kernel:
    authz: AuthorizationService
    recorder: OperationRecorder
    clock: Clock
    ids: IdGenerator
    uow: UnitOfWork = field(default_factory=NoTransaction)
