# Registro de decisiones de arquitectura (ADR)

Cada decisión relevante se documenta en un fichero numerado. Estados: *Propuesta*, *Aceptada*, *Sustituida*.

| ADR | Decisión | Estado |
|-----|----------|--------|
| [0001](0001-monorepo-de-paquetes-en-el-backend.md) | Monorepo de paquetes en el backend | Propuesta |
| [0002](0002-puertos-y-adaptadores-con-protocol.md) | Puertos y adaptadores con `Protocol` | Propuesta |
| [0003](0003-sqlite-fts5-como-primer-indice.md) | SQLite FTS5 como primer índice | Propuesta |
| [0004](0004-servidor-mcp-unico-multitenant-con-token.md) | Servidor MCP único multitenant con token | Propuesta |
| [0005](0005-capa-didactica-como-lectura-del-registro.md) | Capa didáctica como lectura del registro | Propuesta |
| [0006](0006-ingesta-asincrona-con-estados.md) | Ingesta asíncrona con estados | Propuesta |
| [0007](0007-frontend-y-backend-separados-contrato-openapi.md) | Frontend y backend separados, contrato OpenAPI | Propuesta |
| [0008](0008-autorizacion-unica-en-core-para-api-y-mcp.md) | Autorización única en `core` para API y MCP | Propuesta |
| [0009](0009-mcp-de-solo-lectura-por-defecto.md) | MCP de solo lectura por defecto | Propuesta |
| [0010](0010-cola-de-trabajos-con-entrega-al-menos-una-vez-y-ma.md) | Cola de trabajos con entrega al menos una vez y manejadores idempotentes | Propuesta |
| [0011](0011-lecturas-sincronas-escrituras-por-cola.md) | Lecturas síncronas, escrituras por cola | Propuesta |
| [0012](0012-operationlog-unico-solo-de-anadir-con-correlation.md) | `OperationLog` único, solo de añadir, con `correlation_id` | Propuesta |
| [0013](0013-versionado-inmutable-de-documentos.md) | Versionado inmutable de documentos | Propuesta |
| [0014](0014-plantillas-yaml-con-herencia-didactico-profesional.md) | Plantillas YAML con herencia (`didactico`, `profesional`, cliente) | Propuesta |
| [0015](0015-las-plantillas-no-pueden-configurar-los-invariante.md) | Las plantillas no pueden configurar los invariantes de seguridad | Propuesta |
| [0016](0016-guardia-de-produccion-y-secretos-por-variables-de.md) | Guardia de producción y secretos por variables de entorno | Propuesta |
| [0017](0017-adaptadores-como-plugins-registrados-por-nombre.md) | Adaptadores como plugins registrados por nombre | Propuesta |
| [0018](0018-una-instalacion-por-cliente-plantillas-de-cliente.md) | Una instalación por cliente; plantillas de cliente en repositorio privado | Propuesta |
| [0019](0019-codigo-disponible-polyform-small-business-mas-lice.md) | Código disponible: PolyForm Small Business más licencia comercial y CLA | Propuesta |
| [0020](0020-nombre-del-proyecto-glosa.md) | Nombre del proyecto: Glosa | Propuesta |
| [0021](0021-imagen-docker-multietapa-usuario-sin-privilegios-y.md) | Imagen Docker multietapa, usuario sin privilegios y sin secretos | Propuesta |
| [0022](0022-los-casos-de-uso-reciben-un-requestcontext-y-regis.md) | Los casos de uso reciben un `RequestContext` y registran su propio resultado | Propuesta |
| [0023](0023-fragmentos-con-identificador-determinista-y-limpie.md) | Fragmentos con identificador determinista y limpieza previa al indexar | Propuesta |
| [0024](0024-pruebas-de-contrato-para-los-adaptadores-de-la-col.md) | Pruebas de contrato para los adaptadores de la cola | Propuesta |
| [0025](0025-chunker-por-encabezados-con-la-ruta-de-encabezados.md) | Chunker por encabezados con la ruta de encabezados en cada fragmento | Propuesta |
| [0026](0026-los-adaptadores-se-descubren-por-entry-points-del.md) | Los adaptadores se descubren por entry points del grupo `glosa.adapters` | Propuesta |
| [0027](0027-el-contenido-de-los-archivos-vive-dentro-de-sqlite.md) | El contenido de los archivos vive dentro de SQLite | Propuesta |
| [0028](0028-puerto-unitofwork-las-escrituras-relacionadas-se-c.md) | Puerto `UnitOfWork`: las escrituras relacionadas se confirman juntas | Propuesta |
| [0029](0029-consulta-de-texto-palabras-entre-comillas-unidas-c.md) | Consulta de texto: palabras entre comillas unidas con OR, orden por bm25 | Propuesta |
| [0030](0030-los-tests-de-core-se-ejecutan-tambien-contra-los-a.md) | Los tests de `core` se ejecutan también contra los adaptadores reales | Propuesta |
| [0031](0031-la-composicion-construye-el-sistema-desde-la-plant.md) | La composición construye el sistema desde la plantilla y se niega a arrancar si es insegura o incompleta | Propuesta |
| [0032](0032-el-worker-es-un-bucle-sin-logica-de-negocio-reinte.md) | El worker es un bucle sin lógica de negocio: reintentos y `dead` viven en `core` | Propuesta |
| [0033](0033-actor-y-canal-system-para-eventos-sin-persona-sin.md) | Actor y canal `system` para eventos sin persona, sin ningún permiso | Propuesta |
| [0034](0034-el-paquete-retrieval-se-pospone-hasta-que-existan.md) | El paquete `retrieval` se pospone hasta que existan varias estrategias de búsqueda | Propuesta |
| [0035](0035-autoridad-por-coleccion-modo-propio-o-modo-goberna.md) | Autoridad por colección: modo propio o modo gobernado por un sistema externo (ATLAS) | Propuesta |
| [0036](0036-los-indices-son-derivados-y-reconstruibles.md) | Los índices son derivados y reconstruibles | Propuesta |
| [0037](0037-la-integracion-con-atlas-se-hace-por-contratos-exp.md) | La integración con ATLAS se hace por contratos explícitos y no se implementa hasta que existan y estén verificados | Propuesta |
| [0038](0038-en-modo-gobernado-la-autorizacion-se-vuelve-a-comp.md) | En modo gobernado la autorización se vuelve a comprobar al consultar y falla cerrada | Propuesta |
| [0039](0039-rag-en-glosa-es-recuperacion-y-contexto-con-eviden.md) | RAG en Glosa es recuperación y contexto con evidencias; la generación es opcional y la hace por defecto el consumidor | Propuesta |
