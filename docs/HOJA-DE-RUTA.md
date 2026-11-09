# Hoja de ruta de Glosa

> Fecha: 2026-11-08 · Estrategia por fases. La lista táctica del día a día está en [`PENDIENTE.md`](PENDIENTE.md); esta es la visión de conjunto. Nada se marca como terminado porque esté documentado.
>
> Base: [`ECOSISTEMA.md`](ECOSISTEMA.md) (visión), [`AUDITORIA.md`](AUDITORIA.md) (estado real) e [`INTEGRACION-ATLAS.md`](INTEGRACION-ATLAS.md) (contratos).

## Cómo leerla

- Cada fase se divide en **issues pequeñas, verificables y con dependencias explícitas** (`G-nnn`). Son *propuestas*: ninguna issue se ha creado todavía.
- **Sin ATLAS** significa que se puede hacer y verificar solo con Glosa. **Bloqueada** significa que necesita algo de ATLAS que no se ha podido verificar.
- Cada issue indica su criterio de aceptación: sin ese criterio cumplido, no se cierra.
- No se plantea una gran implementación única: cada fase entrega algo utilizable por sí mismo.

## Resumen

| Fase | Objetivo | Estado | ¿Necesita ATLAS? |
|---|---|---|---|
| **0** Auditoría y consolidación | Saber dónde estamos y decidir lo que bloquea | **Hecha en documentos**; pendientes dos decisiones y la Issue #1 | No |
| **1** Núcleo documental | Procedencia, borrado, revalidación, límites, errores y extractores | Parcial | No |
| **2** Indexación y recuperación | *Embeddings*, índice vectorial, recuperación híbrida, filtros | No iniciada | No |
| **3** RAG | Contexto con evidencias y señal de insuficiencia | No iniciada | No |
| **4** MCP y API | Exponer las capacidades con permisos y contratos | No iniciada | No |
| **5** Preparación de la interoperabilidad | Puertos y modo gobernado, con dobles etiquetados | No iniciada | Parcial: el diseño sí, el contrato final no |
| **6** Integración real | Pruebas reales contra ATLAS | **Bloqueada** | **Sí** |

## Fase 0. Auditoría y consolidación

**Hecho:** inventario funcional y matriz de capacidades ([`AUDITORIA.md`](AUDITORIA.md)), mapa de arquitectura, brechas, riesgos, matriz de contratos ([`INTEGRACION-ATLAS.md`](INTEGRACION-ATLAS.md)), reglas R1–R10 y las decisiones propuestas (ADR 0035 a 0039).

| | Issue | Depende de | Criterio de aceptación |
|---|---|---|---|
| **G-001** | Contrastar la Issue #1 con la auditoría | Acceso al texto de la issue. **Bloqueada** | Cada criterio de la issue tiene evidencia (test o fichero) y clasificación; se cierra solo si todos la tienen |
| **G-002** | Actualizar la matriz de contratos tras revisar ATLAS #50, #52, #53 y #67 | Acceso a esas issues. **Bloqueada** | Cada fila de la matriz pasa de "sin verificar" a un estado con evidencia; las preguntas del apartado 7 de `INTEGRACION-ATLAS.md` quedan respondidas |
| **G-003** | Decidir la autoridad por colección (ADR 0035) y el alcance del RAG (ADR 0039) | Decisión del propietario | Los dos ADR pasan de "Propuesta" a "Aceptada" o se sustituyen por otro |

## Fase 1. Núcleo documental (sin ATLAS)

Cierra las brechas de la auditoría que no dependen de nadie. Orden recomendado: **G-014, G-012 y G-010 primero**, porque son las que hacen seguro el modo gobernado más adelante.

| | Issue | Depende de | Criterio de aceptación |
|---|---|---|---|
| **G-010** | **Procedencia en el dominio:** `SourceRef` (origen, referencia, versión de origen) en documento, versión, fragmento y resultado | — | Todo resultado lleva su origen; un fragmento sin procedencia se rechaza al indexar; migración de la base con datos existentes; pruebas con SQLite |
| **G-011** | **Metadatos del documento:** que `Document.metadata` y los `metadata` de la plantilla funcionen (subida, validación y consulta) | G-010 | Se pueden declarar, validar y leer; una plantilla con un campo inexistente falla al arrancar |
| **G-012** | **`DeleteDocument` y `HandleDelete`** con *tombstone* local | — | Borrar retira los fragmentos del índice y el documento deja de verse; un trabajo de alta pendiente no lo resucita; queda en el registro; prueba obligatoria nueva |
| **G-013** | **Reindexación y `DerivationInfo`:** `ReindexDocument`, `HandleReindex` y registro de con qué extractor, chunker y versión se generó cada derivado | G-010 | Reindexar reemplaza los fragmentos de una versión sin duplicar ni dejar huérfanos; se puede reindexar solo lo generado con una versión antigua; se resuelve el campo `content_ref` (usarlo o quitarlo) |
| **G-014** | **Revalidar permisos al ejecutar un trabajo** | — | Si el actor pierde el permiso entre encolar y ejecutar, el trabajo no escribe nada y queda `dead` con razón; prueba nueva contra los dobles y contra SQLite |
| **G-015** | **Límites de tiempo** en extracción, indexado y búsqueda, configurables en la plantilla | — | Un documento patológico no bloquea a un worker; el fallo es un error clasificado |
| **G-016** | **Catálogo de errores con códigos estables** y su correspondencia con los errores del dominio | — | Cada error del dominio tiene un código estable y documentado; hay una prueba que impide añadir un error sin código |
| **G-017** | **Extractores:** PDF (texto), tablas Markdown, codificaciones distintas de UTF-8 y validación del tipo declarado | — | Cada formato con pruebas, incluido el error de extracción y el contenido parcialmente procesable |
| **G-018** | **Chunker:** ubicación exacta en el original (desplazamientos), solapamiento opcional y tablas | G-017 | Cada fragmento permite volver a su lugar de origen; el solapamiento es configurable y probado |
| **G-019** | **Observabilidad:** *health*, *readiness* y contadores (cola, trabajos por estado, latencias) | — | Se puede saber si la base, la cola y los workers están vivos, y cuántos trabajos hay por estado |
| **G-020** | **Cerrar los casos de uso que faltan:** `GetDocumentHistory`, `RetryDeadJob`, `ManageMembers`, `ListCollections`, `UpdateCollectionSettings` (con la regla 6), `DeleteCollection` | Decisión sobre usuarios | Cada uno con permisos, registro y pruebas obligatorias ampliadas |

## Fase 2. Indexación y recuperación (sin ATLAS)

Se prioriza **una implementación sólida y evaluada**, no todas las estrategias por anticipado.

| | Issue | Depende de | Criterio de aceptación |
|---|---|---|---|
| **G-021** | **Evaluación:** script `eval` con `recall@k` y conjuntos de preguntas (hoy faltan `eval.yaml` y `acme-legal/eval.yaml`, que las plantillas ya referencian) | — | Se puede medir cualquier cambio de recuperación con una cifra; los ficheros referenciados existen |
| **G-022** | **Modelo de índices:** modelo, proveedor, dimensiones, versión del modelo y estado de indexación de cada índice; nunca se mezclan índices incompatibles | G-013 | Un índice declara lo que es; consultar un índice a medio construir o incompatible falla con un error claro; un índice nuevo se activa solo cuando está completo |
| **G-023** | **Adaptador de *embeddings*** local, configurable y sustituible (más `none`) | G-022 | Pruebas de contrato del puerto sin servicios externos; cambiar de modelo marca el índice anterior como obsoleto |
| **G-024** | **Índice vectorial.** Evaluar la opción antes de elegirla (ADR) | G-022, G-023 | La decisión se justifica con G-021; aislamiento por colección también en el índice vectorial |
| **G-025** | **Recuperación híbrida y filtros por metadatos** | G-011, G-021, G-024 | Mejora medible frente a solo léxica en el conjunto de G-021; si no mejora, no se mantiene |
| **G-026** | **Reranking:** decidir tras G-025. **Puede descartarse** | G-025 | Solo se implementa si G-021 demuestra una mejora que compense su coste |

## Fase 3. RAG (sin ATLAS)

Primero hay que decidir qué significa RAG en Glosa (ADR 0039): la propuesta es **recuperación + construcción de contexto con evidencias**, y que la **generación** de la respuesta la haga por defecto el modelo que consulta por MCP.

| | Issue | Depende de | Criterio de aceptación |
|---|---|---|---|
| **G-030** | **`BuildContext`:** contexto con presupuesto de tamaño, evidencias, procedencia y las limitaciones de C6 | G-010, G-025 | Cada fragmento del contexto remite a documento y versión de origen; el resultado dice cómo se recuperó |
| **G-031** | **Señal de insuficiencia:** reconocer que no hay contexto suficiente | G-030, G-021 | Una consulta sin evidencia devuelve explícitamente "sin contexto suficiente", no un contexto de relleno; el umbral se calibra con G-021 |
| **G-032** | **Generación opcional con citas.** Solo si ADR 0039 la incluye | G-030, G-031 | Toda afirmación cita un fragmento; sin evidencia, se niega a responder; se registra modelo y estrategia |

## Fase 4. API y MCP (sin ATLAS)

| | Issue | Depende de | Criterio de aceptación |
|---|---|---|---|
| **G-040** | **Decisiones previas:** framework web, SDK de MCP y creación y autenticación de usuarios | Decisión del propietario | ADR escritos; propuesta ya hecha: una API key personal con hash, como los tokens |
| **G-041** | **API de gestión** por tramos (colecciones, documentos, trabajos, tokens, operaciones, trazas) | G-016, G-020, G-040 | Cada endpoint con permisos, errores con código estable, idempotencia y `X-Correlation-Id`; el OpenAPI y la implementación no se desvían |
| **G-042** | **Servidor MCP:** `buscar`, `leer_documento` y `listar_documentos` con permisos, errores y contrato versionado | G-016, G-030, G-040 | Solo lectura por defecto; el contenido se devuelve como dato; pruebas de contrato; prueba de que un token no puede salir de su colección |

## Fase 5. Preparación de la interoperabilidad con ATLAS

El **diseño** y los puertos pueden hacerse ya; la **forma final** de los contratos depende de lo que ATLAS tenga (G-002).

| | Issue | Depende de | Criterio de aceptación |
|---|---|---|---|
| **G-050** | **Puertos `DocumentSource`, `AuthorizationProvider` y `ChangeFeed`**, con dobles **etiquetados como tales** y pruebas de contrato | G-010 | Los dobles tienen nombre y documentación que dicen que no son ATLAS; ningún endpoint ni operación inventados |
| **G-051** | **Modo gobernado:** `Collection.origin`, sin usuarios, roles ni tokens locales (M3), y el contenido original como derivado retirable | G-050, G-003 | El código común no conoce el modo (M5); una colección gobernada no puede crear permisos locales; la prueba obligatoria 1 se repite en ambos modos |
| **G-052** | **Contexto autorizado** y su verificación, con caducidad y **fallo cerrado** | G-050 | Un contexto caducado, de otro emisor o manipulado se rechaza; si no se puede verificar, no se devuelve nada (I2) |
| **G-053** | **Re-comprobación al consultar** (capa 1 de 5.6) | G-050, G-052 | Una revocación entre dos consultas surte efecto; con el origen inalcanzable, la consulta falla cerrada |
| **G-054** | **Procesador de cambios** idempotente, con cursor transaccional, *tombstones* y reconciliación | G-012, G-050 | Repetir un evento no cambia nada (I5); caída entre aplicar y guardar el cursor no pierde ni duplica; un evento atrasado no resucita un borrado |
| **G-055** | **Ventana de obsolescencia** configurable y medible | G-053, G-054, G-019 | El límite se declara en la plantilla y se muestra en la observabilidad (I7) |

## Fase 6. Integración real (bloqueada)

Solo cuando los contratos existan e estén implementados **en ambos proyectos**.

| | Issue | Depende de | Criterio de aceptación |
|---|---|---|---|
| **G-060** | Integración aislada contra ATLAS real | G-002, G-050 a G-055 y trabajo equivalente en ATLAS | Funciona en un entorno separado, sin tocar datos reales |
| **G-061** | Pruebas de contrato, de autorización y de **revocación** reales | G-060 | Una revocación real en ATLAS deja de servirse en Glosa dentro de la ventana declarada |
| **G-062** | Pruebas de consistencia, de fallos y extremo a extremo | G-060 | Las de 5.8 a 5.14 de `INTEGRACION-ATLAS.md` con el sistema real |

## Qué se puede implementar ya, sin esperar a ATLAS

Todo lo de las fases 1 a 4 y el diseño y los puertos de la fase 5. **Primer tramo recomendado**, por este orden:

1. **G-014**, revalidar permisos al ejecutar: es una brecha de seguridad que ya existe hoy (A-02).
2. **G-012**, `DeleteDocument`: sin él no se puede retirar un documento del índice por un caso de uso (A-13).
3. **G-010**, procedencia: lo necesitan casi todas las demás (R7 y R8).
4. **G-016** y **G-015**, errores con código y límites de tiempo: la API y el MCP los necesitan para no inventarlos.
5. **G-021**, evaluación: sin una cifra no se puede decidir G-024, G-025 ni G-026.

## Dependencias entre issues

```
G-010 ──► G-011 ──► G-025 ──► G-030 ──► G-031 ──► G-032
  │                    ▲        ▲
  ├──► G-013 ──► G-022 ──► G-023 ──► G-024 ──┘
  └──► G-050 ──► G-051, G-052 ──► G-053 ──┐
G-012 ─────────► G-054 ──────────────────► G-055 ──► (fase 6, bloqueada)
G-016 ──► G-041, G-042 ◄── G-040 (decisiones) ; G-021 ──► G-024, G-025, G-026, G-031
```

## Lo que esta hoja de ruta no hace

- No crea issues ni cambia ninguna: solo las propone.
- No modifica ATLAS, no despliega servicios, no toca datos remotos.
- No da por terminada ninguna fase que solo esté documentada.
