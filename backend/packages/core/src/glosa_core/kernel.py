"""Servicios transversales que comparten todos los casos de uso."""
from __future__ import annotations

from dataclasses import dataclass

from .authorization import AuthorizationService
from .ports import Clock, IdGenerator
from .recorder import OperationRecorder


@dataclass(frozen=True)
class Kernel:
    authz: AuthorizationService
    recorder: OperationRecorder
    clock: Clock
    ids: IdGenerator
