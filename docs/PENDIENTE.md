# Pendiente de implementar — Glosa

> Última actualización: 2026-11-07 · Spec v0.4.5 · 289 tests (y los 90 de `core` otra vez contra SQLite)

**Cómo se mantiene:** al cerrar una tarea se marca con `[x]` y se anota en el registro de avances del final. Si aparece trabajo nuevo, se añade en su sección. Las cifras del resumen se recalculan en cada entrega.

## Resumen

| Área | Estado |
|------|--------|
| Recorrido subir → indexar → buscar → ver la traza, **sin HTTP** | **Operativo** (composición + worker + `explain`) |
| Casos de uso (SPEC §11) | **15 de 25** |
| Pruebas obligatorias (SPEC §14) | **14 de 14 con test**, ejecutadas contra los dobles en memoria **y contra SQLite** |
| Puertos (SPEC §8) | 13 definidos; **12 con implementación real**. `Embedder` sin implementar (los presets usan `none`) |
| Adaptadores que piden los presets | **8 de 8** disponibles; `check --strict` pasa |
| Worker | **Hecho**: `python -m glosa_app worker`, con paro ordenado y servicio en el compose |
| Endpoints de la API (SPEC §13) | **0 de 24** (3 descritos en el OpenAPI) |
| Servidor MCP | **0 de 3** herramientas |
| Paquetes sin código | `retrieval` (pospuesto a propósito, ADR 0034) |
| Frontend | No iniciado |

## 1. Core (fase 1) — casi cerrada

### Hecho
- [x] Entidades, puertos, autorización por roles y scopes, tokens, encadenado de hashes
- [x] `CreateCollection`, `IssueToken`, `RevokeToken`
- [x] `SubmitDocument`, `SearchCollection`, `ReadDocument`, `ListDocuments`
- [x] `HandleIngest` (ingest y modify) y `ProcessNextJob`
- [x] `GetJob`, `ListJobs`, `CancelJob`, `QueryOperations`, `VerifyOperationLog`, `ViewTrace`
- [x] Las 14 pruebas obligatorias, con alcance completo sobre lo implementado
- [x] `UnitOfWork`, escrituras relacionadas atómicas y tests contra adaptadores reales
- [x] Actor y canal `system` (sin permisos) para el registro del arranque

### Casos de uso que faltan (10)
- [ ] `DeleteDocument` y `HandleDelete`
- [ ] `ReindexDocument` y `HandleReindex`
- [ ] `GetDocumentHistory`
- [ ] `RetryDeadJob`
- [ ] `ManageMembers`
- [ ] `ListCollections`, `UpdateCollectionSettings` y `DeleteCollection` (la API los necesita)

### Otras tareas del núcleo
- [ ] Ampliar las pruebas 1, 4 y 6 a medida que aparezcan los casos de uso que faltan
- [ ] Regla 6 de SPEC §18.4: los ajustes por colección no pueden debilitar la plantilla activa (va con `UpdateCollectionSettings`)
- [ ] `max_attempts` de los trabajos y plazo del lease: hoy el lease sale del entorno y `max_attempts` es fijo; decidir si van en la plantilla
- [ ] Respetar el ajuste `hash_chain` por colección en el registro
- [ ] Purga por retención (`retention_days`, `version_retention`)
- [ ] Renovar el lease (`heartbeat`) mientras un manejador trabaja
- [ ] Limitación de peticiones por token y usuario
- [ ] Al borrar una colección, registrar el hecho en la cadena global (el registro de la propia colección se borra con ella)

## 2. Adaptadores y paquetes (fase 2) — cerrada, salvo mejoras

### Hecho
- [x] `ingest`: extractores de texto y Markdown, chunker por encabezados, registro por entry point
- [x] `storage`: SQLite completo, con atomicidad, concurrencia y persistencia probadas
- [x] `explain`: `build_trace` con descripciones en lenguaje llano y concordancia correcta
- [x] `Database.close()` cierra las conexiones de todos los hilos y descarta las de los hilos que terminan

### Mejoras pendientes
- [ ] `ingest`: codificaciones que no sean UTF-8 (hoy falla con un mensaje claro)
- [ ] `ingest`: encabezados Markdown subrayados (`===` y `---`)
- [ ] `ingest`: tablas y listas como unidades propias en lugar de párrafos
- [ ] `ingest`: solapamiento opcional entre fragmentos contiguos
- [ ] `storage`: `verify_chain` carga el registro entero en memoria; hacerlo por bloques
- [ ] `storage`: copia de seguridad y exportación de la base de datos
- [ ] `explain`: los títulos son texto fijo en español; si se internacionaliza habrá que sacarlos

## 3. Puntos de entrada (fase 3)

### Hecho
- [x] `app`: composición desde la plantilla (guardia de producción, comprobación de adaptadores, política → configuración, huella en el registro de arranque)
- [x] `worker`: bucle con paro ordenado por señales, espera creciente ante fallos de infraestructura y modo `--once`

### Pendiente
- [ ] `http-api`: elegir framework, los 24 endpoints, errores uniformes, `Idempotency-Key`, `X-Correlation-Id`, `429` de capacidad, paginación, CORS y OpenAPI completo
- [ ] `mcp-server`: `buscar`, `leer_documento` y `listar_documentos`, con autenticación por token
- [ ] `app`: datos de demostración para el preset `didactico` (`demo.seed_data` existe, pero no hay datos)

## 4. Transversal

- [ ] Script `eval` con `recall@k` y sus conjuntos de preguntas. **Hoy faltan** `backend/examples/eval.yaml` y `backend/examples/acme-legal/eval.yaml`, que las plantillas ya referencian
- [ ] Integración continua (tests en memoria y contra SQLite, test de arquitectura, revisión de licencias de dependencias)
- [ ] Construir y probar de verdad la imagen Docker (el `Dockerfile` y el servicio `worker` solo se han comprobado reproduciendo sus pasos fuera de Docker)
- [ ] Activar `api` y `mcp` en el compose cuando existan

## 5. Frontend

- [ ] Elegir framework
- [ ] Cliente generado desde `docs/openapi.yaml`
- [ ] Las 9 funciones didácticas de SPEC §15 (la traza ya existe en el backend)

## 6. Documentación y legal

- [ ] Completar los 34 ADRs: todos están como "Propuesta" con las secciones vacías
- [ ] Diagramas: solo existe el de arquitectura general
- [ ] `LICENSE`: titular legal y texto oficial de PolyForm Small Business
- [ ] `LICENSE-COMERCIAL.md`: tramos y precios; revisión legal de la licencia y del CLA
- [ ] Marca **Glosa** (OEPM), dominios y usuario de GitHub; enlaces de apoyo

## 7. Más adelante (hoja de ruta)

- [ ] `retrieval`: estrategias de búsqueda, cuando haya más de una (ADR 0034)
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

Decididas: el contenido de los archivos vive en SQLite (ADR 0027); `retrieval` se pospone (ADR 0034).

## Deuda técnica conocida

- El índice en memoria puntúa de forma muy simple: sirve para probar la mecánica. El de SQLite usa `bm25`, pero no se ha evaluado con un conjunto de preguntas real
- `Job.priority` existe pero ningún caso de uso lo asigna
- `UuidIds` usa 12 caracteres hexadecimales (48 bits): suficiente para demo, a revisar para producción
- No hay forma de ver la historia completa de un **documento**: cada operación tiene su propio `correlation_id`. Falta una consulta del registro por `target.document_id`
- Una versión cancelada o fallida queda en el historial sin haberse indexado nunca. Es coherente con que las versiones son inmutables, pero hay que mostrarlo bien en `GetDocumentHistory`
- El chunker descarta las secciones que solo tienen encabezado; su título solo sobrevive en la ruta de las secciones hijas
- SQLite admite un solo escritor a la vez. Basta para esta fase; Postgres está en la hoja de ruta
- Las transacciones anidadas se unen a la exterior: si una operación interior falla y el código exterior captura el error y sigue, lo que escribió la interior no se deshace. Hoy ningún caso de uso lo hace
- Un trabajo con el lease vencido y un ack tardío del worker antiguo: el ack se ignora si el trabajo ya no está `running`, pero no hay identificador de worker que distinga a dos workers sobre el mismo trabajo
- El worker no renueva el lease mientras trabaja: con 300 s por defecto cubre trabajos normales, pero un documento enorme podría pasarse y otro worker lo recogería a medias (la ingesta es idempotente, así que no corrompe nada, pero se haría dos veces)
- `worker --once` no espera a los trabajos que están en espera de un reintento: termina y esos quedan para la siguiente vuelta
- `ViewTrace` devuelve como máximo 1000 entradas

## Registro de avances

- **2026-11-07:** `app` compone el sistema desde la plantilla; worker como proceso (`glosa_app worker`); `ViewTrace` y `explain`; `Database.close()` cierra todas las conexiones; arranque registrado con la huella de la plantilla. El recorrido subir → indexar → buscar → traza funciona sin HTTP. Spec v0.4.5. Detectado y corregido un nombre de test duplicado, con una comprobación automática.
- **2026-11-06:** adaptadores de `storage` sobre SQLite y puerto `UnitOfWork`; escrituras relacionadas atómicas. La batería de `core` pasa también contra SQLite. Spec v0.4.4.
- **2026-11-04:** `GetJob`, `ListJobs`, `CancelJob`, `QueryOperations` y `VerifyOperationLog`; adaptadores de `ingest`. Corregido un fallo de `SubmitDocument` con contenido ya cancelado. Spec v0.4.3.
- **2026-11-03:** núcleo ampliado con los puertos que faltaban, 9 casos de uso, dobles en memoria, contrato de la cola y las 14 pruebas obligatorias. Spec v0.4.2. Proyecto renombrado a Glosa; `Dockerfile`, `docker-compose.yml` y orden `check`.
- **2026-11-02:** plantillas de cliente, guardia de producción y modelo de licencia (spec v0.4).
