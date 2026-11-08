# Glosa — Especificación v0.4.5

> Estado: borrador · Idioma: español · Formato: Markdown versionado
>
> **Cambios respecto a v0.3:** se añade un **sistema de plantillas** para adaptar el sistema a cualquier cliente o proyecto sin tocar código, y un **modelo de licencia y comercial** (código disponible: gratis para personas y pequeñas empresas, de pago para las demás). Ver [§21 Registro de cambios](#21-registro-de-cambios).
>
> **v0.4.1:** el proyecto se llama **Glosa** (la glosa es la anotación que explica un texto, que es lo que hace la capa didáctica). Se añaden `Dockerfile`, `docker-compose.yml` y la orden `check` para validar la plantilla activa (§17).
>
> **v0.4.2:** se completan los puertos que faltaban (identificadores, colecciones, miembros) y se implementan los primeros casos de uso en `core`, con las 14 pruebas obligatorias de §14. Ver el estado real en [`PENDIENTE.md`](PENDIENTE.md).
>
> **v0.4.3:** se completan las consultas de trabajos y del registro de operaciones (`GetJob`, `ListJobs`, `CancelJob`, `QueryOperations`, `VerifyOperationLog`) y se implementan los adaptadores de `ingest`: extractores de texto y Markdown y chunker por encabezados (§8).
>
> **v0.4.4:** se implementan los adaptadores de `storage` sobre SQLite (documentos, índice FTS5, cola, registro de operaciones, colecciones y accesos), con el puerto `UnitOfWork` para que las escrituras relacionadas se confirmen juntas (§8).
>
> **v0.4.5:** se cierra el recorrido subir → indexar → buscar → ver la traza sin HTTP: composición del sistema desde la plantilla (`build_app`), worker como proceso (`glosa_app worker`), caso de uso `ViewTrace` y el paquete `explain` (§15, §17). `Database.close()` cierra ya las conexiones de todos los hilos.

## 1. Objetivo

Un backend en el que cualquier persona sube sus documentos y obtiene:

- Un **RAG** consultable (búsqueda y contexto para un modelo).
- Un **servidor MCP** propio al que los LLM se conectan directamente, con su gestión de permisos.

Requisitos transversales:

- **Encolado:** las peticiones que modifican datos se encolan y se procesan de forma ordenada y controlada.
- **Trazabilidad:** cada subida, indexación, consulta, modificación y borrado deja constancia verificable de quién lo hizo, cuándo, sobre qué y con qué resultado.
- **Didáctico:** quien lo use debe entender cómo funcionan RAG y MCP viéndolos funcionar.
- **Reutilizable:** el backend puede usarse con otro frontend, o sin ninguno, y cada paquete interno puede usarse suelto.
- **Adaptable:** la adaptación a un cliente o proyecto se hace con una plantilla, no con código (ver [§18](#18-plantillas-y-adaptación-a-clientes)).
- **Didáctico y comercial:** el mismo núcleo sirve para aprender y para ofrecer un servicio profesional; lo que cambia es la plantilla y la licencia (ver [§19](#19-licencia-y-modelo-comercial)).

### No objetivos de la v0.3

- No es un servicio comercial (sin facturación ni escalado horizontal).
- No pretende máxima calidad de recuperación, sino claridad y buen diseño.
- No soporta todos los formatos: solo `.md` y `.txt` en la primera versión.
- El frontend no es parte del contrato: es un ejemplo de cliente.

## 2. Principios de diseño

1. **El backend es el producto.** Toda la lógica y todos los permisos viven ahí.
2. **El frontend es un cliente más.** Solo consume la API pública.
3. **Dominio aislado.** La lógica de negocio no conoce bases de datos, frameworks ni protocolos.
4. **Puertos y adaptadores.** Todo lo externo se conecta mediante interfaces definidas en el núcleo.
5. **Dependencias en una sola dirección.** Los paquetes exteriores dependen de `core`; `core` no depende de nadie.
6. **Una sola autorización para todas las puertas.** API y MCP pasan por el mismo servicio de permisos.
7. **Capas finas en los bordes.** API, MCP y worker solo traducen entradas a casos de uso.
8. **Toda operación se registra.** Una única fuente de verdad: el registro de operaciones.
9. **Las escrituras son asíncronas e idempotentes.** Pasan por la cola y toleran reintentos.
10. **Observable sin acoplarse.** La capa didáctica lee del registro; quitarla no rompe nada.
11. **Un adaptador por puerto al inicio, interfaces completas desde el principio.**
12. **Documentar primero.** Cada decisión relevante tiene su ADR.
13. **La personalización vive en plantillas, no en el código.** Una plantilla elige piezas y ajustes seguros; nunca puede desactivar un invariante.

## 3. Visión general

```
                    ┌──────────────────────────── BACKEND ────────────────────────────┐
 Frontend ─ HTTP ─► │  http-api ──┐                                                    │
 (cliente de la API)│             ├─► autorización ─► casos de uso ─► puertos          │
 LLM / cliente MCP ►│  mcp-server ┘        │               │                          │
                    │                      │               ├─ lecturas: síncronas     │
                    │                      │               └─ escrituras ─► JobQueue  │
                    │                      │                                  │       │
                    │  worker ◄────────────┼──────────────────────────────────┘       │
                    │    (ingesta, modificación, reindexado, borrado)                  │
                    │                      │                                          │
                    │                      ▼                                          │
                    │            OperationLog (solo se añade)                         │
                    │                      ▲                                          │
                    │  explain ────────────┘ (lee; nadie depende de él)               │
                    └─────────────────────────────────────────────────────────────────┘
```

Hay **tres puntos de entrada** al mismo núcleo:

| Entrada      | Quién la usa                          | Para qué                                           |
|--------------|---------------------------------------|----------------------------------------------------|
| `http-api`   | Frontend, scripts, otras aplicaciones | Gestionar colecciones, documentos, tokens, trabajos y trazas |
| `mcp-server` | LLM y clientes MCP                    | Buscar y leer documentos con permisos acotados      |
| `worker`     | Proceso interno                       | Consumir la cola y ejecutar las escrituras          |

## 4. Estructura del repositorio

```
glosa/
├── LICENSE               # PolyForm Small Business 1.0.0 (uso gratuito para pequeñas empresas)
├── LICENSE-COMERCIAL.md  # licencia comercial para el resto (borrador)
├── CLA.md                # acuerdo de contribución (borrador)
├── CONTRIBUTING.md
├── docs/                 # documentación compartida por backend y frontend
│   ├── SPEC.md
│   ├── openapi.yaml      # contrato público de la API
│   ├── adr/
│   ├── glosario.md
│   ├── licencias-dependencias.md
│   └── diagramas/
├── backend/
│   ├── packages/
│   │   ├── core/         # dominio, permisos, puertos y casos de uso
│   │   ├── ingest/       # extractores y chunkers
│   │   ├── retrieval/    # estrategias de búsqueda
│   │   ├── storage/      # adaptadores: repositorios, índice, cola, registro
│   │   ├── explain/      # lectura didáctica del registro de operaciones
│   │   └── templates/    # plantillas: carga, herencia, validación y registro de adaptadores
│   ├── adapters/
│   │   ├── http-api/     # API de gestión (capa fina)
│   │   ├── mcp-server/   # servidor MCP (capa fina)
│   │   └── worker/       # consumidor de la cola (capa fina)
│   ├── app/              # composición, arranque y orden `check`
│   ├── examples/         # documentos, preguntas de ejemplo y plantilla de cliente de ejemplo
│   ├── Dockerfile        # imagen multietapa: builder, runtime y test
│   ├── .dockerignore
│   ├── docker-compose.yml
│   └── Makefile
└── frontend/
    ├── api-client/       # cliente generado desde docs/openapi.yaml
    ├── src/              # UI de subida y modo "ver por dentro"
    └── README.md
```

Cada paquete de `backend/packages/` tiene su propio `README.md`, `pyproject.toml` y `tests/`, y puede instalarse y usarse de forma independiente.

## 5. Reglas de dependencia

| Componente     | Puede depender de      | No puede depender de                              |
|----------------|------------------------|---------------------------------------------------|
| `core`         | solo librería estándar | cualquier otro paquete                            |
| `ingest`       | `core`                 | `storage`, `retrieval`, adaptadores               |
| `retrieval`    | `core`                 | `ingest`, adaptadores                             |
| `storage`      | `core`                 | `ingest`, `retrieval`, adaptadores                |
| `explain`      | `core`                 | todo lo demás                                     |
| `templates`    | `core`                 | todo lo demás                                     |
| `http-api`     | `core`                 | `storage` directamente, `mcp-server`, `worker`    |
| `mcp-server`   | `core`                 | `storage` directamente, `http-api`, `worker`      |
| `worker`       | `core`                 | `storage` directamente, `http-api`, `mcp-server`  |
| `app`          | todos (composición)    | —                                                 |
| `frontend`     | solo la API pública    | cualquier código del backend                      |

La **composición** (inyectar adaptadores concretos en los casos de uso) ocurre únicamente en `backend/app/`.

## 6. Modelo de dominio (`core`)

| Entidad            | Campos principales                                                                       |
|--------------------|------------------------------------------------------------------------------------------|
| `User`             | `id`, `email`, `created_at`                                                              |
| `Collection`       | `id`, `name`, `settings` (`CollectionSettings`), `created_at`                            |
| `Membership`       | `user_id`, `collection_id`, `role` (`owner` / `editor` / `reader`)                       |
| `Document`         | `id`, `collection_id`, `title`, `source_type`, `current_version`, `status`, `metadata`   |
| `DocumentVersion`  | `document_id`, `version`, `content_hash`, `size`, `created_by`, `created_at`, `content_ref` |
| `Chunk`            | `id`, `document_id`, `version`, `collection_id`, `text`, `position`, `metadata`          |
| `SearchHit`        | `chunk`, `score`, `strategy` (`text` / `vector` / `hybrid`)                              |
| `AccessToken`      | `id`, `collection_id`, `created_by`, `hash`, `scopes`, `expires_at`, `revoked`           |
| `CollectionSettings` | `query_logging`, `retention_days`, `version_retention`, `version_keep`, `hash_chain`, `max_file_mb`, `max_documents`, `max_queue_per_collection` |
| `Job`              | ver [§9](#9-cola-de-trabajos)                                                            |
| `OperationEntry`   | ver [§10](#10-registro-de-operaciones-y-trazabilidad)                                    |

Estados de `Document`: `pending` → `processing` → `ready` | `failed`.

**Invariantes clave:**

- Todo `Chunk`, `Document` y `Job` lleva `collection_id`. Ninguna consulta se ejecuta sin él.
- Los fragmentos indexados pertenecen a una **versión** concreta. Solo se buscan los de la versión vigente.
- Una versión nunca se modifica: un cambio crea una versión nueva.

## 7. Autorización

El servicio de autorización vive en `core` y es la **única** pieza que decide permisos. `http-api` y `mcp-server` lo llaman antes de ejecutar cualquier caso de uso. El `worker` ejecuta trabajos ya autorizados al encolarlos, pero conserva el `actor` original para el registro.

### 7.1 Actores

- **Usuario** (acceso por API, normalmente desde el frontend): su permiso depende de su `role` en la colección.
- **Token** (acceso por MCP u otras integraciones): su permiso depende de sus `scopes` y siempre está atado a una única colección.
- **Sistema** (el arranque y las tareas internas): deja constancia en el registro, pero **no tiene ningún permiso** sobre ninguna colección.

### 7.2 Roles de usuario

| Acción                                    | `reader` | `editor` | `owner` |
|-------------------------------------------|:--------:|:--------:|:-------:|
| Buscar y leer documentos                  |    ✔     |    ✔     |    ✔    |
| Subir, modificar y borrar documentos      |          |    ✔     |    ✔    |
| Ver estado de trabajos propios            |          |    ✔     |    ✔    |
| Ver historial de documentos y trazas      |          |    ✔     |    ✔    |
| Emitir y revocar tokens                   |          |          |    ✔    |
| Ver registro de operaciones completo y auditoría |   |          |    ✔    |
| Gestionar miembros, ajustes y borrar la colección |  |          |    ✔    |

### 7.3 Scopes de token

| Scope     | Permite                                                 |
|-----------|---------------------------------------------------------|
| `read`    | `buscar`, `leer_documento`, `listar_documentos`         |
| `write`   | Además, subir, modificar y borrar documentos (encolando) |

Reglas:

- Por defecto un token se emite solo con `read`. `write` hay que pedirlo explícitamente.
- Un token **no puede tener más permisos que quien lo emitió** en esa colección.
- Los tokens pueden caducar y revocarse en cualquier momento; la revocación es inmediata.
- El token fija la colección: el cliente MCP nunca elige sobre qué datos opera.

### 7.4 Tokens: almacenamiento

- Se guardan **hasheados**; el valor en claro solo se muestra al crearlos.
- Formato con prefijo reconocible (por ejemplo `glosa_...`) para detectarlos si se filtran por error.

### 7.5 Autenticación

| Fase       | Usuarios (API)                        | LLM / clientes MCP                                     |
|------------|---------------------------------------|--------------------------------------------------------|
| **v0.x**   | Sesión simple o API key personal      | Token de colección en cabecera `Authorization: Bearer` |
| **Futura** | Proveedor de identidad externo (OIDC) | OAuth 2.1, que es lo que contempla MCP para HTTP remoto |

La autenticación se define como puerto (`Authenticator`): cambiar el mecanismo no afecta al resto.

## 8. Puertos (interfaces)

Definidos en `core/ports/` (`ports.py`). Ejemplo en Python con `Protocol`:

```python
class TextExtractor(Protocol):
    def supports(self, source_type: str) -> bool: ...
    def extract(self, raw: bytes) -> str: ...

class Chunker(Protocol):
    def split(self, text: str) -> list[ChunkDraft]: ...

class CollectionRepository(Protocol):
    def add(self, collection: Collection) -> None: ...
    def get(self, collection_id: str) -> Collection | None: ...
    def delete(self, collection_id: str) -> None: ...
    def update_settings(self, collection_id: str, settings: CollectionSettings) -> None: ...

class DocumentRepository(Protocol):
    def add(self, doc: Document, version: DocumentVersion, content: bytes) -> None: ...
    def add_version(self, collection_id: str, doc_id: str, version: DocumentVersion, content: bytes) -> None: ...
    def get(self, collection_id: str, doc_id: str) -> Document | None: ...
    def get_content(self, collection_id: str, doc_id: str, version: int | None) -> bytes | None: ...
    def history(self, collection_id: str, doc_id: str) -> list[DocumentVersion]: ...
    def list(self, collection_id: str) -> list[Document]: ...          # sin los borrados
    def update_status(self, collection_id: str, doc_id: str, status: DocumentStatus,
                      current_version: int | None = None) -> None: ...
    def mark_deleted(self, collection_id: str, doc_id: str, at: datetime) -> None: ...

class ChunkIndex(Protocol):
    def index(self, chunks: list[Chunk]) -> None: ...
    def search(self, collection_id: str, query: str, limit: int) -> list[SearchHit]: ...
    def remove_version(self, collection_id: str, doc_id: str, version: int) -> None: ...
    def remove_document(self, collection_id: str, doc_id: str) -> None: ...

class JobQueue(Protocol):
    def enqueue(self, job: Job) -> Job: ...                      # respeta idempotency_key
    def find_by_key(self, collection_id: str, key: str) -> Job | None: ...
    def claim(self, worker_id: str, lease_seconds: int) -> Job | None: ...
    def heartbeat(self, job_id: str, worker_id: str) -> None: ...
    def ack(self, job_id: str, result: JobResult) -> None: ...
    def fail(self, job_id: str, error: str, retry_at: datetime | None) -> None: ...
    def cancel(self, collection_id: str, job_id: str) -> bool: ...
    def get(self, collection_id: str, job_id: str) -> Job | None: ...
    def list(self, collection_id: str, status: str | None, limit: int) -> list[Job]: ...

class OperationLog(Protocol):                                     # solo añadir
    def record(self, entry: OperationEntry) -> None: ...         # sella la entrada (hash) al guardarla
    def query(self, collection_id: str, filters: OperationFilter, limit: int) -> list[OperationEntry]: ...
    def verify_chain(self, collection_id: str) -> ChainReport: ...

class AccessRepository(Protocol):                                 # miembros y tokens
    def role_of(self, user_id: str, collection_id: str) -> Role | None: ...
    def add_member(self, user_id: str, collection_id: str, role: Role) -> None: ...
    def remove_member(self, user_id: str, collection_id: str) -> None: ...
    def members(self, collection_id: str) -> list[Membership]: ...
    def collections_of(self, user_id: str) -> list[str]: ...
    def find_token(self, token_hash: str) -> AccessToken | None: ...
    def get_token(self, collection_id: str, token_id: str) -> AccessToken | None: ...
    def list_tokens(self, collection_id: str) -> list[AccessToken]: ...
    def save_token(self, token: AccessToken) -> None: ...
    def revoke_token(self, token_id: str) -> None: ...

class Authenticator(Protocol):
    def identify(self, credentials: Credentials) -> Actor | None: ...

class Embedder(Protocol):             # opcional en v0.x
    def embed(self, texts: list[str]) -> list[list[float]]: ...

class Clock(Protocol):                # para tests deterministas y marcas de tiempo
    def now(self) -> datetime: ...

class IdGenerator(Protocol):          # identificadores y correlation_id
    def new_id(self, prefix: str) -> str: ...
```

```python
class UnitOfWork(Protocol):           # varias escrituras, una sola transacción
    def transaction(self) -> AbstractContextManager[None]: ...
```

Todo método que toca datos de una colección recibe su `collection_id`.

`UnitOfWork` agrupa las escrituras que deben confirmarse juntas (SPEC §9.4): todo lo de dentro de `with uow.transaction():` se confirma junto o no se confirma, y las transacciones anidadas se unen a la exterior. Lo usan `CreateCollection`, `IssueToken`, `RevokeToken`, `SubmitDocument` (documento, versión, trabajo y registro), `CancelJob`, el indexado de `HandleIngest` y el cierre de cada trabajo en `ProcessNextJob`.

### Adaptadores iniciales

| Puerto               | Adaptador inicial                    | Futuros                              |
|----------------------|--------------------------------------|--------------------------------------|
| `TextExtractor`      | Markdown y texto plano               | PDF, DOCX, OCR                       |
| `Chunker`            | Por encabezados y párrafos           | Por tokens, semántico                |
| `DocumentRepository` | SQLite (el contenido, en la misma base) | Postgres + almacenamiento de objetos |
| `ChunkIndex`         | SQLite FTS5                          | pgvector, híbrido, reranker          |
| `JobQueue`           | Tabla en SQLite                      | Postgres, Redis, broker de mensajes  |
| `OperationLog`       | Tabla en SQLite (solo inserciones)   | Almacén de logs externo              |
| `CollectionRepository` | SQLite                             | Postgres                             |
| `AccessRepository`   | SQLite                               | Postgres                             |
| `Authenticator`      | API key / token estático             | OIDC, OAuth 2.1                      |
| `Embedder`           | — (no incluido)                      | Local o API externa                  |
| `Clock`              | `SystemClock` (en `core`)            | —                                    |
| `IdGenerator`        | `UuidIds` (en `core`)                | —                                    |
| `UnitOfWork`         | `Database` de SQLite (en `storage`)  | Transacciones de Postgres            |

### Adaptadores de `storage` (implementados)

Una sola base de datos SQLite (`glosa.db`) para todo, en modo WAL, con una conexión por hilo. Se registran por nombre con el entry point `glosa.adapters`.

| Nombre (plantilla) | Qué incluye                                                                                   |
|--------------------|-----------------------------------------------------------------------------------------------|
| `sqlite`           | Colecciones, accesos (miembros y tokens), documentos con el contenido de cada versión, registro de operaciones y `UnitOfWork` |
| `sqlite` (cola)    | `JobQueue` (`queue: sqlite`)                                                                  |
| `sqlite-fts5`      | `ChunkIndex` con búsqueda de texto completo (`index: sqlite-fts5`)                            |

Decisiones de diseño:

- **El contenido de los archivos vive en la base de datos** (columna binaria por versión). Subir un documento es atómico con el resto de la transacción y una sola copia de seguridad lo guarda todo. Cambiarlo a disco o a un almacén de objetos es cambiar un adaptador.
- **Transacciones:** `BEGIN IMMEDIATE` toma el bloqueo de escritura desde el principio, así que dos procesos nunca se pisan. Si algo falla dentro, no queda nada a medias.
- **Aislamiento por colección en la consulta:** todo `SELECT`, `UPDATE` y `DELETE` filtra por `collection_id` en el propio SQL, no en la aplicación.
- **Índice de texto:** FTS5 con `unicode61 remove_diacritics 2`, de modo que "rescision" encuentra "rescisión". La consulta del usuario nunca se pasa tal cual: cada palabra va entre comillas (así `AND`, `OR`, `*` o `"` no se interpretan como sintaxis) y se unen con OR; el orden lo da `bm25`, con el signo invertido para que mayor sea mejor.
- **Cola:** `claim` es atómico entre procesos; un trabajo no se entrega mientras haya otro anterior sin terminar sobre el mismo documento (aunque espere un reintento); un lease vencido devuelve el trabajo a la cola; un índice único `(colección, clave de idempotencia)` impide duplicados aunque dos peticiones lleguen a la vez. Solo se puede confirmar (`ack`) o fallar un trabajo que esté en marcha.
- **Registro de operaciones:** leer el último hash y añadir la entrada ocurren en una transacción, así que la cadena no se rompe con escrituras concurrentes. El adaptador no ofrece ninguna operación para editar o borrar entradas. Cada colección tiene su cadena; las entradas sin colección tienen la suya.
- **Migraciones numeradas** (`PRAGMA user_version`): para cambiar el esquema se añade una migración, nunca se modifica una anterior. Una base de una versión más nueva que el programa se rechaza.
- **Borrar una colección** elimina todos sus datos, incluidos sus fragmentos del índice de texto y su registro de operaciones.

Los mismos tests de `core` (incluidas las 14 pruebas obligatorias) se ejecutan contra estos adaptadores con `GLOSA_TEST_ADAPTERS=glosa_storage.testing:make_adapters`, y la cola pasa las pruebas de contrato de `queue_contract`.

Limitaciones conocidas: SQLite admite un solo escritor a la vez; `verify_chain` carga el registro de la colección entera en memoria; `Database.close()` solo cierra la conexión del hilo que la llama.

### Adaptadores de `ingest` (implementados)

Se registran por nombre con el entry point `glosa.adapters`, que descubre `glosa_app` al arrancar.

| Nombre (plantilla)        | Puerto          | Qué hace                                                                       |
|---------------------------|-----------------|--------------------------------------------------------------------------------|
| `text`                    | `TextExtractor` | Texto plano UTF-8 (con o sin BOM); normaliza saltos de línea y quita bytes nulos |
| `markdown`                | `TextExtractor` | Como `text`, y además retira el bloque de metadatos YAML (*front matter*) inicial |
| `headings`                | `Chunker`       | Trocea por encabezados Markdown y empaqueta párrafos hasta `max_chars` (1200 por defecto) |

Reglas del chunker `headings`:

- Cada fragmento lleva en sus metadatos la **ruta de encabezados** (`Contrato > Pagos`) y el nivel, para poder citar la procedencia.
- Por defecto el fragmento incluye su línea de encabezado, de modo que se puede buscar por el título de una sección.
- Los encabezados dentro de bloques de código (``` o `~~~`) no cuentan, y un bloque de código no se parte por sus líneas en blanco.
- Un párrafo mayor que el límite se parte por frases; una frase demasiado larga, por palabras; una palabra enorme, a corte duro. Los bloques de código largos se parten por líneas.
- Una sección sin contenido (solo el encabezado) no genera fragmento, pero sí aparece en la ruta de sus hijos.
- El resultado es determinista: el mismo texto da siempre los mismos fragmentos y posiciones.
- Un archivo que no es UTF-8 falla de forma permanente con un mensaje claro: reintentar no lo arreglaría y adivinar la codificación daría texto corrupto.

Limitaciones conocidas: solo encabezados ATX (`# Título`), no los subrayados; las tablas y listas se tratan como párrafos; el tamaño es aproximado cuando el encabezado es muy largo.

## 9. Cola de trabajos

### 9.1 Qué se encola y qué no

| Operación                                  | Modo         | Motivo                                              |
|--------------------------------------------|--------------|-----------------------------------------------------|
| Subir documento (ingesta)                  | **Cola**     | Extraer, trocear e indexar puede tardar             |
| Modificar documento (nueva versión)        | **Cola**     | Igual que la ingesta, más limpieza de la versión anterior |
| Reindexar documento o colección            | **Cola**     | Operación pesada                                    |
| Borrar documento                           | **Cola**     | Debe limpiar índice y archivos sin carreras         |
| Buscar, leer, listar                       | **Síncrona** | El LLM o el usuario esperan la respuesta; siempre registrada |
| Búsquedas por lotes                        | Cola (opcional, futura) | Cargas grandes sin bloquear                |

Las lecturas son síncronas por defecto, pero pasan por el mismo circuito de autorización y registro.

### 9.2 Modelo de `Job`

| Campo             | Descripción                                                              |
|-------------------|--------------------------------------------------------------------------|
| `id`              | Identificador del trabajo                                                |
| `collection_id`   | Colección afectada                                                       |
| `type`            | `ingest` · `modify` · `reindex` · `delete`                               |
| `target`          | `document_id` (y versión, si aplica)                                     |
| `status`          | `queued` · `running` · `succeeded` · `failed` · `dead` · `cancelled`     |
| `priority`        | Entero; menor valor se atiende antes                                     |
| `attempts` / `max_attempts` | Intentos realizados y permitidos                               |
| `run_after`       | No ejecutar antes de esta fecha (reintentos con espera)                  |
| `idempotency_key` | Clave aportada por el cliente para evitar duplicados                     |
| `correlation_id`  | Une la petición original, el trabajo y todos sus pasos                   |
| `actor`           | Quién lo encoló (usuario o token)                                        |
| `lease_until`     | Hasta cuándo lo posee un worker                                          |
| `error`           | Último error, si lo hubo                                                 |
| `created_at`, `started_at`, `finished_at` | Marcas de tiempo                                 |

### 9.3 Estados

```
queued ──claim──► running ──ack──► succeeded
   ▲                 │
   │              fail│
   └──── retry ◄─────┤ (attempts < max_attempts, con espera creciente)
                      └──► dead (attempts agotados)
queued ──cancel──► cancelled
```

- Solo se puede cancelar un trabajo en `queued`.
- `dead` equivale a una cola de mensajes fallidos: el propietario puede ver el error y relanzarlo manualmente.

### 9.4 Garantías y reglas

- **Entrega al menos una vez.** Un trabajo puede ejecutarse más de una vez (caída del worker, caducidad del lease), por lo que todos los manejadores deben ser **idempotentes**.
- **Lease con latido.** Un worker toma el trabajo por un tiempo limitado y lo renueva; si desaparece, el trabajo vuelve a `queued`.
- **Orden por colección.** Los trabajos de escritura de una misma colección sobre un mismo documento se ejecutan **en serie**, en orden de llegada. Evita, por ejemplo, borrar un documento mientras se indexa.
- **Equidad.** Límite de trabajos concurrentes por colección y planificación rotatoria entre colecciones, para que una carga masiva no deje sin servicio a las demás.
- **Idempotencia en el encolado.** Si llega una petición con una `idempotency_key` ya vista en esa colección, se devuelve el trabajo existente en lugar de crear otro.
- **Reintentos con espera creciente** y tope de intentos configurable.
- **Contrapresión.** Límite de trabajos en cola por colección; al superarlo, la API responde con un error claro de capacidad.
- **Atomicidad.** El cambio de estado del documento, la entrada en el registro y el cierre del trabajo se confirman juntos o no se confirman.

## 10. Registro de operaciones y trazabilidad

El `OperationLog` es la **fuente única de verdad** de todo lo que ocurre en el sistema. Sustituye al antiguo registro de auditoría y alimenta tanto la auditoría como la capa didáctica.

### 10.1 Qué se registra

| Categoría       | Operaciones                                                                              |
|-----------------|------------------------------------------------------------------------------------------|
| Subida          | Petición recibida, trabajo encolado, texto extraído, fragmentos creados, indexado, resultado |
| Modificación    | Nueva versión creada, versión anterior retirada del índice, resultado                    |
| Consulta        | `buscar`, `leer_documento`, `listar_documentos` (por API o por MCP)                      |
| Borrado         | Petición, limpieza de índice y archivos, resultado                                       |
| Cola            | Encolado, inicio, reintento, fallo, `dead`, cancelación                                  |
| Seguridad       | Emisión y revocación de tokens, cambios de miembros, **todas las denegaciones**          |

### 10.2 Estructura de `OperationEntry`

| Campo            | Descripción                                                                    |
|------------------|--------------------------------------------------------------------------------|
| `id`             | Identificador único                                                            |
| `at`             | Marca de tiempo                                                                |
| `correlation_id` | Une toda la cadena: petición → trabajo → pasos → resultado                     |
| `actor`          | Usuario o token (con su identificador, nunca el valor del token)               |
| `channel`        | `api` · `mcp` · `worker` · `system`                                            |
| `action`         | Nombre de la operación (`document.ingest`, `search.execute`, `token.issue`, ...) |
| `collection_id`  | Colección afectada                                                             |
| `target`         | Documento, versión y/o trabajo afectados                                       |
| `outcome`        | `allowed` · `denied` · `succeeded` · `failed`                                  |
| `duration_ms`    | Duración, cuando aplica                                                        |
| `details`        | Datos específicos de la acción (ver abajo)                                     |
| `prev_hash` / `hash` | Encadenado opcional para detectar manipulaciones                           |

### 10.3 Contenido de `details` según la acción

| Acción                  | Datos guardados                                                                   |
|-------------------------|-----------------------------------------------------------------------------------|
| Ingesta / modificación  | `content_hash`, tamaño, versión, número de fragmentos, tiempo por paso            |
| Consulta (`buscar`)     | Consulta (texto o hash, según ajuste), estrategia, límite, identificadores y puntuaciones de los fragmentos devueltos |
| Lectura                 | Documento y versión leídos                                                        |
| Borrado                 | Documento, última versión, fragmentos eliminados                                  |
| Denegación              | Permiso o scope que faltaba                                                       |
| Fallo de trabajo        | Paso donde falló, mensaje de error, intento                                       |

### 10.4 Correlación de extremo a extremo

El `correlation_id` se genera al recibir la petición (API o MCP) y se propaga: se guarda en el `Job`, lo usa el `worker` y aparece en cada `OperationEntry`. Con un solo identificador se reconstruye la historia completa de una operación. La API lo devuelve en una cabecera de respuesta.

### 10.5 Versionado de documentos

- Subir un archivo con el mismo identificador de documento, o usar la ruta de modificación, **crea una versión nueva**; nunca se sobrescribe.
- Cada `DocumentVersion` guarda `content_hash`, autor y fecha. Subir un contenido idéntico a la versión vigente no crea versión nueva (se registra como sin cambios).
- Por defecto se conserva el **contenido** de todas las versiones, para poder consultar o restaurar cualquiera. La colección puede configurar conservar solo hashes y las últimas N versiones.
- Solo la versión vigente está en el índice de búsqueda. Al modificar, los fragmentos de la versión anterior se retiran dentro del mismo trabajo.
- `GET /documents/{id}/history` lista las versiones; `GET /documents/{id}?version=n` recupera una concreta.

### 10.6 Privacidad y retención

Las consultas pueden contener datos sensibles, por lo que cada colección configura:

| Ajuste              | Valores                              | Por defecto |
|---------------------|--------------------------------------|-------------|
| `query_logging`     | `full` · `hash_only`                 | `full` en la demo, `hash_only` recomendado en uso real |
| `retention_days`    | Días que se conserva el registro     | Configurable por colección |
| `version_retention` | `all` · `last_n` + `n`               | `all`       |
| `hash_chain`        | Activado / desactivado               | Activado    |

Reglas:

- No se registran nunca el valor de los tokens ni el contenido íntegro de los documentos en el registro (solo hashes y referencias).
- Al borrar una colección se borra su registro, salvo que se haya configurado una retención mínima.
- El registro es **solo de añadir**: ni la API ni los casos de uso permiten editar o borrar entradas; solo la purga por retención.

### 10.7 Auditoría y capa didáctica como vistas

- **Auditoría:** vista del registro filtrada por seguridad (denegaciones, tokens, miembros, accesos). La consulta el `owner`.
- **Trazas didácticas (`explain`):** lectura del registro agrupada por `correlation_id`, presentada paso a paso para que el frontend la dibuje.
- Ninguna de las dos escribe datos propios.

## 11. Casos de uso (`core/usecases/`)

Cada caso de uso recibe un `Actor` ya identificado, **comprueba el permiso** con el servicio de autorización y deja constancia en el `OperationLog`. Los casos de uso de escritura **encolan**; el trabajo real lo ejecutan manejadores que invoca el `worker`.

| Caso de uso           | Permiso requerido     | Modo       | Resultado                          |
|-----------------------|-----------------------|------------|------------------------------------|
| `CreateCollection`    | usuario autenticado   | síncrono   | `Collection`                       |
| `SubmitDocument`      | `write` / `editor`    | **encola** | `Job` (tipo `ingest` o `modify`)   |
| `DeleteDocument`      | `write` / `editor`    | **encola** | `Job` (tipo `delete`)              |
| `ReindexDocument`     | `editor`              | **encola** | `Job` (tipo `reindex`)             |
| `SearchCollection`    | `read` / `reader`     | síncrono   | `list[SearchHit]`                  |
| `ReadDocument`        | `read` / `reader`     | síncrono   | `Document` + texto (versión opcional) |
| `ListDocuments`       | `read` / `reader`     | síncrono   | `list[Document]`                   |
| `GetDocumentHistory`  | `editor`              | síncrono   | `list[DocumentVersion]`            |
| `GetJob` / `ListJobs` | `editor`              | síncrono   | `Job` / `list[Job]`                |
| `CancelJob`           | `editor`              | síncrono   | `Job` cancelado                    |
| `RetryDeadJob`        | `owner`               | síncrono   | `Job`                              |
| `IssueToken`          | `owner`               | síncrono   | token en claro (una sola vez)      |
| `RevokeToken`         | `owner`               | síncrono   | —                                  |
| `ManageMembers`       | `owner`               | síncrono   | —                                  |
| `QueryOperations`     | `owner`               | síncrono   | `list[OperationEntry]`             |
| `VerifyOperationLog`  | `owner`               | síncrono   | `ChainReport`                      |
| `ListCollections`     | usuario autenticado   | síncrono   | `list[Collection]`                 |
| `UpdateCollectionSettings` | `owner`          | síncrono   | `Collection`                       |
| `DeleteCollection`    | `owner`               | síncrono   | —                                  |
| `ViewTrace`           | `editor`              | síncrono   | traza por `correlation_id`         |

### Manejadores del worker

| Manejador          | Pasos (cada uno deja entrada en el registro)                                                      |
|--------------------|---------------------------------------------------------------------------------------------------|
| `HandleIngest`     | Leer contenido → extraer texto → trocear → indexar → marcar documento `ready`                    |
| `HandleModify`     | Crear versión → extraer → trocear → indexar nueva versión → retirar versión anterior del índice   |
| `HandleReindex`    | Releer versión vigente → trocear → reemplazar fragmentos                                          |
| `HandleDelete`     | Retirar del índice → marcar borrado → eliminar contenido según política de retención              |

Los manejadores reciben sus puertos por constructor (inyección de dependencias) y son idempotentes: ejecutarlos dos veces deja el mismo estado final.

**Mecánica común (implementada):**

- Cada caso de uso recibe un `RequestContext` (actor, canal y `correlation_id`) y un `Kernel` con los servicios transversales (autorización, registrador, reloj, ids).
- Una denegación de permiso deja una entrada `denied` en el registro de la colección afectada; un error de validación deja una entrada `failed`.
- `HandleIngest` atiende los trabajos `ingest` y `modify`. Los fragmentos tienen identificador determinista (`<doc>:<versión>:<posición>`) y, antes de indexar, se limpia lo que hubiera dejado un intento interrumpido.
- `ProcessNextJob` es lo que hace un worker en cada vuelta: toma un trabajo, lo despacha, y decide entre `ack`, reintento con espera creciente o `dead`. Actúa con la identidad y el `correlation_id` de quien encoló el trabajo. El adaptador `worker` solo lo llama en bucle.
- Los errores permanentes (`PermanentJobError`) pasan a `dead` sin reintentos. Un documento sin texto indexable es uno de ellos.
- `CancelJob` solo cancela un trabajo en cola (si no, `Conflict`). Una ingesta nueva cancelada deja el documento en `failed`, porque nunca se indexó; una modificación cancelada deja el documento sirviendo su versión vigente.
- "Sin cambios" se decide frente a la versión **vigente** (la indexada), no frente a la última subida: si esa se canceló o falló, volver a subir el mismo contenido sí crea trabajo.
- Las escrituras relacionadas se confirman juntas con `UnitOfWork` (§8). Si algo falla dentro, no queda nada a medias, y el error se registra aparte, fuera de la transacción deshecha.
- `QueryOperations` anota su propia consulta **después** de leer el registro, para que no aparezca en su resultado. El registro se devuelve de antiguo a reciente.

## 12. Servidor MCP (`adapters/mcp-server`)

Un único servidor **multitenant**: la colección se resuelve a partir del token. Capa fina: traduce llamadas MCP a casos de uso.

### Herramientas expuestas

| Herramienta           | Parámetros                              | Scope  | Descripción                                            |
|-----------------------|-----------------------------------------|--------|--------------------------------------------------------|
| `buscar`              | `consulta`, `limite` (def. 5)           | `read` | Devuelve fragmentos relevantes con título, versión y puntuación |
| `leer_documento`      | `id`, `version` (opcional)              | `read` | Devuelve el texto completo de un documento             |
| `listar_documentos`   | —                                       | `read` | Lista los documentos de la colección                   |

En la v0.x el servidor MCP es **solo de lectura**. Las herramientas de escritura (`subir_documento`, `borrar_documento`) se contemplan para versiones futuras: requerirían el scope `write` y **encolarían** el trabajo, devolviendo su `job_id`.

### Reglas

- Autenticación por token en cabecera; el token determina el `collection_id`.
- El servidor **nunca** acepta un `collection_id` como parámetro del cliente.
- Las respuestas incluyen siempre la procedencia (documento, versión y posición) para poder citar.
- Las descripciones de las herramientas explican *cuándo* usarlas.
- El contenido de los documentos se devuelve como **datos**. Un documento puede contener instrucciones maliciosas (inyección de prompts); por eso las herramientas de lectura nunca ejecutan acciones y el modo de solo lectura es el predeterminado.
- Cada llamada genera un `correlation_id` y entradas en el registro de operaciones.

## 13. API de gestión (`adapters/http-api`)

El contrato público se describe en `docs/openapi.yaml`, fuente de verdad del cliente del frontend.

| Método y ruta                                        | Permiso     | Función                                           |
|------------------------------------------------------|-------------|---------------------------------------------------|
| `POST   /v1/collections`                             | autenticado | Crear colección                                   |
| `GET    /v1/collections`                             | autenticado | Listar mis colecciones                            |
| `PATCH  /v1/collections/{id}/settings`               | `owner`     | Ajustes de registro, retención y versiones        |
| `DELETE /v1/collections/{id}`                        | `owner`     | Borrar colección                                  |
| `GET    /v1/collections/{id}/members`                | `owner`     | Listar miembros                                   |
| `PUT    /v1/collections/{id}/members/{user_id}`      | `owner`     | Añadir o cambiar rol                              |
| `POST   /v1/collections/{id}/documents`              | `editor`    | Subir documento → `202` + `job_id`                |
| `PUT    /v1/collections/{id}/documents/{doc_id}`     | `editor`    | Modificar (nueva versión) → `202` + `job_id`      |
| `GET    /v1/collections/{id}/documents`              | `reader`    | Listar documentos y su estado                     |
| `GET    /v1/collections/{id}/documents/{doc_id}`     | `reader`    | Obtener documento (`?version=n` opcional)         |
| `GET    /v1/collections/{id}/documents/{doc_id}/history` | `editor` | Historial de versiones                           |
| `DELETE /v1/collections/{id}/documents/{doc_id}`     | `editor`    | Borrar documento → `202` + `job_id`               |
| `POST   /v1/collections/{id}/documents/{doc_id}/reindex` | `editor` | Reindexar → `202` + `job_id`                     |
| `POST   /v1/collections/{id}/search`                 | `reader`    | Buscar (síncrono)                                 |
| `GET    /v1/collections/{id}/jobs`                   | `editor`    | Listar trabajos (filtro por estado)               |
| `GET    /v1/collections/{id}/jobs/{job_id}`          | `editor`    | Estado de un trabajo                              |
| `POST   /v1/collections/{id}/jobs/{job_id}/cancel`   | `editor`    | Cancelar un trabajo en cola                       |
| `POST   /v1/collections/{id}/jobs/{job_id}/retry`    | `owner`     | Relanzar un trabajo `dead`                        |
| `POST   /v1/collections/{id}/tokens`                 | `owner`     | Emitir token MCP                                  |
| `DELETE /v1/collections/{id}/tokens/{token_id}`      | `owner`     | Revocar token                                     |
| `GET    /v1/collections/{id}/operations`             | `owner`     | Registro de operaciones (filtros y paginación)    |
| `GET    /v1/collections/{id}/operations/verify`      | `owner`     | Verificar el encadenado de hashes                 |
| `GET    /v1/collections/{id}/traces/{correlation_id}`| `editor`    | Traza paso a paso de una operación                |
| `GET    /v1/collections/{id}/audit`                  | `owner`     | Vista de auditoría (seguridad y denegaciones)     |

### Convenciones

- **Escrituras asíncronas:** responden `202 Accepted` con `job_id`, `correlation_id` y la URL para consultar el estado.
- **Idempotencia:** cabecera `Idempotency-Key` en las escrituras.
- **Correlación:** cabecera de respuesta `X-Correlation-Id` en todas las respuestas.
- **Errores:** formato uniforme con código estable, mensaje y, si procede, el permiso que faltaba.
- **Capacidad:** si la cola de la colección está llena, `429` con indicación de cuándo reintentar.
- **Paginación** en todos los listados y en el registro.
- Versionado en la ruta (`/v1/...`) desde el primer día.

## 14. Multitenancy y seguridad

- **Aislamiento en la capa de datos:** todas las consultas del repositorio, del índice, de la cola y del registro exigen `collection_id`. No es un filtro opcional de la aplicación.
- Límites por colección: tamaño de archivo, número de documentos, de fragmentos, de versiones y de trabajos en cola.
- Limitación de peticiones (rate limit) por token y por usuario.
- Borrado completo: eliminar un documento retira sus fragmentos del índice y sus versiones según la política de retención.
- CORS restringido a los orígenes del frontend configurado.
- Sin secretos en el repositorio; configuración por variables de entorno.

### Pruebas de seguridad y consistencia obligatorias

1. Un token de la colección A nunca devuelve datos, trabajos ni registros de la B.
2. Un token `read` no puede subir, modificar ni borrar.
3. Un token revocado o caducado es rechazado de inmediato.
4. Un `reader` no puede emitir tokens ni ver el registro de operaciones.
5. Un token no puede emitirse con más scopes que los del emisor.
6. Todas las denegaciones quedan en el registro de operaciones.
7. Una misma `idempotency_key` no crea trabajos ni versiones duplicadas.
8. Ejecutar dos veces un trabajo deja el mismo estado final (idempotencia de manejadores).
9. Dos escrituras sobre el mismo documento se ejecutan en el orden de llegada.
10. Si un worker cae a mitad de un trabajo, el trabajo se recupera y termina sin dejar fragmentos huérfanos.
11. Tras modificar un documento, la búsqueda solo devuelve fragmentos de la versión vigente.
12. Todo `correlation_id` permite reconstruir la cadena completa desde la petición hasta el resultado.
13. Manipular una entrada del registro hace fallar `verify`.
14. Con `hash_only`, el texto de las consultas no aparece en el registro.

## 15. Capa didáctica

`explain` (backend) lee el registro de operaciones agrupado por `correlation_id` y lo expone como trazas. Ningún otro paquete lo importa. El frontend solo las dibuja.

### Funciones de la UI (frontend)

| Función                      | Qué enseña                                                                      |
|------------------------------|---------------------------------------------------------------------------------|
| **Ver por dentro (ingesta)** | Texto extraído, fragmentos resaltados y qué se guardó en el índice               |
| **Cola en vivo**             | Trabajos en cola, en curso, reintentos y fallos; orden por colección             |
| **Historial de un documento**| Versiones, diferencias entre ellas y qué versión está indexada                   |
| **Búsqueda explicada**       | Fragmentos recuperados, su puntuación y el prompt final que recibiría el modelo  |
| **Traza del MCP**            | Cada llamada de herramienta con parámetros y respuesta                           |
| **Línea de tiempo de una operación** | Todo lo ocurrido bajo un `correlation_id`, de la petición al resultado   |
| **Comparador RAG vs MCP**    | La misma pregunta con recuperación fija y con herramienta, lado a lado           |
| **Permisos en vivo**         | Qué puede y qué no puede hacer cada token, con las denegaciones a la vista       |
| **Ejemplos precargados**     | Documentos pequeños y preguntas sugeridas para ver el efecto en segundos         |

### Documentación didáctica

Cada paquete incluye en su `README.md`:

1. **Qué hace**, en una frase.
2. **Por qué existe** como pieza separada.
3. **Cómo se usa** suelto, con un ejemplo mínimo.
4. **Qué se puede cambiar** (puertos y adaptadores alternativos).

### Paquete `explain` (implementado)

Convierte las entradas del registro que comparten un `correlation_id` en una **traza** que se lee paso a paso. El caso de uso `ViewTrace` (editor o superior) devuelve las entradas; `explain.build_trace` las presenta. `explain` solo depende de `core` y nadie depende de él.

| Campo de `Trace`   | Contenido                                                                              |
|--------------------|----------------------------------------------------------------------------------------|
| `steps`            | Cada paso con su título y detalle en lenguaje llano, canal, actor, hora y duración     |
| `outcome`          | `succeeded`, `failed`, `denied` o `in_progress`                                        |
| `channels`         | Canales por los que pasó, en orden (por ejemplo `api` → `worker`)                      |
| `duration_ms`      | De la primera a la última entrada                                                      |

Reglas del resultado: cualquier denegación → `denied`; un trabajo muerto o un paso fallido sin reintento → `failed`; un trabajo que empezó o espera un reintento, o una subida aún sin procesar → `in_progress`; si no, `succeeded`. Un reintento que acaba bien es `succeeded`, y el fallo intermedio **se conserva** en la traza.

Los títulos están en español llano (`Texto dividido en fragmentos`, `El trabajo falló y se reintentará`, `Acceso denegado`...) y una prueba comprueba que toda acción del sistema tiene su descripción. Una acción que `explain` aún no conozca no rompe la traza: se muestra con su nombre técnico. `Trace.to_text()` la presenta como texto para una terminal o un informe. Si la colección usa `query_logging: hash_only`, la traza de una búsqueda dice que la consulta no se guardó, en lugar de mostrarla.

## 16. Evaluación

- Conjunto de preguntas de prueba en `examples/` con el documento y fragmento esperados.
- Métrica simple: **¿aparece el fragmento correcto entre los k primeros resultados?** (recall@k).
- Script `eval` que ejecuta el conjunto y muestra el resultado por estrategia.
- Sirve para decidir con datos cuándo merece la pena añadir embeddings.

## 17. Despliegue

### 17.1 Imagen (`backend/Dockerfile`)

Imagen multietapa, con el contexto de construcción en `backend/`:

| Etapa      | Contenido                                                                                      |
|------------|------------------------------------------------------------------------------------------------|
| `builder`  | Instala todos los paquetes en un entorno virtual                                               |
| `runtime`  | Imagen final: solo el entorno virtual, sin herramientas de compilación, usuario sin privilegios (uid 10001) |
| `test`     | `builder` más `pytest` y el código fuente, para ejecutar los tests en contenedor               |

- `/data` y `/app/templates` existen en la imagen con el propietario correcto, para que los volúmenes con nombre los hereden.
- No hay secretos en la imagen: la configuración llega por variables de entorno y las plantillas por volumen.

### 17.2 Orquestación (`backend/docker-compose.yml`)

| Servicio  | Estado               | Función                                                                       |
|-----------|----------------------|-------------------------------------------------------------------------------|
| `check`   | Operativo            | Valida la plantilla activa (esquema y guardia de producción) y termina        |
| `tests`   | Operativo (perfil `test`) | Ejecuta los tests dentro de un contenedor                                |
| `api`     | Pendiente (perfil `pendiente`) | API de gestión, puerto 8000                                        |
| `mcp`     | Pendiente (perfil `pendiente`) | Servidor MCP, puerto 8001                                          |
| `worker`  | Operativo (perfil `worker`)    | Procesa la cola; escalable con `--scale worker=N`                  |

- `api` y `mcp` están definidos pero agrupados en el perfil `pendiente`, de modo que `docker compose up` no los arranca; cuando existan los adaptadores basta con quitar la línea `profiles`. Hasta entonces, su punto de entrada termina con un mensaje claro y código de salida 2. El `worker` va en su propio perfil (`docker compose --profile worker up worker`) para que `docker compose up` siga validando y terminando; su `stop_grace_period` es de 60 s para que, al pararlo, termine el trabajo en curso.
- Todos los servicios corren con sistema de archivos de solo lectura, sin capacidades de Linux y con `no-new-privileges`.
- Las plantillas de cliente se montan en solo lectura desde `examples/templates`; para usar otras se cambia ese volumen.
- Los datos (`/data`) van en el volumen con nombre `glosa-data`.

### 17.3 Configuración

| Variable               | Función                                                                        | Por defecto  |
|------------------------|--------------------------------------------------------------------------------|--------------|
| `GLOSA_TEMPLATE`       | Plantilla activa: preset, nombre de fichero en `GLOSA_TEMPLATE_DIRS` o ruta    | `didactico`  |
| `GLOSA_TEMPLATE_DIRS`  | Carpetas con plantillas de cliente, separadas por `:`                          | `/app/templates` en la imagen |
| `GLOSA_DATA_DIR`       | Carpeta de datos (la base `glosa.db` vive aquí)                                | `./data` (`/data` en la imagen) |
| `GLOSA_WORKER_ID`      | Identidad del worker en el registro de trabajos                                | `<host>-<pid>` |
| `GLOSA_WORKER_LEASE_SECONDS` | Plazo que el worker se reserva cada trabajo antes de que otro lo recupere | `300`        |

Al arrancar se valida la plantilla. En modo `production` el arranque se aborta si la guardia de producción detecta algún problema (ver §18.4). La orden `python -m glosa_app check` hace esa comprobación sin arrancar nada; con `--strict` también falla si la plantilla pide adaptadores que no están registrados (hoy ninguno lo está).

### 17.4 Otros

- Con la plantilla `didactico`: datos de ejemplo cargados al primer arranque, junto con un usuario y un token de demostración. Con `profesional` no hay datos ni credenciales de demo.
- El frontend se despliega por separado, o se sirve como estático.
- El README del backend explica cómo conectar el servidor MCP a un cliente compatible.
- El README del frontend explica cómo apuntarlo a otra instancia del backend.

### 17.5 Composición y worker

`glosa_app.build_app(template, data_dir=...)` (o `build_from_env`) es el único sitio donde se construye el sistema:

1. Aplica la **guardia de producción**: una plantilla insegura no arranca y ni siquiera crea la base de datos.
2. Comprueba que todos los adaptadores que pide la plantilla estén registrados; si no, falla con la lista de los que faltan (`ConfigurationError`).
3. Construye los adaptadores por el nombre que pide la plantilla (convención de las fábricas: `storage(data_dir)`, `queue(storage, clock)`, `index(storage)`) y cablea los casos de uso.
4. Traduce la política de la plantilla a la configuración de los casos de uso: los ajustes con los que nace cada colección, la caducidad por defecto de los tokens y el límite de búsqueda (`retrieval.k`).
5. Deja constancia del arranque: una entrada `template.applied` en la cadena global del registro, con el nombre, el modo y la **huella** de la plantilla resuelta (actor y canal `system`).

El worker se ejecuta con `python -m glosa_app worker`:

| Opción         | Efecto                                                                                      |
|----------------|---------------------------------------------------------------------------------------------|
| (ninguna)      | Se queda esperando trabajos y procesa los que lleguen                                       |
| `--once`       | Procesa los trabajos que haya listos y termina (uno en espera de reintento no cuenta)       |
| `--idle-seconds` | Espera cuando no hay trabajos (por defecto, 1 s); se interrumpe al pedir parar            |

- `SIGTERM` y `Ctrl+C` piden parar: el worker **termina el trabajo en curso** y sale.
- Un fallo de infraestructura (por ejemplo, la base bloqueada) se avisa y se reintenta con espera creciente; tras 20 seguidos el worker se rinde con código de salida 1 para que el orquestador lo reinicie.
- Códigos de salida: `0` correcto, `1` error de configuración o worker rendido.
- La lógica de qué hacer con cada trabajo (reintentos, `dead`) vive en `core` (`ProcessNextJob`); el adaptador `worker` solo ofrece el bucle y no conoce colas ni plantillas.

## 18. Plantillas y adaptación a clientes

### 18.1 Objetivo

Un mismo núcleo sirve al uso didáctico y al comercial. La adaptación a un cliente o proyecto se hace con una **plantilla**: un fichero YAML declarativo que elige adaptadores y ajustes, sin tocar código. Vive en el paquete `packages/templates`.

### 18.2 Qué decide una plantilla

| Sección       | Qué decide                                                                                  |
|---------------|---------------------------------------------------------------------------------------------|
| `mode`        | `didactic` o `production`; activa la guardia de producción                                  |
| `adapters`    | Almacenamiento, cola, índice, embeddings, extractores, chunker y autenticación, por nombre  |
| `retrieval`   | Estrategia (`text` / `vector` / `hybrid`), `k` y reranker                                   |
| `mcp`         | Idioma y **descripción** de cada herramienta (los nombres y scopes son fijos)               |
| `policy`      | `query_logging`, retención, versiones, encadenado de hashes, caducidad de tokens y límites  |
| `metadata`    | Campos de metadatos propios del dominio del cliente                                         |
| `branding`    | Nombre, logo, color, idioma y paneles didácticos del frontend                               |
| `evaluation`  | Conjunto de preguntas del cliente                                                           |
| `demo`        | Datos de ejemplo y token de demostración                                                    |

### 18.3 Herencia

| Plantilla      | Hereda de     | Propósito                                                                    |
|----------------|---------------|------------------------------------------------------------------------------|
| `didactico`    | —             | Todo visible, registro completo de consultas, datos y token de demo          |
| `profesional`  | `didactico`   | Modo producción: `hash_only`, retención, sin datos de demo ni paneles didácticos |
| `<cliente>`    | `profesional` | Solo declara lo que cambia                                                   |

```yaml
name: acme-legal
extends: profesional
mcp:
  tools:
    buscar: "Busca cláusulas en los contratos de Acme"
metadata: [fecha_contrato, jurisdiccion]
```

Reglas de fusión:

- Los objetos se fusionan campo a campo; cualquier otro valor (listas incluidas) se **reemplaza**.
- La herencia circular se rechaza.
- Los presets tienen prioridad: un fichero de cliente con el nombre `profesional` no puede ocultar al preset.

### 18.4 Reglas

1. **Los invariantes no son configurables.** El aislamiento por colección (§14), la autorización única (§7), el registro de solo añadir (§10) y el hasheado de tokens no existen como opciones del esquema. Cualquier clave no declarada se rechaza como desconocida.
2. **Validación al arrancar.** El esquema se comprueba entero y se listan todos los errores a la vez.
3. **Guardia de producción.** Con `mode: production` el arranque se aborta si:
   - `demo.seed_data` o `demo.demo_token` están activos;
   - `policy.query_logging` no es `hash_only`;
   - `policy.hash_chain` no es `true`;
   - `policy.retention_days` no es un número de días mayor que 0;
   - hay secretos escritos en el fichero.
4. **Secretos por entorno.** Las claves que parecen secretos (`secret`, `password`, `token`, `api_key`) solo admiten referencias `${NOMBRE}`.
5. **Plantilla activa registrada** (implementado). Al arrancar se deja una entrada `template.applied` en el registro de operaciones con el nombre, el modo y la huella de la plantilla resuelta.
6. **Los ajustes por colección (§10.6) no pueden debilitar la plantilla activa.** Pueden ser iguales o más estrictos. *Regla de diseño pendiente de implementar.*

### 18.5 Adaptadores como plugins

- Cada adaptador se registra **por nombre** en un `Registry` (tipos: `storage`, `queue`, `index`, `embedder`, `extractors`, `chunker`, `authenticator`).
- Los paquetes externos se descubren por entry points del grupo `glosa.adapters`: cada uno expone una función `register(registry)`.
- Un cliente con un caso especial añade su paquete y lo nombra en su plantilla, sin bifurcar el núcleo.
- Si una plantilla pide un adaptador no registrado, el arranque falla con un mensaje claro.

### 18.6 Modelo de despliegue

- **Por defecto, una instalación por cliente.** La plantilla se elige al arrancar con `GLOSA_TEMPLATE`. Los datos y la infraestructura de cada cliente quedan separados.
- **Instancia compartida con una plantilla por organización:** fuera del alcance de las versiones 0.x. Si se aborda, la plantilla se resolverá por organización y la regla 6 de §18.4 pasará a ser obligatoria.

### 18.7 Dónde viven las plantillas

- Los presets `didactico` y `profesional` van dentro de `packages/templates`.
- Las plantillas de cada cliente viven en un **repositorio privado aparte**, junto con su conjunto de evaluación, para que el repositorio didáctico pueda ser público y el núcleo se mantenga genérico.
- `backend/examples/templates/acme-legal.yaml` es un ejemplo ficticio y se valida en los tests.

### 18.8 Criterios de entrega de una plantilla de cliente

1. Pasa la validación del esquema y la guardia de producción.
2. Todos sus adaptadores están registrados.
3. Las 14 pruebas obligatorias de §14 pasan con esa plantilla.
4. Alcanza el `recall@k` mínimo acordado con el cliente sobre su conjunto de evaluación.
5. No incluye datos ni credenciales de demostración.

## 19. Licencia y modelo comercial

> **Aviso:** borrador sin revisión legal. Antes de publicar o vender, debe revisarlo alguien especializado en propiedad intelectual.

### 19.1 Modelo

El proyecto es **código disponible** (*source-available*), no *open source* en sentido estricto. Es gratuito para personas y pequeñas empresas, y las empresas que superen el límite necesitan una licencia comercial.

| Capa                  | Fichero                | Quién                                                                  |
|-----------------------|------------------------|------------------------------------------------------------------------|
| Licencia pública      | `LICENSE`              | PolyForm Small Business 1.0.0: uso gratuito para quien tenga menos de 100 personas (empleados y contratistas) y menos de 1.000.000 USD (de 2019) de ingresos el año fiscal anterior, con el umbral ajustado por inflación. Una persona individual cumple estos límites |
| Licencia comercial    | `LICENSE-COMERCIAL.md` | Empresas que superen esos límites; tramos y precios por definir         |

### 19.2 Aportación voluntaria

A los usuarios y pequeñas empresas se les pide, sin obligación y sin que condicione la licencia, que ayuden al proyecto. Se canaliza con un apartado "Apoya el proyecto" en el README y un fichero `.github/FUNDING.yml` (plataformas como GitHub Sponsors, Open Collective o Liberapay).

### 19.3 Contribuciones externas

- No se acepta código externo sin **CLA** firmado (`CLA.md`, borrador). Un DCO por sí solo no concede el derecho a relicenciar, y ese derecho es lo que permite seguir ofreciendo la licencia comercial.
- Las plantillas de cliente no forman parte del repositorio público.

### 19.4 Dependencias

- Sin copyleft fuerte (GPL, AGPL) en el núcleo ni en las dependencias que se distribuyen, porque chocaría con este modelo.
- El inventario está en `docs/licencias-dependencias.md` y se revisa al añadir cada dependencia.

### 19.5 Licenciatario y plantillas de cliente

**Decisión pendiente:** cuando se despliega el sistema para un cliente grande, ¿quién es el licenciatario? Propuesta por defecto: el cliente, que adquiere la licencia comercial. Las plantillas de cliente se licencian por separado, en su propio contrato.

### 19.6 Pendiente antes de publicar

- Indicar el titular legal del copyright en `LICENSE`.
- Pegar en `LICENSE` el texto íntegro oficial de PolyForm Small Business 1.0.0.
- Fijar tramos y precios en `LICENSE-COMERCIAL.md`.
- Revisión legal de la licencia comercial y del CLA.
- Completar los enlaces de apoyo.
- Comprobar la marca **Glosa** en la OEPM (con un agente de la propiedad industrial, si se va a vender) y registrar los dominios y el usuario de GitHub.

## 20. Hoja de ruta

| Versión | Contenido                                                                                           |
|---------|-----------------------------------------------------------------------------------------------------|
| **0.1** | Núcleo, ingesta `.md`/`.txt`, SQLite FTS5, roles y tokens con scopes, cola en SQLite con worker, registro de operaciones con encadenado, versionado de documentos, MCP de solo lectura, API con OpenAPI, evaluación mínima, paquete `templates` con los presets `didactico` y `profesional`, ficheros de licencia |
| **0.2** | Frontend con cola en vivo, historial, línea de tiempo de operaciones y permisos en vivo             |
| **0.3** | PDF, embeddings, búsqueda híbrida, comparador de estrategias                                        |
| **0.4** | Reranker, OCR, adaptador Postgres/pgvector, búsquedas por lotes por cola                            |
| **0.5** | OIDC para usuarios y OAuth 2.1 para clientes MCP remotos, herramientas MCP de escritura con `write` |

## 21. Registro de cambios

### v0.4.5
- `app`: composición del sistema desde la plantilla (`build_app`, `build_from_env`), con guardia de producción, comprobación de adaptadores y traducción de la política de la plantilla a la configuración de los casos de uso.
- `worker`: el bucle del proceso (`run`, `drain`) y la orden `python -m glosa_app worker` con `--once`, paro ordenado por señales y espera creciente ante fallos de infraestructura.
- `ViewTrace` (caso de uso) y paquete `explain` (`build_trace`): la traza de una operación, paso a paso y en lenguaje llano.
- Actor y canal `system` para eventos sin persona (el arranque); sin ningún permiso.
- El arranque deja una entrada `template.applied` con la huella de la plantilla (`Template.fingerprint`).
- `SearchCollection` acepta un límite por defecto (`retrieval.k`).
- Corregido: `Database.close()` solo cerraba la conexión del hilo que lo llamaba; ahora cierra las de todos los hilos y descarta las de los hilos que terminan.
- Los adaptadores `authenticator: token` y `embedder: none` se registran desde `app`; `check --strict` pasa con los presets.
- `docker-compose`: el servicio `worker` es operativo (perfil `worker`).
- ADRs 0031 a 0034. Total: 25 casos de uso, 15 implementados.

### v0.4.4
- `storage`: adaptadores SQLite de colecciones, accesos, documentos (con el contenido de cada versión en la base), índice FTS5, cola, registro de operaciones y `UnitOfWork`, con migraciones numeradas y borrado de colección en cascada.
- Nuevo puerto `UnitOfWork`; las escrituras relacionadas de `CreateCollection`, `IssueToken`, `RevokeToken`, `SubmitDocument`, `CancelJob`, `HandleIngest` y `ProcessNextJob` se confirman juntas. Cierra la deuda de atomicidad de §9.4.
- La idempotencia de `SubmitDocument` ya no depende de un `find` seguido de un `insert`: la garantiza un índice único en la base.
- Los tests de `core` se pueden ejecutar contra cualquier conjunto de adaptadores (`GLOSA_TEST_ADAPTERS`); la batería completa, incluidas las 14 pruebas obligatorias, pasa también contra SQLite.
- Tests propios de `storage`: transacciones, concurrencia entre hilos, FTS5, atomicidad con fallos inyectados, persistencia tras reabrir y borrado en cascada.
- Corregido: los tests de `core` importaban constantes desde `conftest`, lo que fallaba al ejecutarlos junto a otros paquetes. Pasan a `glosa_core.testing`.
- La spec incluye ahora `ListCollections`, `UpdateCollectionSettings` y `DeleteCollection`, que la API ya necesitaba (§13) y no tenían caso de uso. Total: 25 casos de uso, 14 implementados.
- ADRs 0027 a 0030.

### v0.4.3
- Casos de uso nuevos: `GetJob`, `ListJobs`, `CancelJob`, `QueryOperations` y `VerifyOperationLog` (este último cubre el endpoint `operations/verify`, que no tenía caso de uso). Total: 22 casos de uso, 14 implementados.
- Las pruebas obligatorias 1, 4 y 6 pasan a cubrir trabajos y registro de operaciones.
- Corregido: `SubmitDocument` comparaba el contenido con la última versión subida y no con la vigente; tras cancelar o fallar un trabajo, volver a subir lo mismo no hacía nada.
- Un documento sin texto indexable falla de forma permanente (`dead`).
- `ingest`: `PlainTextExtractor`, `MarkdownExtractor` y `HeadingChunker`, registrados por entry point. `glosa_app check` los descubre.
- `World` pasa a `glosa_core.testing_world`, reutilizable por otros paquetes.
- ADRs 0025 y 0026.

### v0.4.2
- Puertos nuevos: `CollectionRepository`, `IdGenerator`; `AccessRepository` ampliado (miembros y consulta de tokens); `JobQueue.find_by_key`; `DocumentRepository.update_status`. Los métodos de `DocumentRepository` reciben siempre `collection_id`.
- `Collection.settings` pasa a ser `CollectionSettings`; `Job` gana el campo `version`.
- Casos de uso implementados en `core`: `CreateCollection`, `IssueToken`, `RevokeToken`, `SubmitDocument`, `SearchCollection`, `ReadDocument`, `ListDocuments`, `HandleIngest` (ingest y modify) y `ProcessNextJob`.
- Dobles en memoria de todos los puertos y pruebas de contrato de la cola, reutilizables por los adaptadores reales.
- Las 14 pruebas obligatorias de §14 tienen test (alcance parcial en 1, 4 y 6 hasta que existan los casos de uso de consulta de trabajos y registro).
- Nuevo `docs/PENDIENTE.md`: lista viva de lo que falta.
- ADRs 0022 a 0024.

### v0.4.1
- El proyecto pasa a llamarse **Glosa**. Paquetes `glosa-*` (módulos `glosa_*`), variables `GLOSA_*`, prefijo de token `glosa_` y grupo de entry points `glosa.adapters`.
- Nuevo `Dockerfile` multietapa y `docker-compose.yml` con los servicios `check` y `tests` operativos y `api`, `mcp` y `worker` definidos como pendientes (§17).
- Nueva orden `python -m glosa_app check` y puntos de entrada pendientes en los tres adaptadores.
- ADRs 0020 y 0021.

### v0.4
- Nuevo paquete `templates`: plantillas YAML con herencia (`didactico` → `profesional` → cliente), esquema estricto, guardia de producción y registro de adaptadores por nombre (§18).
- Los invariantes de seguridad no son configurables: no existen en el esquema.
- Modelo de despliegue por defecto: una instalación por cliente, con la plantilla elegida por `GLOSA_TEMPLATE`.
- Modelo de licencia: PolyForm Small Business 1.0.0 más licencia comercial, CLA para contribuciones y aportación voluntaria (§19).
- Nuevos ficheros: `LICENSE`, `LICENSE-COMERCIAL.md`, `CLA.md`, `CONTRIBUTING.md`, `docs/licencias-dependencias.md`, `.github/FUNDING.yml`.
- ADRs 0014 a 0019.

### v0.3
- Nuevo puerto `JobQueue` y entrada `worker`: las escrituras se encolan, con estados, reintentos, cola de fallidos, idempotencia, orden por colección y equidad entre colecciones.
- Nuevo `OperationLog` solo de añadir, con `correlation_id` de extremo a extremo y encadenado de hashes opcional. Sustituye a `AuditLog`.
- Auditoría y trazas didácticas pasan a ser vistas del registro.
- Documentos con versiones; solo la vigente está indexada; historial consultable.
- Ajustes de privacidad y retención por colección (`query_logging`, `retention_days`, `version_retention`, `hash_chain`).
- Nuevos endpoints de trabajos, historial, operaciones, verificación y trazas. Las escrituras responden `202`.
- Pruebas obligatorias ampliadas de 6 a 14.
- ADRs 0010 a 0013.
- `docs/` pasa a la raíz del repositorio, compartida por backend y frontend.

### v0.2
- División en backend y frontend; el frontend consume solo la API pública.
- Dos puertas de entrada al mismo núcleo: `http-api` y `mcp-server`.
- Modelo de permisos: roles de usuario, scopes de token, revocación, auditoría.
- Contrato `openapi.yaml` como fuente de verdad.
- MCP de solo lectura en las primeras versiones, con nota sobre inyección de prompts.

### v0.1
- Borrador inicial con estructura de paquetes, dominio, puertos y capa didáctica.

## 22. Decisiones iniciales (ADRs a redactar)

| ADR  | Decisión                                                        | Motivo                                                          |
|------|-----------------------------------------------------------------|-----------------------------------------------------------------|
| 0001 | Monorepo de paquetes en el backend                              | Reutilización y separación clara                                |
| 0002 | Puertos y adaptadores con `Protocol`                            | Intercambiar piezas sin tocar el dominio                        |
| 0003 | SQLite FTS5 como primer índice                                  | Cero dependencias; suficiente para texto estructurado           |
| 0004 | Servidor MCP único multitenant con token                        | Un despliegue sirve a todas las colecciones                     |
| 0005 | Capa didáctica como lectura del registro                        | Explicar sin acoplar                                            |
| 0006 | Ingesta asíncrona con estados                                   | La subida no se bloquea por documentos grandes                  |
| 0007 | Frontend y backend separados, contrato OpenAPI                  | El backend es reutilizable con cualquier cliente                |
| 0008 | Autorización única en `core` para API y MCP                     | Una sola fuente de verdad de permisos                           |
| 0009 | MCP de solo lectura por defecto                                 | Reduce el riesgo de inyección de prompts y de borrados accidentales |
| 0010 | Cola de trabajos con entrega al menos una vez y manejadores idempotentes | Simplicidad y robustez frente a caídas                 |
| 0011 | Lecturas síncronas, escrituras por cola                         | Latencia baja para el LLM; orden y control en los cambios       |
| 0012 | `OperationLog` único, solo de añadir, con `correlation_id`      | Una sola fuente de verdad para auditoría, trazas y depuración   |
| 0013 | Versionado inmutable de documentos                              | Trazabilidad de modificaciones y posibilidad de restaurar       |
| 0014 | Plantillas YAML con herencia (`didactico`, `profesional`, cliente) | Adaptar a cada cliente sin tocar código                      |
| 0015 | Las plantillas no pueden configurar los invariantes de seguridad | Una plantilla nunca debilita el aislamiento, la autorización ni el registro |
| 0016 | Guardia de producción y secretos por variables de entorno       | Evitar que una configuración de demo llegue a producción        |
| 0017 | Adaptadores como plugins registrados por nombre                 | Casos especiales sin bifurcar el núcleo                         |
| 0018 | Una instalación por cliente; plantillas de cliente en repositorio privado | Aislamiento y núcleo genérico                         |
| 0019 | Código disponible: PolyForm Small Business más licencia comercial y CLA | Gratis para pequeños, de pago para empresas, con derecho a relicenciar |
| 0020 | Nombre del proyecto: Glosa                                      | Corto, castizo y describe la capa didáctica; sin producto de RAG/MCP con ese nombre en las búsquedas hechas. Pendientes marca y dominios |
| 0021 | Imagen Docker multietapa, usuario sin privilegios y sin secretos | Imagen pequeña y segura; la configuración entra por entorno y volúmenes |
| 0022 | Los casos de uso reciben un `RequestContext` y registran su propio resultado | Una sola forma de autorizar y de dejar rastro, igual para API, MCP y worker |
| 0023 | Fragmentos con identificador determinista y limpieza previa al indexar | Reintentos y caídas del worker no dejan fragmentos duplicados ni huérfanos |
| 0024 | Pruebas de contrato para los adaptadores de la cola                | Cualquier cola (memoria, SQLite, Postgres) debe cumplir las mismas garantías |
| 0025 | Chunker por encabezados con la ruta de encabezados en cada fragmento | Poder citar la procedencia y buscar por el título de una sección |
| 0026 | Los adaptadores se descubren por entry points del grupo `glosa.adapters` | Añadir adaptadores sin tocar la composición ni bifurcar el núcleo |
| 0027 | El contenido de los archivos vive dentro de SQLite                  | Atomicidad con la transacción y una sola copia de seguridad; cambiar a disco es cambiar un adaptador |
| 0028 | Puerto `UnitOfWork`: las escrituras relacionadas se confirman juntas | Cumplir la atomicidad de §9.4 sin que el dominio conozca SQLite |
| 0029 | Consulta de texto: palabras entre comillas unidas con OR, orden por bm25 | La entrada del usuario no se interpreta como sintaxis de FTS5 y gana recall |
| 0030 | Los tests de `core` se ejecutan también contra los adaptadores reales | Una sola batería valida dobles y adaptadores; las pruebas obligatorias cubren ambos |
| 0031 | La composición construye el sistema desde la plantilla y se niega a arrancar si es insegura o incompleta | Un despliegue mal configurado falla al arrancar, no en producción |
| 0032 | El worker es un bucle sin lógica de negocio: reintentos y `dead` viven en `core` | El adaptador es intercambiable y la política de reintentos se prueba sin procesos |
| 0033 | Actor y canal `system` para eventos sin persona, sin ningún permiso | El arranque queda en el registro sin dar permisos a nadie |
| 0034 | El paquete `retrieval` se pospone hasta que existan varias estrategias de búsqueda | Hoy solo hay una (texto) y una abstracción con una sola implementación no aporta nada |

## 23. Glosario

- **RAG:** técnica que recupera fragmentos relevantes y los añade al prompt antes de generar la respuesta.
- **MCP:** protocolo estándar para que un modelo use herramientas y fuentes de datos externas.
- **Chunk (fragmento):** trozo de un documento que se indexa y se recupera por separado.
- **Embedding:** representación numérica del significado de un texto para buscar por similitud.
- **FTS5:** búsqueda de texto completo integrada en SQLite.
- **Búsqueda híbrida:** combina búsqueda por texto y búsqueda vectorial.
- **Reranker:** modelo que reordena los resultados iniciales según su relevancia real.
- **Multitenancy:** varios usuarios comparten el sistema con datos totalmente aislados.
- **Scope:** permiso concreto que lleva un token (por ejemplo `read`).
- **Job (trabajo):** unidad de trabajo encolada que ejecuta el worker.
- **Worker:** proceso que consume la cola y ejecuta los trabajos.
- **Lease:** posesión temporal de un trabajo por parte de un worker; si caduca, el trabajo se reasigna.
- **Idempotencia:** ejecutar una operación varias veces produce el mismo resultado que ejecutarla una.
- **Cola de fallidos (`dead`):** trabajos que agotaron sus reintentos y esperan revisión.
- **Correlation ID:** identificador que une todos los pasos de una misma operación.
- **Registro de solo añadir:** registro en el que las entradas nunca se editan ni se borran.
- **Encadenado de hashes:** cada entrada incluye el hash de la anterior, de modo que alterar una invalida las siguientes.
- **OpenAPI:** formato estándar para describir una API HTTP y generar clientes automáticamente.
- **OAuth 2.1 / OIDC:** estándares de autorización y de identidad para acceso delegado.
- **Inyección de prompts:** texto malicioso dentro de un documento que intenta dar órdenes al modelo que lo lee.
- **Puerto / adaptador:** interfaz definida por el dominio / implementación concreta que la cumple.
- **Plantilla:** fichero YAML que adapta el sistema a un cliente o proyecto eligiendo adaptadores y ajustes.
- **Preset:** plantilla incluida en el proyecto (`didactico`, `profesional`) de la que heredan las de cliente.
- **Guardia de producción:** comprobación al arrancar que impide usar en producción una configuración de demo.
- **Registro de adaptadores:** tabla de adaptadores disponibles por nombre; permite añadir los de un cliente como plugins.
- **Código disponible (source-available):** el código es público, pero la licencia limita quién puede usarlo gratis; no es open source en sentido estricto.
- **PolyForm Small Business:** licencia que permite el uso gratuito a organizaciones por debajo de un tamaño e ingresos concretos.
- **Licencia comercial:** contrato de pago para quien no cumple los límites de la licencia pública.
- **CLA:** acuerdo por el que quien contribuye concede al titular los derechos necesarios para relicenciar su código.
- **Glosa:** nombre del proyecto. Anotación que explica un texto, como la capa didáctica explica cómo funciona el sistema.
- **Front matter:** bloque de metadatos YAML al principio de un documento Markdown, entre líneas `---`. No es contenido y se retira al extraer el texto.
- **Ruta de encabezados:** cadena de títulos que contienen a un fragmento (`Contrato > Pagos`); permite citar de dónde viene.
- **Entry point:** mecanismo de Python por el que un paquete instalado anuncia sus adaptadores sin que nadie los importe a mano.
- **Unidad de trabajo (`UnitOfWork`):** agrupa varias escrituras en una transacción: se confirman juntas o no se confirma ninguna.
- **WAL:** modo de SQLite en el que las lecturas no bloquean a la escritura.
- **bm25:** función de relevancia de FTS5 que ordena los resultados por lo bien que encajan con la consulta.
- **Migración:** cambio numerado del esquema de la base de datos; las ya aplicadas nunca se modifican.
- **Traza:** el conjunto de entradas del registro que comparten un `correlation_id`, presentado paso a paso, de la petición al resultado.
- **Huella de la plantilla:** resumen criptográfico de la plantilla ya resuelta; queda en el registro al arrancar para saber con qué configuración se trabajó.
- **Actor del sistema:** el propio sistema (arranque, tareas internas); deja constancia en el registro pero no tiene ningún permiso.
