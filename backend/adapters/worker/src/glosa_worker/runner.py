"""Bucle del worker: llama una y otra vez a "procesa el siguiente trabajo".

No sabe nada de colas, bases de datos ni plantillas: recibe una función que procesa un
trabajo y devuelve el trabajo (o `None` si no había ninguno). La lógica de qué hacer con cada
trabajo, reintentos incluidos, está en `core` (`ProcessNextJob`).
"""
from __future__ import annotations

import threading
from typing import Any, Callable

MAX_BACKOFF_SECONDS = 30.0


class WorkerError(RuntimeError):
    """El worker se rindió tras demasiados fallos seguidos de infraestructura."""


def run(
    process_next: Callable[[], Any],
    *,
    stop: threading.Event,
    idle_seconds: float = 1.0,
    max_consecutive_errors: int = 20,
    on_job: Callable[[Any], None] | None = None,
    on_error: Callable[[BaseException], None] | None = None,
) -> int:
    """Procesa trabajos hasta que `stop` se active. Devuelve cuántos procesó.

    - Sin trabajo, espera `idle_seconds` (la espera se interrumpe en cuanto se pide parar).
    - Un trabajo que falla NO llega aquí: `ProcessNextJob` ya decide su reintento o su fallo.
      Lo que sí llega son los fallos de infraestructura (por ejemplo, la base bloqueada):
      se avisa, se espera con espera creciente y se sigue. Si se repiten
      `max_consecutive_errors` veces seguidas, el worker se rinde con `WorkerError` para que
      el orquestador lo reinicie en lugar de quedarse colgado.
    - Al pedir parar, termina el trabajo que tenga entre manos antes de salir.
    """
    processed = 0
    consecutive_errors = 0
    while not stop.is_set():
        try:
            job = process_next()
        except Exception as exc:  # infraestructura, no un fallo del trabajo
            consecutive_errors += 1
            if on_error:
                on_error(exc)
            if consecutive_errors >= max_consecutive_errors:
                raise WorkerError(
                    f"{consecutive_errors} fallos seguidos de infraestructura; último: {exc}"
                ) from exc
            stop.wait(min(idle_seconds * 2 ** (consecutive_errors - 1), MAX_BACKOFF_SECONDS))
            continue
        consecutive_errors = 0
        if job is None:
            stop.wait(idle_seconds)
            continue
        processed += 1
        if on_job:
            on_job(job)
    return processed


def drain(process_next: Callable[[], Any], *, limit: int | None = None) -> int:
    """Procesa los trabajos que haya listos y termina. Devuelve cuántos procesó.

    Un trabajo en espera de reintento no está "listo", así que no se espera por él.
    """
    processed = 0
    while limit is None or processed < limit:
        if process_next() is None:
            break
        processed += 1
    return processed
