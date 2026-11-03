# glosa-templates

Plantillas de cliente: la forma de adaptar el sistema a cualquier cliente o proyecto **sin tocar código**.

## Qué hace

- Carga plantillas YAML con herencia (`extends`): `didactico` → `profesional` → plantilla del cliente.
- Valida el esquema: lo que no está declarado se rechaza, y todos los errores se listan juntos.
- Aplica la **guardia de producción**: una plantilla en modo `production` no arranca con credenciales de demo, registro completo de consultas, sin retención o con secretos escritos en el fichero.
- Mantiene un **registro de adaptadores por nombre**, con descubrimiento de paquetes externos por entry points (`glosa.adapters`).

## Por qué existe como pieza separada

Para que el mismo núcleo sirva a un uso didáctico y a uno comercial. Las plantillas solo eligen piezas y ajustes; **no pueden desactivar los invariantes** (aislamiento por colección, autorización única, registro de solo añadir), porque no existen como opciones en el esquema.

## Cómo se usa suelto

```python
from glosa_templates import load_template, validate_production

t = load_template("acme-legal", search_dirs=["examples/templates"])
validate_production(t)                      # lanza TemplateError si algo no es seguro
t.get("policy.query_logging")               # "hash_only"
```

Plantilla de cliente mínima:

```yaml
name: acme-legal
extends: profesional
mcp:
  tools:
    buscar: "Busca cláusulas en los contratos de Acme"
metadata: [fecha_contrato, jurisdiccion]
```

Los presets (`didactico`, `profesional`) van incluidos y tienen prioridad sobre cualquier fichero con el mismo nombre.

## Qué se puede cambiar

Los ajustes del esquema (`schema.py`) y los adaptadores registrados. Las plantillas de cada cliente deben vivir en un repositorio privado aparte; este paquete solo lleva los presets.

## Estado

Implementado: carga, herencia, esquema, guardia de producción y registro, con tests.
Pendiente: conectar el registro con los adaptadores reales (`app/`) cuando existan.
