"""Lectura didáctica del registro de operaciones: de entradas sueltas a una traza legible."""
from .trace import OUTCOME_LABELS, Trace, TraceStep, build_trace, describe

__all__ = ["OUTCOME_LABELS", "Trace", "TraceStep", "build_trace", "describe"]
