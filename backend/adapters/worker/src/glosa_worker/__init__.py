"""Worker de la cola de trabajos (capa fina)."""
from .runner import WorkerError, drain, run

__all__ = ["WorkerError", "drain", "run"]
