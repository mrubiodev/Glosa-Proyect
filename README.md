![Glosa — conocimiento documental conectado](docs/images/glosa-banner.svg)

# Glosa

**Plataforma en desarrollo para convertir documentos en una base de conocimiento RAG y exponerla mediante MCP, con un diseño centrado en permisos, trazabilidad y adaptación por cliente.**

Glosa tiene dos objetivos complementarios: **enseñar** cómo funcionan RAG y MCP haciendo visible su funcionamiento, y **ofrecer una base profesional** adaptable a distintos clientes mediante plantillas, sin modificar el núcleo.

> *Glosa*: la anotación que explica un texto. Es también la idea de su capa didáctica: aportar contexto y hacer comprensible lo que ocurre.

## Estado

El proyecto está en fase de diseño e implementación del núcleo. La arquitectura y el contrato están documentados, pero todavía no existe un flujo completo de ingesta y consulta de documentos.

| Pieza | Estado |
|-------|--------|
| Especificación (v0.4.1), ADRs y contrato OpenAPI | Documentados |
| Núcleo: entidades, puertos, permisos, tokens y registro encadenado | Implementado, con tests |
| Plantillas de cliente (carga, herencia y guardia de producción) | Implementado, con tests |
| Composición de aplicación y validación de configuración | Implementado, con tests |
| Dockerfile y Docker Compose | Preparados; validación de configuración y tests |
| Casos de uso, almacenamiento SQLite, API, servidor MCP y worker | Pendiente |
| Frontend | Pendiente |

## Inicio rápido

### En local

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
make install
make test        # suite documentada: 51 tests
make check       # valida la plantilla activa
```

### Con Docker

```bash
cd backend
docker compose up                              # valida la plantilla y termina
GLOSA_TEMPLATE=profesional docker compose up
docker compose --profile test run --rm tests
```

Estos comandos permiten validar la base actual; no levantan todavía un servicio RAG/MCP operativo. Más detalles en [`backend/README.md`](backend/README.md).

## Modelo de funcionamiento previsto

- Las **escrituras** (subir, modificar, borrar y reindexar) se encolarán y serán procesadas por un worker, en orden por colección y con operaciones idempotentes.
- Las **lecturas** (buscar, leer y listar) serán síncronas.
- Cada operación dejará una entrada en un **registro de solo añadir**, encadenado con hashes y relacionado mediante un `correlation_id` de extremo a extremo.
- Los LLM se conectarán al **servidor MCP** mediante un token de colección. El token fijará la colección y sus permisos, con lectura como permiso predeterminado.
- La autorización estará centralizada en `core`, compartida por la API y MCP.

Este es el comportamiento definido por el diseño; sus componentes pendientes se implementarán por etapas. El detalle está en [`docs/SPEC.md`](docs/SPEC.md).

## Estructura

```
docs/       especificación, ADRs, contrato OpenAPI, glosario, diagramas y licencias de dependencias
backend/    núcleo y paquetes del producto (ver backend/README.md)
frontend/   futuro cliente de la API, desacoplado del backend
```

## Adaptación a clientes

Cada cliente o proyecto se define con una **plantilla** YAML que hereda de los presets `didactico` y `profesional`:

```yaml
name: acme-legal
extends: profesional
mcp:
  tools:
    buscar: "Busca cláusulas en los contratos de Acme"
metadata: [fecha_contrato, jurisdiccion]
```

Las plantillas solo pueden elegir piezas y ajustes seguros: los invariantes (aislamiento por colección, autorización única y registro de solo añadir) no son configurables. En modo producción, la validación impide arrancar con credenciales de demo o configuraciones inseguras. Ver [`docs/SPEC.md`](docs/SPEC.md) §18.

## Licencia

Código disponible (*source-available*), **no** open source en sentido estricto.

- **Gratis** para personas y pequeñas empresas: licencia PolyForm Small Business 1.0.0 (`LICENSE`).
- **De pago** para las empresas que superen sus límites: licencia comercial (`LICENSE-COMERCIAL.md`, borrador).
- Para contribuir con código hace falta firmar el CLA (`CLA.md`). Ver [`CONTRIBUTING.md`](CONTRIBUTING.md).

> Los textos de licencia son borradores sin revisión legal. Además, `LICENSE` aún necesita el texto oficial y el titular legal. No debe considerarse lista para una publicación comercial. Ver [`docs/SPEC.md`](docs/SPEC.md) §19.6.

## Apoya el proyecto

Si lo usas y puedes, ayuda a que siga adelante. Es voluntario y no condiciona la licencia.

`<enlace de apoyo: GitHub Sponsors, Open Collective, Liberapay...>`

## Siguiente paso

Implementar los casos de uso de `core` (`backend/packages/core/src/glosa_core/usecases/`), empezando por los tests: crear colección, emitir token, subir documento y buscar. Después, el adaptador de almacenamiento en SQLite.
