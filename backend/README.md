# Glosa — backend

Es el producto: núcleo, permisos, cola de trabajos, registro de operaciones, API de gestión y servidor MCP. La especificación está en [`../docs/SPEC.md`](../docs/SPEC.md).

## Estructura

```
packages/   core · ingest · retrieval · storage · explain · templates
adapters/   http-api · mcp-server · worker      (capas finas)
app/        composición y orden `check`: único sitio que conecta adaptadores con casos de uso
examples/   datos de demostración y plantilla de cliente de ejemplo
tests/      test de arquitectura (reglas de dependencia)
Dockerfile · docker-compose.yml · Makefile
```

## Puesta en marcha

### En local

```bash
python -m venv .venv && source .venv/bin/activate
make install
make test        # 149 tests
make check       # valida la plantilla activa
```

### Con Docker

```bash
docker compose up                              # valida la plantilla "didactico" y termina
GLOSA_TEMPLATE=profesional docker compose up   # valida la plantilla "profesional"
docker compose --profile test run --rm tests   # tests dentro de un contenedor
```

Los servicios `api`, `mcp` y `worker` están definidos pero agrupados en el perfil `pendiente` hasta que existan sus adaptadores. Detalles en `docs/SPEC.md` §17.

> Nota: el `Dockerfile` y el `docker-compose.yml` se comprobaron reproduciendo sus pasos fuera de Docker (instalación no editable en entorno limpio, `check` y tests). La primera construcción real con Docker puede pedir algún ajuste.

## Configuración

| Variable | Función | Por defecto |
|----------|---------|-------------|
| `GLOSA_TEMPLATE` | Plantilla activa: preset, nombre de fichero o ruta | `didactico` |
| `GLOSA_TEMPLATE_DIRS` | Carpetas con plantillas de cliente, separadas por `:` | `/app/templates` en la imagen |
| `GLOSA_DATA_DIR` | Carpeta de datos | `/data` |

## Plantillas de cliente

La adaptación a un cliente o proyecto se hace con una plantilla YAML (ver `docs/SPEC.md` §18 y `packages/templates/README.md`). Hay dos presets, `didactico` y `profesional`, y un ejemplo de cliente en `examples/templates/acme-legal.yaml`.

## Reglas de dependencia

Se comprueban automáticamente en `tests/test_architecture.py`:

- `core` no importa nada, ni siquiera librerías de terceros.
- `ingest`, `retrieval`, `storage`, `explain`, `templates` y los adaptadores solo pueden importar `core`.
- Solo `app` puede importar de todos.

## Estado

La lista completa y al día de lo que falta está en [`../docs/PENDIENTE.md`](../docs/PENDIENTE.md).

| Pieza | Estado |
|-------|--------|
| `core`: entidades, puertos, autorización, tokens, encadenado de hashes | Implementado, con tests |
| `core`: casos de uso | 14 de 22 implementados, con las 14 pruebas obligatorias |
| `templates`: carga con herencia, esquema, guardia de producción, registro de adaptadores | Implementado, con tests |
| `app`: orden `check` | Implementado, con tests |
| `ingest`: extractores de texto y Markdown, chunker por encabezados | Implementado, con tests |
| `retrieval`, `storage`, `explain` | Esqueleto |
| `http-api`, `mcp-server`, `worker` | Esqueleto (su punto de entrada avisa de que está pendiente) |
| `Dockerfile`, `docker-compose.yml` | Hechos; `check` y `tests` operativos |
