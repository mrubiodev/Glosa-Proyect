# Pendiente de implementar — Glosa

> Última actualización: 2026-11-03 · Spec v0.4.2 · 92 tests

**Cómo se mantiene:** al cerrar una tarea se marca con `[x]` y se anota en el registro de avances del final. Si aparece trabajo nuevo, se añade en su sección. Las cifras del resumen se recalculan en cada entrega.

## Resumen

| Área | Estado |
|------|--------|
| Casos de uso (SPEC §11) | **9 de 21** |
| Pruebas obligatorias (SPEC §14) | **14 de 14 con test**; alcance parcial en la 1, la 4 y la 6 (ver §1) |
| Puertos (SPEC §8) | 12 definidos. 3 con implementación real (`Authenticator` de tokens, `Clock`, `IdGenerator`); 8 solo con doble en memoria o de prueba; `Embedder` sin nada |
| Cola de trabajos | Contrato y doble en memoria hechos; falta el adaptador real |
| Endpoints de la API (SPEC §13) | **0 de 24** (3 descritos en el OpenAPI) |
| Servidor MCP | **0 de 3** herramientas |
| Worker | La lógica (`ProcessNextJob`) está en `core`; falta el proceso |
| Paquetes sin código | `ingest`, `retrieval`, `storage`, `explain` |
| Frontend | No iniciado |

## 1. Core (fase 1) — en curso

### Hecho
- [x] Entidades, puertos, autorización por roles y scopes, tokens, encadenado de hashes
- [x] Puertos nuevos: `CollectionRepository`, `IdGenerator`, `AccessRepository` ampliado
- [x] `SystemClock` y `UuidIds`
- [x] Dobles en memoria de todos los puertos y pruebas de contrato de la cola
- [x] `CreateCollection`, `IssueToken`, `RevokeToken`
- [x] `SubmitDocument` (nuevo y nueva versión, idempotencia, límites, contenido idéntico)
- [x] `SearchCollection` (con `query_logging` completo o `hash_only`), `ReadDocument`, `ListDocuments`
- [x] `HandleIngest` (ingest y modify) y `ProcessNextJob` (reintentos con espera creciente y `dead`)
- [x] Las 14 pruebas obligatorias tienen test

### Casos de uso que faltan (12)
- [ ] `DeleteDocument` y `HandleDelete`
- [ ] `ReindexDocument` y `HandleReindex`
- [ ] `GetDocumentHistory`
- [ ] `GetJob` y `ListJobs`
- [ ] `CancelJob`
- [ ] `RetryDeadJob`
- [ ] `ManageMembers`
- [ ] `QueryOperations`
- [ ] `ViewTrace`

### Otras tareas del núcleo
- [ ] Ampliar las pruebas 1, 4 y 6: hoy no pueden comprobar trabajos ni registro de otra colección porque `GetJob`, `ListJobs` y `QueryOperations` no existen
- [ ] Puerto `UnitOfWork`: `SubmitDocument` escribe en tres sitios (documento, versión y trabajo) sin transacción, y la spec (§9.4) exige atomicidad
- [ ] `UpdateCollectionSettings` y la regla 6 de SPEC §18.4: los ajustes por colección no pueden debilitar la plantilla activa
- [ ] Traducir la plantilla activa a `CollectionSettings` y a los parámetros de los casos de uso (`max_attempts`, caducidad por defecto de tokens)
- [ ] Respetar el ajuste `hash_chain` por colección en el registro
- [ ] Purga por retención (`retention_days`, `version_retention`)
- [ ] Renovar el lease (`heartbeat`) mientras un manejador trabaja
- [ ] Entrada de registro al arrancar con el nombre y el hash de la plantilla activa
- [ ] Limitación de peticiones por token y usuario

## 2. Adaptadores (fase 2)

- [ ] `ingest`: extractor de Markdown, extractor de texto plano y chunker por encabezados y párrafos
- [ ] `storage`: repositorio de documentos (SQLite y archivos), índice FTS5, cola (debe pasar `queue_contract`), registro de operaciones con sellado atómico, repositorios de colecciones y accesos
- [ ] `retrieval`: estrategia de texto sobre `ChunkIndex`
- [ ] `explain`: agrupar el registro por `correlation_id` en trazas

## 3. Puntos de entrada (fase 3)

- [ ] `worker`: bucle sobre `ProcessNextJob`, parada ordenada, varias réplicas
- [ ] `http-api`: elegir framework, los 24 endpoints, errores uniformes, `Idempotency-Key`, `X-Correlation-Id`, `429` de capacidad, paginación, CORS y OpenAPI completo
- [ ] `mcp-server`: `buscar`, `leer_documento` y `listar_documentos`, con autenticación por token
- [ ] `app`: composición real, registro de adaptadores, datos de demo y uso de `GLOSA_DATA_DIR`

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

- [ ] Completar los 24 ADRs: todos están como "Propuesta" con las secciones vacías
- [ ] Diagramas: solo existe el de arquitectura general
- [ ] `LICENSE`: titular legal y texto oficial de PolyForm Small Business
- [ ] `LICENSE-COMERCIAL.md`: tramos y precios; revisión legal de la licencia y del CLA
- [ ] Marca **Glosa** (OEPM), dominios y usuario de GitHub; enlaces de apoyo

## 7. Más adelante (hoja de ruta)

- [ ] PDF, embeddings, búsqueda híbrida y comparador de estrategias
- [ ] Reranker, OCR, Postgres y pgvector, búsquedas por lotes
- [ ] OIDC para usuarios, OAuth 2.1 para clientes MCP y herramientas MCP de escritura

## Decisiones pendientes

- Framework web y SDK de MCP (la spec propone FastAPI y el SDK oficial, sin ADR)
- Cómo se crean y se autentican los usuarios en la API (la spec dice "sesión o API key personal" sin concretar). Hoy no hay puerto `UserRepository`
- Si un token `write` puede consultar el estado de sus trabajos
- Dónde se guarda el contenido de los archivos: disco o base de datos
- Anclaje externo de la cadena de hashes: hoy no detecta que se borren las últimas entradas
- Framework del frontend
- Licenciatario en los despliegues a clientes (SPEC §19.5)

## Deuda técnica conocida

- La idempotencia de `SubmitDocument` hace `find_by_key` y luego `enqueue`: no es atómico. Los adaptadores reales necesitan una restricción de unicidad `(colección, clave)`
- El índice en memoria puntúa de forma muy simple: sirve para probar la mecánica, no para medir calidad de búsqueda
- `Job.priority` existe pero ningún caso de uso lo asigna
- `UuidIds` usa 12 caracteres hexadecimales (48 bits): suficiente para demo, a revisar para producción
- No hay forma de ver la historia completa de un documento: cada operación tiene su propio `correlation_id`. Falta una consulta del registro por `target.document_id`

## Registro de avances

- **2026-11-03:** núcleo ampliado con los puertos que faltaban, 9 casos de uso, dobles en memoria, contrato de la cola y las 14 pruebas obligatorias. Spec v0.4.2.
- **2026-11-03:** proyecto renombrado a Glosa; `Dockerfile`, `docker-compose.yml` y orden `check`.
- **2026-11-02:** plantillas de cliente, guardia de producción y modelo de licencia (spec v0.4).
