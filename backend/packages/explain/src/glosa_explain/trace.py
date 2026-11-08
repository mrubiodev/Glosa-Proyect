"""De entradas del registro a una traza que se pueda leer paso a paso."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Sequence

from glosa_core.domain import OperationEntry, Outcome

OUTCOME_LABELS = {
    "succeeded": "correcto",
    "failed": "fallido",
    "denied": "denegado",
    "in_progress": "en curso",
}


def _n(count, singular: str, plural: str) -> str:
    """"1 fragmento", "2 fragmentos": la concordancia correcta para cualquier cantidad."""
    if count is None:
        return f"? {plural}"
    return f"{count} {singular if count == 1 else plural}"


@dataclass(frozen=True)
class TraceStep:
    index: int  # empieza en 1
    at: datetime
    action: str  # nombre técnico, p. ej. "document.extract"
    title: str  # lo que ocurrió, en lenguaje llano
    detail: str  # datos concretos (puede estar vacío)
    outcome: str  # "allowed" | "denied" | "succeeded" | "failed"
    channel: str  # "api", "mcp", "worker" o "system"
    actor_id: str
    duration_ms: int | None


@dataclass(frozen=True)
class Trace:
    correlation_id: str
    collection_id: str | None
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    outcome: str  # "succeeded" | "failed" | "denied" | "in_progress"
    steps: tuple[TraceStep, ...]
    channels: tuple[str, ...]  # canales por los que pasó, en orden
    actors: tuple[str, ...]

    def to_text(self) -> str:
        """La traza como texto para leer en una terminal o en un informe."""
        head = (
            f"Traza {self.correlation_id} · resultado: {OUTCOME_LABELS[self.outcome]} · "
            f"{_n(len(self.steps), 'paso', 'pasos')} · {self.duration_ms} ms"
        )
        lines = [head]
        for step in self.steps:
            stamp = step.at.strftime("%H:%M:%S.%f")[:-3]
            lines.append(f"{step.index:>2}. {stamp} [{step.channel}] {step.actor_id} — {step.title}")
            if step.detail:
                lines.append(f"      {step.detail}")
        return "\n".join(lines)


# --- Descripciones ----------------------------------------------------------------

def _submit(e: OperationEntry) -> tuple[str, str]:
    d, t = e.details, e.target
    if d.get("deduplicated"):
        return "Petición repetida", f"Se devolvió el trabajo que ya existía ({t.get('job_id')})"
    if d.get("unchanged"):
        return "Documento sin cambios", f"Es idéntico a la versión vigente ({t.get('version')}); no se creó trabajo"
    return (
        "Se recibió el documento",
        f"Versión {t.get('version')}, {_n(d.get('size'), 'byte', 'bytes')}; trabajo {t.get('job_id')} en cola",
    )


def _search(e: OperationEntry) -> tuple[str, str]:
    d = e.details
    found = len(d.get("hits", []))
    query = f"«{d['query']}»" if "query" in d else "consulta no guardada (solo su huella)"
    return "Búsqueda", f"{query} → {_n(found, 'resultado', 'resultados')}"


def _ingest(e: OperationEntry) -> tuple[str, str]:
    d, t = e.details, e.target
    retired = d.get("retired_versions") or []
    extra = f"; versiones anteriores retiradas del índice: {retired}" if retired else ""
    return "Documento listo para buscar", f"Versión {t.get('version')} con {_n(d.get('chunks'), 'fragmento', 'fragmentos')}{extra}"


_DESCRIBERS: dict[str, Callable[[OperationEntry], tuple[str, str]]] = {
    "collection.create": lambda e: ("Se creó la colección", f"Nombre: {e.details.get('name')}"),
    "token.issue": lambda e: (
        "Se emitió un token",
        f"Permisos: {', '.join(e.details.get('scopes', []))}; caduca: {e.details.get('expires_at') or 'nunca'}",
    ),
    "token.revoke": lambda e: ("Se revocó un token", ""),
    "document.submit": _submit,
    "job.start": lambda e: (
        "El worker tomó el trabajo",
        f"Intento {e.details.get('attempt')} ({e.details.get('type')})",
    ),
    "document.extract": lambda e: ("Texto extraído del archivo", _n(e.details.get("chars"), "carácter", "caracteres")),
    "document.chunk": lambda e: ("Texto dividido en fragmentos", _n(e.details.get("chunks"), "fragmento", "fragmentos")),
    "document.index": lambda e: (
        "Fragmentos añadidos al índice de búsqueda",
        _n(e.details.get("chunks"), "fragmento", "fragmentos"),
    ),
    "document.ingest": _ingest,
    "job.succeed": lambda e: ("Trabajo terminado", ""),
    "job.retry": lambda e: (
        "El trabajo falló y se reintentará",
        f"{e.details.get('error')} — próximo intento: {e.details.get('retry_at')}",
    ),
    "job.dead": lambda e: (
        "El trabajo falló definitivamente",
        f"{e.details.get('error')} (tras {_n(e.details.get('attempts'), 'intento', 'intentos')})",
    ),
    "job.cancel": lambda e: ("Se canceló el trabajo", ""),
    "job.get": lambda e: ("Se consultó un trabajo", f"Estado: {e.details.get('status')}"),
    "jobs.list": lambda e: ("Se listaron los trabajos", _n(e.details.get("count"), "trabajo", "trabajos")),
    "search.execute": _search,
    "document.read": lambda e: ("Se leyó un documento", f"Versión {e.target.get('version')}"),
    "documents.list": lambda e: ("Se listaron los documentos", _n(e.details.get("count"), "documento", "documentos")),
    "operations.query": lambda e: ("Se consultó el registro", _n(e.details.get("count"), "entrada", "entradas")),
    "operations.verify": lambda e: (
        "Se verificó el registro",
        "cadena íntegra" if e.details.get("valid") else f"cadena rota en {e.details.get('broken_at')}",
    ),
    "trace.view": lambda e: ("Se consultó una traza", _n(e.details.get("steps"), "paso", "pasos")),
    "template.applied": lambda e: (
        "El sistema arrancó con una plantilla",
        f"{e.details.get('name')} ({e.details.get('mode')}), huella {str(e.details.get('fingerprint'))[:12]}",
    ),
}

# Fallos que ya describe su propio descriptor, en lugar del texto genérico
_OWN_FAILURE_TEXT = {"job.retry", "job.dead"}


def describe(entry: OperationEntry) -> tuple[str, str]:
    """Título y detalle de una entrada, en lenguaje llano."""
    if entry.outcome is Outcome.DENIED:
        d = entry.details
        return (
            "Acceso denegado",
            f"Faltaba el permiso «{d.get('permission', '?')}»: {d.get('reason', 'sin motivo registrado')}",
        )
    if entry.outcome is Outcome.FAILED and entry.action not in _OWN_FAILURE_TEXT:
        title, _ = _DESCRIBERS.get(entry.action, lambda e: (e.action, ""))(entry)
        return f"{title} — falló", str(entry.details.get("error", "sin detalle"))
    describer = _DESCRIBERS.get(entry.action)
    return describer(entry) if describer else (entry.action, "")


def _overall_outcome(entries: Sequence[OperationEntry]) -> str:
    actions = [e.action for e in entries]
    last = entries[-1]
    if any(e.outcome is Outcome.DENIED for e in entries):
        return "denied"
    if last.action == "job.dead" or (
        last.outcome is Outcome.FAILED and last.action != "job.retry"
    ):
        return "failed"
    has_job = any(a.startswith("job.") for a in actions)
    if has_job and last.action not in ("job.succeed", "job.cancel"):
        return "in_progress"  # el trabajo empezó o espera un reintento, pero no terminó
    if "document.submit" in actions and not has_job:
        deduplicated_or_unchanged = entries[0].details.get("deduplicated") or entries[0].details.get("unchanged")
        return "succeeded" if deduplicated_or_unchanged else "in_progress"  # en cola, sin procesar
    return "succeeded"


def build_trace(entries: Sequence[OperationEntry]) -> Trace:
    """Construye la traza de una operación a partir de sus entradas del registro.

    Las entradas deben compartir `correlation_id` y venir de antigua a reciente, que es como las
    devuelven `QueryOperations` y `ViewTrace`.
    """
    if not entries:
        raise ValueError("No hay entradas con las que construir una traza")
    correlation_ids = {e.correlation_id for e in entries}
    if len(correlation_ids) != 1:
        raise ValueError(f"Las entradas mezclan varias operaciones: {sorted(correlation_ids)}")

    steps = []
    for index, e in enumerate(entries, start=1):
        title, detail = describe(e)
        steps.append(
            TraceStep(index, e.at, e.action, title, detail, e.outcome.value, e.channel.value,
                      e.actor.id, e.duration_ms)
        )
    started, finished = entries[0].at, entries[-1].at
    channels: list[str] = []
    for e in entries:
        if not channels or channels[-1] != e.channel.value:
            channels.append(e.channel.value)
    return Trace(
        correlation_id=entries[0].correlation_id,
        collection_id=entries[0].collection_id,
        started_at=started,
        finished_at=finished,
        duration_ms=max(0, int((finished - started).total_seconds() * 1000)),
        outcome=_overall_outcome(entries),
        steps=tuple(steps),
        channels=tuple(channels),
        actors=tuple(dict.fromkeys(e.actor.id for e in entries)),
    )
