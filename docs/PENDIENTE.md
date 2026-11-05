# Pendiente de implementar — Glosa

> Última actualización: 2026-11-04 · Spec v0.4.3 · 149 tests

**Cómo se mantiene:** al cerrar una tarea se marca con `[x]` y se anota en el registro de avances del final. Si aparece trabajo nuevo, se añade en su sección. Las cifras del resumen se recalculan en cada entrega.

## Resumen

| Área | Estado |
|------|--------|
| Casos de uso (SPEC §11) | **14 de 22** |
| Pruebas obligatorias (SPEC §14) | **14 de 14 con test**, con alcance completo sobre los casos de uso que existen hoy |
| Puertos (SPEC §8) | 12 definidos. 5 con implementación real (`Authenticator` de tokens, `Clock`, `IdGenerator`, `TextExtractor`, `Chunker`); 6 solo con doble en memoria; `Embedder` sin nada |
| Adaptadores descubiertos por `check` | 3 de 8 (extractores `markdown` y `text`, chunker `headings`); faltan `storage`, `queue`, `index`, `embedder` y `authenticator` |
| Cola de trabajos | Contrato y doble en memoria hechos; falta el adaptador real |
| Endpoints de la API (SPEC §13) | **0 de 24** (3 descritos en el OpenAPI) |
| Servidor MCP | **0 de 3** herramientas |
| Worker | La lógica (`ProcessNextJob`) está en `core`; falta el proceso |
| Paquetes sin código | `retrieval`, `storage`, `explain` |
| Frontend | No iniciado |

## 1. Core (fase 1) — casi cerrada

### Hecho
- [x] Entidades, puertos, autorización por roles y scopes, tokens, encadenado de hashes
- [x] Puertos nuevos: `CollectionRepository`, `IdGenerator`, `AccessRepository` ampliado
- [x] `SystemClock` y `UuidIds`
- [x] Dobles en memoria de todos los puertos y pruebas de contrato de la cola
- [x] `CreateCollection`, `IssueToken`, `RevokeToken`
- [x] `SubmitDocument` (nuevo y nueva versión, idempotencia, límites, "sin cambios" frente a la versión vigente)
- [x] `SearchCollection` (con `query_logging` completo o `hash_only`), `ReadDocument`, `ListDocuments`
- [x] `HandleIngest` (ingest y modify) y `ProcessNextJob` (reintentos con espera creciente y `dead`)
- [x] `GetJob`, `ListJobs`, `CancelJob`
- [x] `QueryOperations` y `VerifyOperationLog`
- [x] Las 14 pruebas obligatorias tienen test; las 1, 4 y 6 cubren trabajos y registro
- [x] `World` reutilizable (`glosa_core.testing_world`) para probar otros paquetes dentro del flujo real

### Casos de uso que faltan (8)
- [ ] `DeleteDocument` y `HandleDelete`
- [ ] `ReindexDocument` y `HandleReindex`
- [ ] `GetDocumentHistory`
- [ ] `RetryDeadJob`
- [ ] `ManageMembers`
- [ ] `ViewTrace`

### Otras tareas del núcleo
- [ ] Ampliar las pruebas 1, 4 y 6 a medida que aparezcan `GetDocumentHistory`, `ViewTrace`, `ManageMembers` y `RetryDeadJob`
- [ ] Puerto `UnitOfWork`: `SubmitDocument` escribe en tres sitios (documento, versión y trabajo) sin transacción, y la spec (§9.4) exige atomicidad
- [ ] `UpdateCollectionSettings` y la regla 6 de SPEC §18.4: los ajustes por colección no pueden debilitar la plantilla activa
- [ ] Traducir la plantilla activa a `CollectionSettings` y a los parámetros de los casos de uso (`max_attempts`, caducidad por defecto de tokens)
- [ ] Respetar el ajuste `hash_chain` por colección en el registro
- [ ] Purga por retención (`retention_days`, `version_retention`)
- [ ] Renovar el lease (`heartbeat`) mientras un manejador trabaja
- [ ] Entrada de registro al arrancar con el nombre y el hash de la plantilla activa
- [ ] Limitación de peticiones por token y usuario

## 2. Adaptadores (fase 2)

### `ingest` — hecho
- [x] Extractor de texto plano y extractor de Markdown (con retirada del front matter)
- [x] Chunker por encabezados con ruta de encabezados, bloques de código y límites de tamaño
- [x] Registro por entry point `glosa.adapters`

### `ingest` — pendiente
- [ ] Detección o configuración de codificaciones que no sean UTF-8 (hoy falla con un mensaje claro)
- [ ] Encabezados Markdown subrayados (`===` y `---`)
- [ ] Tablas y listas como unidades propias en lugar de párrafos
- [ ] Solapamiento opcional entre fragmentos contiguos

### Resto
- [ ] `storage`: repositorio de documentos (SQLite y archivos), índice FTS5, cola (debe pasar `queue_contract`), registro de operaciones con sellado atómico, repositorios de colecciones y accesos
- [ ] `retrieval`: estrategia de texto sobre `ChunkIndex`
- [ ] `explain`: agrupar el registro por `correlation_id` en trazas
- [ ] Registrar en `app` los adaptadores que viven en `core`: `authenticator: token` y `embedder: none`

## 3. Puntos de entrada (fase 3)

- [ ] `worker`: bucle sobre `ProcessNextJob`, parada ordenada, varias réplicas
- [ ] `http-api`: elegir framework, los 24 endpoints, errores uniformes, `Idempotency-Key`, `X-Correlation-Id`, `429` de capacidad, paginación, CORS y OpenAPI completo
- [ ] `mcp-server`: `buscar`, `leer_documento` y `listar_documentos`, con autenticación por token
- [ ] `app`: composición real, datos de demo y uso de `GLOSA_DATA_DIR`

## 4. Transversal

- [ ] Script `eval` con `recall@k` y sus conjuntos de preguntas. **Hoy faltan** `backend/examples/eval.yaml` y `backend/examples/acme-legal/eval.yaml`, que las plantillas ya referencian
- [ ] Datos de demostración para el preset `didactico`
- [ ] Integración continua (tests, test de arquitectura, revisión de licencias de dependencias)
- [ ] Construir y probar de verdad la imagen Docker; activar `api`, `mcp` y `worker` en el compose

## 5. Frontend

- [ ] Elegir framework
- [ ] Cliente generado desde `docs/openapi.yaml`
- [ ] Las 9 funciones didácticas de SPEC §15

## 6. Documentación y legal

- [ ] Completar los 26 ADRs: todos están como "Propuesta" con las secciones vacías
- [ ] Diagramas: solo existe el de arquitectura general
- [ ] `LICENSE`: titular legal y texto oficial de PolyForm Small Business
- [ ] `LICENSE-COMERCIAL.md`: tramos y precios; revisión legal de la licencia y del CLA
- [ ] Marca **Glosa** (OEPM), dominios y usuario de GitHub; enlaces de apoyo

## 7. Más adelante (hoja de ruta)

- [ ] PDF, embeddings, búsqueda híbrida y comparador de estrategias
- [ ] Reranker, OCR, Postgres y pgvector, búsquedas por lotes
- [ ] OIDC para usuarios, OAuth 2.1 para clientes MCP y herramientas MCP de escritura

## Decisiones pendientes

Con propuesta por defecto, pendientes de confirmar:

- **Contenido de los archivos:** propuesto dentro de SQLite (atómico con la transacción y una sola copia de seguridad). Cambiarlo a disco es cambiar un adaptador
- **Usuarios:** propuesta de una API key personal por usuario, guardada con hash como los tokens, y una orden para crearlos. Hoy no hay puerto `UserRepository`; bloquea `ManageMembers` y la API

Sin propuesta todavía:

- Framework web y SDK de MCP (la spec propone FastAPI y el SDK oficial, sin ADR)
- Si un token `write` puede consultar el estado de sus trabajos
- Anclaje externo de la cadena de hashes: hoy no detecta que se borren las últimas entradas
- Framework del frontend
- Licenciatario en los despliegues a clientes (SPEC §19.5)

## Deuda técnica conocida

- La idempotencia de `SubmitDocument` hace `find_by_key` y luego `enqueue`: no es atómico. Los adaptadores reales necesitan una restricción de unicidad `(colección, clave)`
- El índice en memoria puntúa de forma muy simple: sirve para probar la mecánica, no para medir calidad de búsqueda
- `Job.priority` existe pero ningún caso de uso lo asigna
- `UuidIds` usa 12 caracteres hexadecimales (48 bits): suficiente para demo, a revisar para producción
- No hay forma de ver la historia completa de un documento: cada operación tiene su propio `correlation_id`. Falta una consulta del registro por `target.document_id`
- Una versión cancelada o fallida queda en el historial del documento sin haberse indexado nunca. Es coherente con que las versiones son inmutables, pero hay que mostrarlo bien en `GetDocumentHistory`
- El chunker descarta las secciones que solo tienen encabezado; su título solo sobrevive en la ruta de las secciones hijas

## Registro de avances

- **2026-11-04:** `GetJob`, `ListJobs`, `CancelJob`, `QueryOperations` y `VerifyOperationLog`; pruebas 1, 4 y 6 con alcance completo; adaptadores de `ingest` (extractores y chunker por encabezados) descubiertos por entry point. Corregido un fallo de `SubmitDocument` con contenido ya cancelado. Spec v0.4.3.
- **2026-11-03:** núcleo ampliado con los puertos que faltaban, 9 casos de uso, dobles en memoria, contrato de la cola y las 14 pruebas obligatorias. Spec v0.4.2.
- **2026-11-03:** proyecto renombrado a Glosa; `Dockerfile`, `docker-compose.yml` y orden `check`.
- **2026-11-02:** plantillas de cliente, guardia de producción y modelo de licencia (spec v0.4).
