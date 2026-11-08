"""Línea de órdenes de Glosa.

  check    valida la plantilla activa: esquema, guardia de producción y adaptadores.
  worker   procesa la cola de trabajos (ingesta, modificación...) hasta que se le pida parar.

Variables de entorno (SPEC §17.3):
  GLOSA_TEMPLATE       plantilla a usar: nombre de un preset, de un fichero en
                       GLOSA_TEMPLATE_DIRS, o ruta a un .yaml. Por defecto, "didactico".
  GLOSA_TEMPLATE_DIRS  carpetas donde buscar plantillas de cliente, separadas por ":".
  GLOSA_DATA_DIR       carpeta de datos (la base de datos vive aquí). Por defecto, "./data".
  GLOSA_WORKER_ID, GLOSA_WORKER_LEASE_SECONDS   identidad y plazo de cada trabajo del worker.
"""
from __future__ import annotations

import argparse
import os
import signal
import sys
import threading
from typing import Mapping, Sequence

from glosa_templates import Registry, TemplateError, load_template, validate_production
from glosa_worker import WorkerError, drain, run

from .composition import ConfigurationError, build_from_env, default_registry

DEFAULT_TEMPLATE = "didactico"


def _template_dirs(env: Mapping[str, str]) -> list[str]:
    raw = env.get("GLOSA_TEMPLATE_DIRS", "")
    return [d for d in raw.split(os.pathsep) if d]


def check(env: Mapping[str, str], strict: bool, out=None, err=None, registry=None) -> int:
    # Se resuelven al llamar (no al importar) para que se puedan redirigir en los tests.
    out = out or sys.stdout
    err = err or sys.stderr
    ref = env.get("GLOSA_TEMPLATE", DEFAULT_TEMPLATE)
    try:
        template = load_template(ref, search_dirs=_template_dirs(env))
        validate_production(template)
    except TemplateError as exc:
        print(f"Plantilla '{ref}' no válida:", file=err)
        for problem in exc.problems:
            print(f"  - {problem}", file=err)
        return 1

    print(f"Plantilla:  {template.name}", file=out)
    print(f"Modo:       {template.mode}", file=out)
    print(f"Consultas:  {template.get('policy.query_logging')}", file=out)
    print(f"Retención:  {template.get('policy.retention_days') or 'sin límite'} días", file=out)
    print(f"Demo:       datos={template.get('demo.seed_data')} token={template.get('demo.demo_token')}", file=out)

    # Los adaptadores se descubren por entry points (grupo `glosa.adapters`) y los de core
    registry = registry or default_registry()
    missing = registry.missing(template)
    if missing:
        print(f"Adaptadores pendientes de implementar: {len(missing)}", file=out)
        if strict:
            for item in missing:
                print(f"  - {item}", file=err)
            return 1
    print("Plantilla válida.", file=out)
    return 0


def worker(
    env: Mapping[str, str],
    *,
    once: bool = False,
    idle_seconds: float = 1.0,
    stop: threading.Event | None = None,
    install_signals: bool = True,
    out=None,
    err=None,
) -> int:
    """Arranca un worker. Devuelve el código de salida (0 correcto, 1 error de configuración)."""
    out = out or sys.stdout
    err = err or sys.stderr
    try:
        app = build_from_env(env)
    except (TemplateError, ConfigurationError) as exc:
        print(str(exc), file=err)
        return 1

    stop = stop or threading.Event()
    previous: dict[int, object] = {}
    if install_signals and threading.current_thread() is threading.main_thread():
        # SIGTERM (docker stop) y Ctrl+C piden parar: se termina el trabajo en curso y se sale
        for sig in (signal.SIGTERM, signal.SIGINT):
            previous[sig] = signal.signal(sig, lambda *_: stop.set())

    print(f"Worker listo: plantilla {app.template.name}, datos en {env.get('GLOSA_DATA_DIR', './data')}", file=out)
    try:
        if once:
            processed = drain(app.process_next_job.execute)
        else:
            processed = run(
                app.process_next_job.execute,
                stop=stop,
                idle_seconds=idle_seconds,
                on_error=lambda exc: print(f"Fallo de infraestructura: {exc}", file=err),
            )
    except WorkerError as exc:
        print(str(exc), file=err)
        return 1
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        app.close()
    print(f"Trabajos procesados: {processed}", file=out)
    return 0


def main(argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="glosa", description="Glosa: RAG y MCP con permisos y trazabilidad.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Valida la plantilla activa")
    p_check.add_argument(
        "--strict", action="store_true",
        help="Falla si la plantilla pide adaptadores que no están registrados",
    )

    p_worker = sub.add_parser("worker", help="Procesa la cola de trabajos")
    p_worker.add_argument(
        "--once", action="store_true",
        help="Procesa los trabajos que haya listos y termina (en lugar de quedarse esperando)",
    )
    p_worker.add_argument(
        "--idle-seconds", type=float, default=1.0,
        help="Segundos de espera cuando no hay trabajos (por defecto, 1)",
    )

    args = parser.parse_args(argv)
    environment = os.environ if env is None else env
    if args.command == "check":
        return check(environment, strict=args.strict)
    if args.command == "worker":
        return worker(environment, once=args.once, idle_seconds=args.idle_seconds)
    return 2  # pragma: no cover
