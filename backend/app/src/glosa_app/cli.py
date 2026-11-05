"""Línea de órdenes de Glosa.

Por ahora tiene una orden, `check`, que valida la plantilla activa (SPEC §18):
esquema, guardia de producción y estado de los adaptadores.

Variables de entorno:
  GLOSA_TEMPLATE       plantilla a usar: nombre de un preset, nombre de un fichero
                       en GLOSA_TEMPLATE_DIRS, o ruta a un .yaml. Por defecto, "didactico".
  GLOSA_TEMPLATE_DIRS  carpetas donde buscar plantillas de cliente, separadas por ":".
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Mapping, Sequence

from glosa_templates import Registry, TemplateError, load_template, validate_production

DEFAULT_TEMPLATE = "didactico"


def _template_dirs(env: Mapping[str, str]) -> list[str]:
    raw = env.get("GLOSA_TEMPLATE_DIRS", "")
    return [d for d in raw.split(os.pathsep) if d]


def check(env: Mapping[str, str], strict: bool, out=None, err=None) -> int:
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

    # Los adaptadores se descubren por entry points (grupo `glosa.adapters`)
    registry = Registry()
    registry.load_entry_points()
    missing = registry.missing(template)
    if missing:
        print(f"Adaptadores pendientes de implementar: {len(missing)}", file=out)
        if strict:
            for item in missing:
                print(f"  - {item}", file=err)
            return 1
    print("Plantilla válida.", file=out)
    return 0


def main(argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="glosa", description="Glosa: RAG y MCP con permisos y trazabilidad.")
    sub = parser.add_subparsers(dest="command", required=True)
    p_check = sub.add_parser("check", help="Valida la plantilla activa")
    p_check.add_argument(
        "--strict",
        action="store_true",
        help="Falla si la plantilla pide adaptadores que no están registrados",
    )
    args = parser.parse_args(argv)
    environment = os.environ if env is None else env
    if args.command == "check":
        return check(environment, strict=args.strict)
    return 2  # pragma: no cover
