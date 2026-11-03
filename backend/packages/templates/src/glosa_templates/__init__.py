"""Plantillas de cliente (SPEC §18).

Una plantilla es un YAML declarativo que elige adaptadores y ajustes sin tocar
código. Hereda de otras (`extends`) y se valida al arrancar.
"""
from .errors import TemplateError
from .guard import validate_production
from .loader import load_template
from .model import Template
from .registry import Registry

__all__ = ["Registry", "Template", "TemplateError", "load_template", "validate_production"]
