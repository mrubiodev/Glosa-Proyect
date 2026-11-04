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
