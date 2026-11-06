# glosa-storage

Adaptadores de persistencia sobre SQLite.

## Qué hace

Implementa los puertos de almacenamiento de `glosa-core` sobre **una sola base de datos** (`glosa.db`):

| Adaptador | Puerto |
|-----------|--------|
| `SqliteCollectionRepository` | `CollectionRepository` |
| `SqliteAccessRepository` | `AccessRepository` (miembros y tokens) |
| `SqliteDocumentRepository` | `DocumentRepository` (con el contenido de cada versión) |
| `SqliteChunkIndex` | `ChunkIndex` (búsqueda de texto completo FTS5) |
| `SqliteJobQueue` | `JobQueue` |
| `SqliteOperationLog` | `OperationLog` (con la cadena de hashes) |
| `Database` | `UnitOfWork` (transacciones) |

## Por qué existe como pieza separada

Es el único sitio donde vive SQLite; el dominio no lo conoce. Cambiar a Postgres es escribir otro paquete que cumpla los mismos puertos y las mismas pruebas.

## Qué garantiza

- **Atomicidad:** lo que se escribe dentro de `with db.transaction():` se confirma junto o no se confirma. Se prueba inyectando fallos a mitad de la operación.
- **Aislamiento por colección en el propio SQL:** ninguna consulta se apoya en que la aplicación filtre después.
- **Cola segura entre procesos:** dos workers nunca reciben el mismo trabajo; los trabajos de un mismo documento van en orden; un worker caído no pierde su trabajo; una clave de idempotencia no se puede duplicar ni con peticiones simultáneas.
- **Registro a prueba de manipulación:** cadena de hashes sellada de forma atómica; alterar o borrar una entrada se detecta.
- **Búsqueda sin tildes ni mayúsculas**, y consultas del usuario que nunca se interpretan como sintaxis de FTS5.
- **Migraciones numeradas:** el esquema solo cambia añadiendo una migración al final.

## Cómo se usa suelto

```python
from glosa_storage import SqliteStorage, SqliteChunkIndex, SqliteJobQueue

storage = SqliteStorage("glosa.db")          # colecciones, accesos, documentos, registro, uow
index = SqliteChunkIndex(storage.db)         # el índice y la cola comparten la misma base
queue = SqliteJobQueue(storage.db, clock)

with storage.uow.transaction():
    storage.documents.add(doc, version, contenido)
    queue.enqueue(job)                       # o se guardan los dos, o ninguno
```

Dentro de Glosa se registra solo por el entry point `glosa.adapters` y las plantillas lo piden por nombre (`storage: sqlite`, `queue: sqlite`, `index: sqlite-fts5`).

## Cómo se prueba

```bash
pytest packages/storage/tests                                                  # tests propios
GLOSA_TEST_ADAPTERS=glosa_storage.testing:make_adapters pytest packages/core/tests   # toda la batería de core, contra SQLite
```

## Qué se puede cambiar

Un adaptador distinto (Postgres y pgvector, otra cola) que pase las mismas pruebas de contrato (`glosa_core.queue_contract`) y la batería de `core`.

## Estado

Implementado y probado. Pendiente: cerrar las conexiones de todos los hilos, verificar la cadena por bloques, copia de seguridad. Ver `docs/PENDIENTE.md`.
