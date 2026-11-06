# Pendiente de implementar — Glosa

> Última actualización: 2026-11-06 · Spec v0.4.4 · 228 tests (y los 81 de `core` otra vez contra SQLite)

**Cómo se mantiene:** al cerrar una tarea se marca con `[x]` y se anota en el registro de avances del final. Si aparece trabajo nuevo, se añade en su sección. Las cifras del resumen se recalculan en cada entrega.

## Resumen

| Área | Estado |
|------|--------|
| Casos de uso (SPEC §11) | **14 de 25** |
| Pruebas obligatorias (SPEC §14) | **14 de 14 con test**, ejecutadas contra los dobles en memoria **y contra SQLite** |
| Puertos (SPEC §8) | 13 definidos; **12 con implementación real**. Falta `Embedder` |
| Adaptadores que piden los presets | 6 de 8 descubiertos por `check`; faltan `embedder: none` y `authenticator: token` |
| Cola de trabajos | Hecha sobre SQLite y validada con las pruebas de contrato, incluida la concurrencia |
| Endpoints de la API (SPEC §13) | **0 de 24** (3 descritos en el OpenAPI) |
| Servidor MCP | **0 de 3** herramientas |
| Worker | La lógica (`ProcessNextJob`) está en `core`; falta el proceso |
| Paquetes sin código | `retrieval`, `explain` |
| Frontend | No iniciado |

## 1. Core (fase 1) — casi cerrada

### Hecho
- [x] Entidades, puertos, autorización por roles y scopes, tokens, encadenado de hashes
- [x] `CreateCollection`, `IssueToken`, `RevokeToken`
- [x] `SubmitDocument`, `SearchCollection`, `ReadDocument`, `ListDocuments`
- [x] `HandleIngest` (ingest y modify) y `ProcessNextJob`
- [x] `GetJob`, `ListJobs`, `CancelJob`, `QueryOperations`, `VerifyOperationLog`
- [x] Las 14 pruebas obligatorias, con alcance completo sobre lo implementado
- [x] Puerto `UnitOfWork` y escrituras relacionadas en una sola transacción
- [x] Los tests de `core` se pueden ejecutar contra adaptadores reales (`GLOSA_TEST_ADAPTERS`)

### Casos de uso que faltan (11)
- [ ] `DeleteDocument` y `HandleDelete`
- [ ] `ReindexDocument` y `HandleReindex`
- [ ] `GetDocumentHistory`
- [ ] `RetryDeadJob`
- [ ] `ManageMembers`
- [ ] `ViewTrace`
- [ ] `ListCollections`, `UpdateCollectionSettings` y `DeleteCollection` (la API los necesita; la spec no los tenía y ya están en §11)

### Otras tareas del núcleo
- [ ] Ampliar las pruebas 1, 4 y 6 a medida que aparezcan los casos de uso que faltan
- [ ] Regla 6 de SPEC §18.4: los ajustes por colección no pueden debilitar la plantilla activa (va con `UpdateCollectionSettings`)
- [ ] Traducir la plantilla activa a `CollectionSettings` y a los parámetros de los casos de uso (`max_attempts`, caducidad por defecto de tokens)
- [ ] Respetar el ajuste `hash_chain` por colección en el registro
- [ ] Purga por retención (`retention_days`, `version_retention`)
- [ ] Renovar el lease (`heartbeat`) mientras un manejador trabaja
- [ ] Entrada de registro al arrancar con el nombre y el hash de la plantilla activa
- [ ] Limitación de peticiones por token y usuario
- [ ] Al borrar una colección, registrar el hecho en la cadena global (el registro de la propia colección se borra con ella)

## 2. Adaptadores (fase 2)

### `ingest` — hecho
- [x] Extractores de texto plano y Markdown, chunker por encabezados, registro por entry point

### `ingest` — pendiente
- [ ] Codificaciones que no sean UTF-8 (hoy falla con un mensaje claro)
- [ ] Encabezados Markdown subrayados (`===` y `---`)
- [ ] Tablas y listas como unidades propias en lugar de párrafos
- [ ] Solapamiento opcional entre fragmentos contiguos

### `storage` — hecho
- [x] SQLite: colecciones, accesos, documentos con su contenido, índice FTS5, cola, registro de operaciones y `UnitOfWork`
- [x] Migraciones numeradas, WAL, aislamiento por colección en el propio SQL y borrado de colección en cascada
- [x] Atomicidad probada con fallos inyectados; concurrencia probada con varios hilos; persistencia tras reabrir

### `storage` — pendiente
- [ ] `Database.close()` solo cierra la conexión del hilo que lo llama: hace falta cerrar las de todos los hilos cuando llegue la API
- [ ] `verify_chain` carga el registro entero en memoria: hacerlo por bloques para registros grandes
- [ ] Copia de seguridad y exportación de la base de datos
- [ ] Crear la base en `GLOSA_DATA_DIR` desde la composición de `app`

### Resto
- [ ] `retrieval`: estrategia de texto sobre `ChunkIndex`
- [ ] `explain`: agrupar el registro por `correlation_id` en trazas
- [ ] Registrar en `app` los adaptadores que viven en `core`: `authenticator: token` y `embedder: none`

## 3. Puntos de entrada (fase 3)

- [ ] `worker`: bucle sobre `ProcessNextJob`, parada ordenada, varias réplicas
- [ ] `http-api`: elegir framework, los 24 endpoints, errores uniformes, `Idempotency-Key`, `X-Correlation-Id`, `429` de capacidad, paginación, CORS y OpenAPI completo
- [ ] `mcp-server`: `buscar`, `leer_documento` y `listar_documentos`, con autenticación por token
- [ ] `app`: composición real (crear la base, construir los casos de uso con los adaptadores elegidos por la plantilla), datos de demo

## 4. Transversal

- [ ] Script `eval` con `recall@k` y sus conjuntos de preguntas. **Hoy faltan** `backend/examples/eval.yaml` y `backend/examples/acme-legal/eval.yaml`, que las plantillas ya referencian
- [ ] Datos de demostración para el preset `didactico`
- [ ] Integración continua (tests en memoria y contra SQLite, test de arquitectura, revisión de licencias de dependencias)
- [ ] Construir y probar de verdad la imagen Docker; activar `api`, `mcp` y `worker` en el compose

## 5. Frontend

- [ ] Elegir framework
- [ ] Cliente generado desde `docs/openapi.yaml`
- [ ] Las 9 funciones didácticas de SPEC §15

## 6. Documentación y legal

- [ ] Completar los 30 ADRs: todos están como "Propuesta" con las secciones vacías
- [ ] Diagramas: solo existe el de arquitectura general
- [ ] `LICENSE`: titular legal y texto oficial de PolyForm Small Business
- [ ] `LICENSE-COMERCIAL.md`: tramos y precios; revisión legal de la licencia y del CLA
- [ ] Marca **Glosa** (OEPM), dominios y usuario de GitHub; enlaces de apoyo

## 7. Más adelante (hoja de ruta)

- [ ] PDF, embeddings, búsqueda híbrida y comparador de estrategias
- [ ] Reranker, OCR, Postgres y pgvector, búsquedas por lotes
- [ ] OIDC para usuarios, OAuth 2.1 para clientes MCP y herramientas MCP de escritura

## Decisiones pendientes

Con propuesta por defecto, pendiente de confirmar:

- **Usuarios:** una API key personal por usuario, guardada con hash como los tokens, y una orden para crearlos. Hoy no hay puerto `UserRepository`; bloquea `ManageMembers` y la API

Sin propuesta todavía:

- Framework web y SDK de MCP (la spec propone FastAPI y el SDK oficial, sin ADR)
- Si un token `write` puede consultar el estado de sus trabajos
- Anclaje externo de la cadena de hashes: hoy no detecta que se borren las últimas entradas
- Framework del frontend
- Licenciatario en los despliegues a clientes (SPEC §19.5)

Decidida: **el contenido de los archivos vive en SQLite** (ADR 0027).

## Deuda técnica conocida

- El índice en memoria puntúa de forma muy simple: sirve para probar la mecánica, no para medir calidad de búsqueda. El de SQLite usa `bm25`, pero no se ha evaluado con un conjunto de preguntas real
- `Job.priority` existe pero ningún caso de uso lo asigna
- `UuidIds` usa 12 caracteres hexadecimales (48 bits): suficiente para demo, a revisar para producción
- No hay forma de ver la historia completa de un documento: cada operación tiene su propio `correlation_id`. Falta una consulta del registro por `target.document_id`
- Una versión cancelada o fallida queda en el historial sin haberse indexado nunca. Es coherente con que las versiones son inmutables, pero hay que mostrarlo bien en `GetDocumentHistory`
- El chunker descarta las secciones que solo tienen encabezado; su título solo sobrevive en la ruta de las secciones hijas
- SQLite admite un solo escritor a la vez. Basta para esta fase; Postgres está en la hoja de ruta
- Las transacciones anidadas se unen a la exterior: si una operación interior falla y el código exterior captura el error y sigue, lo que escribió la interior no se deshace. Hoy ningún caso de uso lo hace, pero hay que tenerlo presente
- Un trabajo con el lease vencido y un ack tardío del worker antiguo: el ack se ignora si el trabajo ya no está `running`, pero no hay identificador de worker que distinga a dos workers sobre el mismo trabajo

## Registro de avances

- **2026-11-06:** adaptadores de `storage` sobre SQLite (documentos, FTS5, cola, registro, colecciones, accesos) y puerto `UnitOfWork`; escrituras relacionadas atómicas. La batería de `core`, con las 14 pruebas obligatorias, pasa también contra SQLite. Spec v0.4.4.
- **2026-11-04:** `GetJob`, `ListJobs`, `CancelJob`, `QueryOperations` y `VerifyOperationLog`; adaptadores de `ingest`. Corregido un fallo de `SubmitDocument` con contenido ya cancelado. Spec v0.4.3.
- **2026-11-03:** núcleo ampliado con los puertos que faltaban, 9 casos de uso, dobles en memoria, contrato de la cola y las 14 pruebas obligatorias. Spec v0.4.2. Proyecto renombrado a Glosa; `Dockerfile`, `docker-compose.yml` y orden `check`.
- **2026-11-02:** plantillas de cliente, guardia de producción y modelo de licencia (spec v0.4).
