# Glosa y ATLAS: reparto de autoridad

> Estado: **diseño propuesto, no implementado.** Este documento fija la visión y las reglas. Salvo que se indique lo contrario, lo que describe **no existe todavía en el código**. Estado real de lo implementado: [`AUDITORIA.md`](AUDITORIA.md).

## En una frase

**Glosa procesa y recupera conocimiento documental. ATLAS gobierna el conocimiento, su contexto y quién puede acceder a él.**

Son dos sistemas independientes que deben poder trabajar juntos mediante contratos explícitos, sin duplicar información, autoridad ni funcionalidades. Cada uno debe poder funcionar por sí solo.

## Qué hace cada uno

| Responsabilidad | ATLAS | Glosa |
|---|---|---|
| Documentos originales y vault | Autoridad | Consume; no los duplica como fuente de verdad |
| Versiones de los documentos | Autoridad | Guarda su referencia |
| Identidad de usuarios y agentes | Autoridad | Consume un contexto autorizado |
| ACL y permisos | Autoridad | Aplica las restricciones recibidas |
| Auditoría global | Autoridad | Aporta evidencias |
| Procedencia | Fuente de verdad | Conserva referencias y evidencias |
| Relaciones globales entre entidades | Autoridad | Puede aportar relaciones derivadas |
| Ingesta y extracción | Puede coordinar | **Responsable** |
| Normalización, chunking y metadatos derivados | No es su función principal | **Responsable** |
| Embeddings e índices (léxicos y vectoriales) | No es su función principal | **Responsable** |
| Recuperación y construcción de contexto (RAG) | No es su función principal | **Responsable** |
| MCP documental | Puede coordinar | **Responsable** |

Glosa **no** es un repositorio de memoria, ni un framework genérico de IA, ni (en una colección gobernada) un sistema de identidad. Su especialización es el conocimiento documental.

## Reglas obligatorias

Se citan como R1 a R10 en el resto de la documentación.

| | Regla | Dónde aplica |
|---|---|---|
| **R1** | Glosa no crea una segunda fuente de verdad documental | Colecciones gobernadas |
| **R2** | Glosa no modifica los documentos originales del sistema de origen | Colecciones gobernadas |
| **R3** | Glosa no implementa una identidad propia que compita con la de ATLAS | Colecciones gobernadas |
| **R4** | Glosa no es autoridad de permisos | Colecciones gobernadas |
| **R5** | Un agente no accede a nada que ATLAS no autorice | Colecciones gobernadas |
| **R6** | Los índices son derivados y reconstruibles | Todas |
| **R7** | El contenido indexado conserva su procedencia | Todas |
| **R8** | Las referencias permiten identificar el documento y la versión de origen | Todas |
| **R9** | Las decisiones de autorización proceden de ATLAS cuando la información está gobernada por ATLAS | Colecciones gobernadas |
| **R10** | Glosa puede trabajar con fuentes independientes, sin obligar a instalar ATLAS | Todas |

## Cómo conviven R1–R5 con R10: autoridad por colección

Hoy Glosa **es** la autoridad de todo lo que R1–R5 le prohíben ser: guarda el contenido original y sus versiones (ADR 0027), tiene sus propios usuarios, roles y tokens, y su propio registro de auditoría. Leídas al pie de la letra, esas reglas chocan con R10.

La forma de resolverlo, **propuesta y pendiente de confirmar** ([ADR 0035](adr/0035-autoridad-por-coleccion-modo-propio-o-modo-goberna.md)), es que la autoridad se decide **por colección**:

| Aspecto | Modo propio (lo que hay hoy) | Modo gobernado (propuesto) |
|---|---|---|
| Documento original | Glosa lo guarda y es su autoridad | Glosa no lo guarda como fuente de verdad: lo obtiene del sistema de origen por referencia y versión. Solo conserva copias derivadas (el texto de los fragmentos) |
| Versiones | Las numera Glosa | Las define el sistema de origen; Glosa guarda su referencia |
| Identidad | Usuarios y tokens de Glosa | Contexto autorizado emitido por el sistema de origen; Glosa no mantiene usuarios ni roles para esa colección |
| Permisos | Roles y scopes de Glosa | Decisión del sistema de origen. Glosa aplica las restricciones recibidas y **vuelve a comprobar al consultar** |
| Auditoría | El registro de Glosa es la auditoría de la colección | El registro de Glosa es una **evidencia que se aporta**; la auditoría global es del sistema de origen |
| Índices | Derivados del contenido propio | Derivados; solo se reconstruyen mientras el sistema de origen siga autorizando el contenido |
| Revocación y borrado | `RevokeToken` inmediato; borrado de documento pendiente | Las revocaciones y *tombstones* del origen retiran los derivados; la consulta **falla cerrada** si no puede confirmar la autorización |

Reglas de convivencia:

- **M1.** El modo se fija al crear la colección y no cambia.
- **M2.** No hay conversión silenciosa: pasar de un modo a otro sería una migración explícita y auditada.
- **M3.** En modo gobernado, ningún caso de uso crea usuarios, roles ni tokens locales para esa colección.
- **M4.** No existe modo mixto en esta versión: ni permisos locales que amplíen los del origen, ni tokens locales que los estrechen.
- **M5.** El código común (ingesta, extracción, chunking, indexación, recuperación) **no conoce el modo**. El modo solo cambia de dónde vienen el contenido y las decisiones de autorización, y eso se expresa con puertos, no con condicionales repartidos.

## Qué conserva Glosa en modo gobernado

Solo datos **derivados y reconstruibles**, siempre con su procedencia: fragmentos, embeddings, índices, metadatos derivados, referencias al origen y evidencias de lo que hizo. Si el sistema de origen deja de autorizar un documento, el derivado debe desaparecer o dejar de servirse, y reconstruirlo solo puede hacerse volviendo al origen.

## Diseño propuesto (nada de esto existe en el código)

| Pieza | Para qué |
|---|---|
| `Collection.origin` (`own` o `governed`) y el identificador del sistema de origen | Fijar el modo de cada colección |
| `SourceRef` (sistema de origen, referencia del documento, versión de origen) | Procedencia: R7 y R8. Iría en documento, versión, fragmento y resultados |
| `AuthorizedContext` | El contexto de autorización que llega del sistema de origen, verificable y con caducidad |
| Puerto `DocumentSource` | Obtener el contenido autorizado de una versión concreta |
| Puerto `AuthorizationProvider` | Preguntar al origen si un conjunto de referencias sigue autorizado |
| Puerto `ChangeFeed` | Recibir altas, cambios, borrados y revocaciones, con cursor |
| `DerivationInfo` | Registrar con qué extractor, chunker y modelo se generó cada derivado, para reconstruir de forma selectiva (R6) |

Todos son **puertos** en el sentido de la arquitectura de Glosa: en modo propio los implementa el propio Glosa y en modo gobernado un adaptador hacia el sistema de origen. Que un adaptador de ATLAS exista, y con qué forma, depende de que ATLAS tenga los contratos correspondientes; ver [`INTEGRACION-ATLAS.md`](INTEGRACION-ATLAS.md). **No se inventa ningún contrato mientras tanto.**

## Decisiones y documentos relacionados

- ADRs: [0035](adr/0035-autoridad-por-coleccion-modo-propio-o-modo-goberna.md) (autoridad por colección), [0036](adr/0036-los-indices-son-derivados-y-reconstruibles.md) (índices derivados), [0037](adr/0037-la-integracion-con-atlas-se-hace-por-contratos-exp.md) (contratos explícitos), [0038](adr/0038-en-modo-gobernado-la-autorizacion-se-vuelve-a-comp.md) (re-comprobación al consultar), [0039](adr/0039-rag-en-glosa-es-recuperacion-y-contexto-con-eviden.md) (alcance del RAG).
- Contratos y problemas por resolver: [`INTEGRACION-ATLAS.md`](INTEGRACION-ATLAS.md).
- Estado real y brechas: [`AUDITORIA.md`](AUDITORIA.md).
- Fases y trabajo: [`HOJA-DE-RUTA.md`](HOJA-DE-RUTA.md).
