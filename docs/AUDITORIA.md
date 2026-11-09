# Auditoría de Glosa frente a la visión del ecosistema

> Fecha: 2026-11-08 · Repositorio local en la versión 0.4.5 de la spec · 289 tests (y los 90 de `core` otra vez contra SQLite).
>
> Esta auditoría compara lo que **hay** en el repositorio con la visión de [`ECOSISTEMA.md`](ECOSISTEMA.md). Cada afirmación se ha comprobado contra el código o contra un test; las que no se han podido comprobar se dicen aparte (apartado 3).

## 1. Qué es Glosa y cuál es su responsabilidad

Glosa transforma documentos en conocimiento recuperable y consultable: ingesta, extracción, normalización, chunking, indexación, recuperación, construcción de contexto y exposición por MCP. **No** es un repositorio de memoria ni un sistema de identidad en las colecciones gobernadas por otro sistema. Reparto completo de autoridad con ATLAS en [`ECOSISTEMA.md`](ECOSISTEMA.md).

## 2. Arquitectura real encontrada

Arquitectura hexagonal, en un monorepo de paquetes. Las reglas de dependencia las comprueba un test (`tests/test_architecture.py`).

| Pieza | Papel | Estado |
|---|---|---|
| `core` | Dominio, permisos, puertos y casos de uso. No importa nada fuera de la librería estándar | 15 de 25 casos de uso |
| `ingest` | Extractores de texto y Markdown; chunker por encabezados | Implementado |
| `storage` | SQLite: documentos, FTS5, cola, registro, colecciones, accesos, transacciones | Implementado |
| `explain` | Trazas legibles | Implementado |
| `templates` | Plantillas YAML con herencia y guardia de producción | Implementado |
| `app` | Composición y órdenes `check` y `worker` | Implementado |
| `worker` | Bucle del proceso | Implementado |
| `retrieval` | Estrategias de búsqueda | Sin código, a propósito (ADR 0034) |
| `http-api`, `mcp-server` | Entradas HTTP y MCP | Sin código |
| Frontend | Cliente de la API | No iniciado |

Lo que **sí** funciona de extremo a extremo, sin HTTP: crear una colección, subir un documento, que el worker lo indexe, buscarlo y ver su traza (`app/tests/test_end_to_end.py`).

## 3. Estado de la Issue #1

**No verificable desde este entorno.** No se ha podido consultar su contenido, criterios de aceptación, comentarios ni evidencias, así que **no se da por cerrada ni por incumplida**.

Para contrastarla:

1. Aportar el texto de la issue (criterios y comentarios).
2. Convertir cada criterio en una fila con su evidencia (test o fichero) y una clasificación del apartado 4.
3. Solo entonces cerrarla, y solo si cada criterio tiene evidencia.

Lo mismo vale para las issues de ATLAS #50, #52, #53 y #67 (ver [`INTEGRACION-ATLAS.md`](INTEGRACION-ATLAS.md), apartado 1).

## 4. Capacidades

Clasificación: **Implementada y probada**, **Implementada parcialmente**, **Implementada, pero sin pruebas suficientes**, **Diseñada, pero no implementada**, **No contemplada** y **Bloqueada por dependencia externa**. La documentación no cuenta como implementación, ni una interfaz o puerto vacío como una función operativa, ni un test unitario como una prueba de funcionamiento real.

| Clasificación | Capacidades |
|---|---:|
| Implementada y probada | 17 |
| Implementada parcialmente | 8 |
| Implementada, pero sin pruebas suficientes | 2 |
| Diseñada, pero no implementada | 7 |
| No contemplada | 7 |
| Bloqueada por dependencia externa | 1 |
| **Total** | **42** |

### Núcleo
| Capacidad | Clasificación | Evidencia | Brecha frente a la visión |
|---|---|---|---|
| Autorización por roles y scopes | **Implementada y probada** | `core/tests/test_authorization.py`, pruebas obligatorias 1–6 en `test_usecases*.py`; también contra SQLite | Solo autoridad local (A-01). Sin autorización externa |
| Tokens: emisión, hash, caducidad, revocación | **Implementada y probada** | `test_tokens.py`, `test_usecases.py` | Sin listado ni rotación (S-08) |
| Registro de operaciones con cadena de hashes | **Implementada y probada** | `test_chain.py`, `storage/tests/test_operation_log.py` | No detecta el truncado final (A-10); sin exportación hacia ATLAS (C7) |
| Trazas legibles de una operación | **Implementada y probada** | `explain/tests/test_build_trace.py`, `test_view_trace.py` | — |
| Cola de trabajos: idempotencia, orden, lease, reintentos, `dead` | **Implementada y probada** | `test_queue_contract.py`, `storage/tests/test_queue.py` (con concurrencia) | — |
| Atomicidad de las escrituras relacionadas | **Implementada y probada** | `storage/tests/test_atomicity.py` (con fallos inyectados) | — |
| Idempotencia y recuperación ante un worker caído | **Implementada y probada** | `test_usecases.py` (pruebas 7, 8 y 10), `storage/tests/test_persistence.py` | — |
| Límites por colección (tamaño, documentos, cola) | **Implementada y probada** | `test_usecases.py::test_limites_de_la_coleccion` | Sin límites de tiempo (A-07) |
| Plantillas: herencia, esquema y guardia de producción | **Implementada y probada** | `templates/tests/test_templates.py` | Algunos campos no tienen efecto (A-05) |
| Composición y arranque desde la plantilla | **Implementada y probada** | `app/tests/test_composition.py` | — |
| Versionado inmutable de documentos | **Implementada y probada** | `test_usecases.py`, `storage/tests/test_documents.py` | Las versiones son locales (modo propio) |
| Retención y purga (`retention_days`, `version_retention`) | **Diseñada, pero no implementada** | Ajustes guardados en `CollectionSettings`; nada los aplica | Falta la purga |
| Limitación de peticiones | **Diseñada, pero no implementada** | Spec §14 | No hay (S-05) |

### Pipeline documental
| Capacidad | Clasificación | Evidencia | Brecha frente a la visión |
|---|---|---|---|
| Ingesta: incorporar documentos | **Implementada parcialmente** | `SubmitDocument` (`test_usecases.py`) | Solo subida directa de bytes; sin adaptadores de fuente ni `DocumentSource`; sin procedencia de origen (R7, R8) |
| Extracción de contenido | **Implementada parcialmente** | `ingest/tests/test_extractors.py` | Solo texto y Markdown en UTF-8; sin PDF ni tablas; contenido vacío y no UTF-8 se clasifican como error permanente |
| Normalización | **Implementada parcialmente** | `test_extractors.py` | Saltos de línea, nulos y *front matter*; sin estructura más allá de los encabezados |
| Chunking por estructura (encabezados, párrafos, límite de tamaño) | **Implementada y probada** | `ingest/tests/test_chunker.py` | Una sola estrategia; sin tablas, solapamiento ni ubicación exacta (desplazamientos) en el original |
| Metadatos documentales derivados | **Implementada parcialmente** | `test_chunker.py`, `test_pipeline.py` | Solo ruta de encabezados, nivel y título; `Document.metadata` y los `metadata` de la plantilla no se usan (A-05) |
| Persistencia de representaciones derivadas | **Implementada y probada** | `storage/tests/test_index.py` | No registra con qué extractor y chunker se generaron (A-04) |

### Indexación
| Capacidad | Clasificación | Evidencia | Brecha frente a la visión |
|---|---|---|---|
| Índice léxico (FTS5) | **Implementada y probada** | `storage/tests/test_index.py` | — |
| Embeddings: modelo, proveedor, dimensiones, versión | **Diseñada, pero no implementada** | Existe el puerto `Embedder`; el preset usa `none` | Sin implementación ni modelo de metadatos del índice |
| Índice vectorial | **No contemplada** | — | Sin diseño de índices por modelo, estados de indexación ni reglas para no mezclarlos |
| Reconstrucción de índices | **Implementada parcialmente** | El contenido original y `remove_*` lo permiten (`test_collection_delete.py`) | Falta `ReindexDocument` y los metadatos de generación (A-04) |

### Recuperación
| Capacidad | Clasificación | Evidencia | Brecha frente a la visión |
|---|---|---|---|
| Recuperación léxica con relevancia (bm25) y aislamiento por colección | **Implementada y probada** | `storage/tests/test_index.py`, `core/tests/test_usecases.py::test_1_un_token_de_a_no_toca_nada_de_b` | Sin filtros por metadatos |
| Búsqueda vectorial, híbrida, filtrado y reranking | **Diseñada, pero no implementada** | La plantilla tiene `retrieval.strategy` y `reranker`, sin efecto (A-05) | Sin implementación; el paquete `retrieval` está pospuesto (ADR 0034) |

### RAG
| Capacidad | Clasificación | Evidencia | Brecha frente a la visión |
|---|---|---|---|
| Construcción de contexto con evidencias | **No contemplada** | — | Hoy solo hay recuperación de fragmentos |
| Respuesta fundamentada y reconocimiento de contexto insuficiente | **No contemplada** | — | Depende de la decisión sobre el alcance del RAG (ADR 0039) |

### Interfaces
| Capacidad | Clasificación | Evidencia | Brecha frente a la visión |
|---|---|---|---|
| MCP (`buscar`, `leer_documento`, `listar_documentos`) | **Diseñada, pero no implementada** | Spec §12 | 0 de 3 herramientas; sin contrato versionado |
| API de gestión | **Diseñada, pero no implementada** | `openapi.yaml`: 3 de 24 endpoints descritos | 0 de 24 implementados |
| Interfaz de usuario | **No contemplada** | — | No iniciada |

### Operación
| Capacidad | Clasificación | Evidencia | Brecha frente a la visión |
|---|---|---|---|
| Worker como proceso, con paro ordenado por evento | **Implementada y probada** | `adapters/worker/tests/test_runner.py`, `app/tests/test_composition.py` | — |
| Paro ordenado por señales (SIGTERM, Ctrl+C) | **Implementada, pero sin pruebas suficientes** | Se prueba el paro por evento; no se envía una señal real | Falta una prueba con una señal real |
| Imagen Docker y servicio `worker` del compose | **Implementada, pero sin pruebas suficientes** | Solo se han reproducido sus pasos fuera de Docker | Nunca se ha construido con Docker |
| Observabilidad: estado real de los componentes | **Implementada parcialmente** | Registro de operaciones y trazas | Sin *health*, *readiness* ni métricas (A-09) |
| Límites de tiempo (*timeouts*) | **No contemplada** | Solo `busy_timeout` de SQLite | Sin límites en extracción, indexado ni búsqueda (A-07) |
| Errores explícitos y clasificables | **Implementada parcialmente** | Jerarquía de excepciones del dominio | Sin catálogo de códigos estables (A-08) |
| Contratos versionados | **Implementada parcialmente** | `/v1` previsto en el OpenAPI | El esquema de plantillas no lleva versión; MCP sin contrato (C9) |
| Pruebas sin servicios externos | **Implementada y probada** | Toda la batería es local (SQLite en memoria o en archivo) | — |

### Ecosistema
| Capacidad | Clasificación | Evidencia | Brecha frente a la visión |
|---|---|---|---|
| Borrado de documentos y *tombstones* | **Diseñada, pero no implementada** | Puerto `mark_deleted`; borrado de colección en cascada en el adaptador | No existe `DeleteDocument` ni *tombstones* (A-13) |
| Modo gobernado: origen externo, contexto autorizado y re-comprobación al consultar | **No contemplada** | Diseño en `ECOSISTEMA.md` | Nada en el código (A-01, A-03) |
| Contratos C1–C5 y C8 con ATLAS | **Bloqueada por dependencia externa** | Matriz en `INTEGRACION-ATLAS.md` | Su forma final depende de lo que ATLAS tenga; no se ha podido consultar |
| Sincronización, cursores y reconciliación | **No contemplada** | Diseño en `INTEGRACION-ATLAS.md` | Nada en el código |

## 5. Problemas arquitectónicos

| | Gravedad | Problema | Qué hacer |
|---|---|---|---|
| **A-01** | Alta | Glosa es hoy la autoridad local de documentos, identidad, permisos y auditoría en **todas** las colecciones. Chocaría con R1–R5 en una colección gobernada | Autoridad por colección, modo propio o gobernado (ADR 0035) |
| **A-02** | Alta | Un trabajo se ejecuta con los permisos que tenía el actor **al encolar**; el worker no vuelve a comprobar nada. Si se revoca entre medias, el trabajo sigue adelante | Volver a autorizar al ejecutar (G-014) |
| **A-03** | Media | `Collection` mezcla inquilino y fuente: no existe la noción de origen | `Collection.origin` y `SourceRef` (G-010, G-051) |
| **A-04** | Media | Los derivados no registran con qué extractor, chunker y versión se generaron: no se puede reconstruir de forma selectiva (R6) | `DerivationInfo` (G-013) |
| **A-05** | Media | **La plantilla promete más de lo que hace.** `metadata`, `retrieval.reranker` y `adapters.embedder` no tienen efecto, y `retrieval.strategy` solo es una etiqueta que no cambia el comportamiento. Una configuración engañosa es un riesgo | Implementarlos o marcarlos como reservados hasta que existan (G-011, G-023) |
| **A-06** | Baja | Campo sin uso: `DocumentVersion.content_ref` | Eliminarlo o usarlo (G-013) |
| **A-07** | Media | Sin límites de tiempo en extracción, indexado ni búsqueda. El *lease* no interrumpe un manejador colgado | Timeouts configurables y errores clasificados (G-015) |
| **A-08** | Media | Sin catálogo de errores con códigos estables: la API y el MCP tendrán que inventarlos | Catálogo (G-016) |
| **A-09** | Media | Sin *health*, *readiness* ni métricas | G-019 |
| **A-10** | Media | La cadena de hashes no detecta que se borren las últimas entradas. Importa porque ese registro será una evidencia para ATLAS | Anclaje externo (decisión pendiente) |
| **A-11** | Baja | `verify_chain` carga el registro entero en memoria | Hacerlo por bloques |
| **A-12** | Media | El resultado de búsqueda no incluye limitaciones ni información de recuperación suficiente (C6) | G-030 |
| **A-13** | Alta | No existe borrado de documentos ni *tombstones* | `DeleteDocument` (G-012) |
| **A-14** | Media | Guardar el contenido original en SQLite (ADR 0027) es propio del modo propio. En el gobernado sería una copia que hay que poder retirar | G-051 |
| **A-15** | Baja | `source_type` es texto libre y decide el extractor; nada comprueba que el contenido corresponda al tipo declarado | Detección o validación (G-017) |
| **A-16** | Media | La regla 6 de la spec (los ajustes por colección no pueden debilitar la plantilla) no está implementada: un futuro `UpdateCollectionSettings` podría hacerlo | Implementarla junto a ese caso de uso |

**Lo que está bien:** el dominio no depende de frameworks y un test lo impone; los proveedores están detrás de puertos; la configuración es validable; las escrituras relacionadas son atómicas; la idempotencia, la concurrencia y la recuperación ante caídas están probadas con adaptadores reales; los dobles están identificados como tales y la misma batería se ejecuta contra los adaptadores reales.

**Lo que conviene simplificar:** los campos de plantilla sin efecto (A-05) y el campo `content_ref` (A-06). El paquete `retrieval` sin código es una decisión deliberada, no una carencia.

## 6. Riesgos de seguridad y autorización

| | Gravedad | Riesgo |
|---|---|---|
| **S-01** | Alta | Revocación: ver A-02. Además `ManageMembers` no existe, así que un rol no se puede retirar por caso de uso (solo por el adaptador) |
| **S-02** | Alta (modo gobernado) | Un índice derivado seguiría sirviendo lo revocado o borrado: no hay re-comprobación al consultar ni propagación de cambios. El diseño está en `INTEGRACION-ATLAS.md`, apartado 5.6 |
| **S-03** | Alta (modo gobernado) | No existe identidad ni autenticación entre sistemas |
| **S-04** | Media | Inyección de instrucciones en los documentos que se devuelven a un agente. Mitigación prevista (MCP de solo lectura, contenido como dato); **no verificable** porque el MCP no existe |
| **S-05** | Media | Sin limitación de peticiones |
| **S-06** | Media | Sin límites de tiempo: un documento patológico puede bloquear a un worker |
| **S-07** | Media | El contenido original y los fragmentos están **en claro** en la base SQLite, sin cifrado en reposo. En modo gobernado serían copias de contenido autorizado |
| **S-08** | Media | `query_logging: full` es el valor del preset didáctico y guarda las consultas en claro; la guardia de producción lo impide en producción |
| **S-09** | Baja | Los tokens no se pueden listar ni rotar |
| **S-10** | Baja | Los identificadores aleatorios usan 48 bits |

Mitigaciones que **ya existen y están probadas**: aislamiento por colección en el propio SQL (prueba obligatoria 1, también contra SQLite), tokens guardados con hash, revocación inmediata de tokens, caducidad, denegaciones siempre registradas, registro con cadena de hashes, guardia de producción y ausencia de secretos en las plantillas.

## 7. Diferencias respecto a la visión

| Apartado de la visión | Situación |
|---|---|
| Separación de autoridad con ATLAS (R1–R5, R9) | Solo existe el modo propio. Falta el modo gobernado (A-01) |
| Índices derivados y reconstruibles (R6) | Parcial: se puede reconstruir desde el contenido propio, sin caso de uso ni metadatos de generación (A-04) |
| Procedencia (R7, R8) | Parcial: cada fragmento lleva documento y versión **locales**; falta el origen (`SourceRef`) |
| Funcionar sin ATLAS (R10) | **Cumplido**: Glosa no depende de ATLAS en ningún punto |
| 5.1 Ingesta desde distintas fuentes | Parcial: solo subida directa |
| 5.2 Extracción y normalización | Parcial: texto y Markdown |
| 5.3 Chunking por estructura | **Cumplido** para Markdown y texto: encabezados, párrafos y tamaño; faltan tablas, solapamiento y ubicación exacta |
| 5.4 Embeddings e indexación | Solo índice léxico; el modelo de índices vectoriales no existe |
| 5.5 Recuperación | Léxica; sin filtros, híbrida ni reranking |
| 5.6 RAG trazable | No existe: solo recuperación |
| 5.7 MCP | No existe |
| 4. Operaciones con límites y *timeouts* | Límites de tamaño sí; de tiempo no |
| 4. Errores explícitos y clasificables | Parcial: sin códigos estables |
| 4. Contratos versionados | Parcial |
| 4. Observabilidad del estado real | Parcial: registro y trazas, sin *health* ni métricas |
| 4. Tests sin servicios externos | **Cumplido** |

## 8. Contratos con ATLAS y dependencias reales

Los diez contratos que Glosa necesita están en [`INTEGRACION-ATLAS.md`](INTEGRACION-ATLAS.md), apartado 2. **Dependencias reales de Glosa respecto a ATLAS hoy: ninguna.** Todo el trabajo hacia ATLAS está bloqueado por la verificación de sus contratos, y no se ha supuesto ninguno.

## 9. Qué puede hacerse ya sin ATLAS

Casi todo el trabajo previo a la integración (procedencia, borrado, revalidación de permisos, límites de tiempo, errores, observabilidad, extractores, embeddings, recuperación, RAG y MCP) no depende de ATLAS. Está ordenado en [`HOJA-DE-RUTA.md`](HOJA-DE-RUTA.md).
