# Glosa y ATLAS: reparto de autoridad

> **Alcance.** Trata un consumidor concreto, ATLAS, y por eso **queda fuera del perfil neutral** que pide la [Issue #1](https://github.com/mrubiodev/Glosa-Proyect/issues/1) ([matriz de aceptación](ISSUE-1-ACEPTACION.md)). El perfil neutral será un documento aparte (G-100 y G-101).
>
> **Estado: diseño propuesto, no implementado.** Revisado el 2026-11-09 tras leer la Issue #1: se corrigieron el modelo de autoridad de Glosa y las reglas M3 y M4. Lo implementado: [`AUDITORIA.md`](AUDITORIA.md).

## En una frase

**Glosa procesa y recupera conocimiento documental. ATLAS gobierna el conocimiento, su contexto y quién puede acceder a él.**

Dos sistemas independientes que deben poder trabajar juntos mediante contratos explícitos, sin duplicar información, autoridad ni funcionalidades. Cada uno funciona por sí solo.

## Qué hace cada uno

| Responsabilidad | ATLAS | Glosa |
|---|---|---|
| Documentos originales y vault | Autoridad | Puede guardar **copias y derivados** de lo que ingiere; no es fuente de verdad del original |
| Versiones del original | Autoridad | Guarda la referencia y las versiones que ingiere |
| Identidad de usuarios y agentes | Autoridad | Solo emite **credenciales de integración** |
| ACL y permisos sobre los documentos | Autoridad | Aplica sus **propias barreras**; no copia la ACL |
| Auditoría global | Autoridad | Aporta evidencias de lo que hizo |
| Procedencia | Fuente de verdad | Conserva referencias y evidencias |
| Ingesta, extracción, chunking, metadatos derivados, embeddings, índices | No es su función principal | **Responsable** |
| Recuperación y construcción de contexto | No es su función principal | **Responsable** |
| Validación documental de los candidatos recuperados | **Responsable** | Aporta la procedencia necesaria |
| MCP documental | Puede coordinar | **Responsable** |

Glosa **no** es un repositorio de memoria ni un framework genérico de IA.

## Reglas obligatorias (R1 a R10)

| | Regla | Dónde aplica |
|---|---|---|
| **R1** | Glosa no es fuente de verdad del documento original del consumidor: puede guardar copias y derivados, nunca presentarlos como el original | Gobernadas |
| **R2** | Glosa no modifica los documentos originales del consumidor | Gobernadas |
| **R3** | Glosa no gestiona la identidad de las personas y agentes del consumidor; solo emite credenciales de integración | Gobernadas |
| **R4** | Glosa no es autoridad de la ACL del consumidor, pero **aplica siempre sus propias barreras** | Gobernadas |
| **R5** | Un agente no accede a nada que el consumidor no autorice | Gobernadas |
| **R6** | Los índices son derivados y reconstruibles | Todas |
| **R7** | El contenido indexado conserva su procedencia | Todas |
| **R8** | Las referencias permiten identificar el documento y la versión de origen | Todas |
| **R9** | Las decisiones de autorización sobre los documentos proceden del consumidor cuando es él quien los gobierna | Gobernadas |
| **R10** | Glosa puede trabajar con fuentes independientes, sin obligar a instalar ATLAS | Todas |

## Autoridad por colección

Hoy Glosa solo tiene un modo: es autoridad de todo en cada colección. Propuesta, **pendiente de la aprobación del propietario** ([ADR 0035](adr/0035-autoridad-por-coleccion-modo-propio-o-modo-goberna.md)):

| Aspecto | Modo propio (hoy) | Modo gobernado (propuesto) |
|---|---|---|
| Documento | Glosa lo guarda y es su autoridad | Glosa guarda la **copia que ingiere** y es autoridad sobre ella; **no** sobre el original |
| Versiones | Las numera Glosa | Las define el consumidor; Glosa guarda su referencia |
| Identidad | Usuarios y tokens de Glosa | Personas y agentes del consumidor; Glosa solo emite credenciales de integración |
| Política de acceso a cada documento | La define Glosa | La define el consumidor |
| Autorización efectiva | La de Glosa | **La intersección** de la de Glosa (credencial de mínimo privilegio) y la del consumidor |
| Auditoría | El registro de Glosa es la de la colección | El registro de Glosa es una evidencia; la global es del consumidor |
| Revocación y borrado | `RevokeToken` inmediato; borrado de documento pendiente | **Retirada efectiva** en Glosa y validación de candidatos por el consumidor ([ADR 0038](adr/0038-glosa-no-da-por-autorizado-un-resultado-por-habers.md)) |

**Doble control.** Glosa comprueba que la integración está autenticada y tiene acceso a la colección y a la clase de operación; el consumidor comprueba que el usuario o agente puede acceder a cada documento. La autorización efectiva es la **intersección** y **ninguno amplía los permisos del otro**. El control de Glosa es de **grano grueso**: si degenerase en una copia de la ACL por documento, volveríamos a duplicar la autoridad del consumidor.

Reglas de convivencia:

- **M1.** El modo se fija al crear la colección y no cambia.
- **M2.** No hay conversión silenciosa: sería una migración explícita y auditada.
- **M3.** Los tokens de integración son **tokens nativos de Glosa**: de mínimo privilegio, revocables y acotados a la colección. (Sustituye a la regla anterior, que prohibía cualquier token local y contradecía la Issue #1.)
- **M4.** La colección es la **frontera de seguridad**: no se mezclan documentos con políticas de acceso incompatibles. No hay modo mixto.
- **M5.** El código común **no conoce el modo**: solo cambia quién decide el acceso a nivel de documento, y se expresa con puertos.

## Diseño propuesto (nada de esto existe en el código)

| Pieza | Para qué |
|---|---|
| `Collection.origin` (`own` o `governed`) | Fijar el modo |
| `SourceRef` (*namespace* y identificador de origen, versión, hash) | Procedencia (R7 y R8) en documento, versión, fragmento y resultado |
| **Entradas públicas de sincronización de Glosa** | El consumidor las usa para dar de alta o actualizar una versión, retirarla, borrarla o pedir su reindexación, con idempotencia, hash y *namespace* |
| Credenciales de integración | Mínimo privilegio, revocables, acotadas a colección y clase de operación (R3, M3) |
| `DerivationInfo` | Con qué extractor, chunker y modelo se generó cada derivado (R6) |
| Contexto de autorización delegado | **Opcional**, solo si puede validarse de extremo a extremo. Nunca un claim arbitrario del cliente |

**Corrección de rumbo.** Una propuesta anterior preveía puertos para que Glosa *tirase* del contenido y de los cambios de un origen (`DocumentSource`, `ChangeFeed`) y preguntase a un `AuthorizationProvider` por cada resultado. La Issue #1 apunta a lo contrario: un contrato **que posee Glosa** y por el que el consumidor *envía* sus cambios. Esos puertos quedan como alternativa de segundo orden ([`ISSUE-1-ACEPTACION.md`](ISSUE-1-ACEPTACION.md), apartado 4).

## Relacionado

ADR [0035](adr/0035-autoridad-por-coleccion-modo-propio-o-modo-goberna.md), [0036](adr/0036-los-indices-son-derivados-y-reconstruibles.md), [0037](adr/0037-los-contratos-de-interoperabilidad-los-define-glos.md), [0038](adr/0038-glosa-no-da-por-autorizado-un-resultado-por-habers.md) y [0039](adr/0039-rag-en-glosa-es-recuperacion-y-contexto-con-eviden.md) · [`INTEGRACION-ATLAS.md`](INTEGRACION-ATLAS.md) · [`ISSUE-1-ACEPTACION.md`](ISSUE-1-ACEPTACION.md) · [`AUDITORIA.md`](AUDITORIA.md) · [`HOJA-DE-RUTA.md`](HOJA-DE-RUTA.md)
