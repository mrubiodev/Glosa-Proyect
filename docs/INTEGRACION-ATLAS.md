# Integración con ATLAS: contratos y problemas por resolver

> **Alcance.** Documento **específico de ATLAS**; fuera del perfil neutral de la [Issue #1](https://github.com/mrubiodev/Glosa-Proyect/issues/1) ([matriz](ISSUE-1-ACEPTACION.md)). Describe lo que Glosa **ofrece y necesita** y lo que **propone**. **No describe contratos que existan:** no hay endpoints inventados, ni operaciones supuestas, ni autorización simulada con un booleano.
>
> **Revisado el 2026-11-09** tras leer la Issue #1 y recibir un informe externo sobre ATLAS. El contrato por defecto lo **posee Glosa** y el consumidor envía sus cambios; la validación documental de los candidatos es del consumidor.

## 1. Qué se ha verificado y qué no

| Fuente | Estado |
|---|---|
| Issue #1 de Glosa | **Leída directamente** (repositorio público) |
| Repositorio de ATLAS (issues #50, #52, #53, #67 y su documentación) | **No accesible desde este entorno** (responde *404*: privado). **No verificado por mí** |
| Informe externo sobre ATLAS (otra IA, 2026-11-09) | Afirmaciones sobre ATLAS recogidas en el apartado 2 como **declaradas, no verificadas** |

Una issue abierta no significa que su trabajo no esté hecho, ni una cerrada que esté aceptado: eso exige revisar las evidencias.

## 2. Lo declarado sobre ATLAS (no verificado por mí)

- **#67 (cerrada)** fija la dirección: ATLAS es autoridad de identidad, ACL, recursos originales, versiones y auditoría; Glosa puede ser un **proveedor externo de recuperación documental**; sus índices son **derivados**; ATLAS conserva FTS5, *Vault* y grafo; los resultados son **evidencias o candidatos**, no hechos incorporados a la memoria; los proveedores son opcionales y sustituibles.
- **Tres bloqueos declarados en #67:** (1) no hay un protocolo completo para calcular el **ámbito autorizado antes de consultar** al proveedor; (2) el sistema de eventos **no garantiza** todas las revocaciones, borrados e invalidaciones; (3) no hay mecanismo completo de **sincronización, reconciliación y recuperación de cursores**. Define la dirección, pero **no autoriza todavía una integración funcional segura**.
- **#50:** inventario de interfaces y capacidades, documental. **#52:** mejoras de observabilidad y versiones, con pruebas locales. **#53:** integración con el *Core* real, **no acreditada**.
- **Hallazgo del observador:** `events_poll` no sirve como observación automática de solo lectura, porque puede **crear de forma persistente un consumidor** en el *Core*; la corrección publicada lo bloquea. Se distingue *PASS contractual/local*, *integración HTTP real: no probada* e *identidad independiente del Core: sin verificar*.

**Implicación para Glosa** (si se confirma): la sincronización **no puede depender de un registro de eventos sin garantías**, y que ATLAS calcule el ámbito antes de consultar y trate los resultados como candidatos coincide con que [la validación documental sea del consumidor](adr/0038-glosa-no-da-por-autorizado-un-resultado-por-habers.md).

## 3. Matriz de contratos

*Posee:* quién define y mantiene el contrato. *Lado ATLAS:* **lo declarado, sin verificar**. Ninguno está implementado ni verificado en ambas partes.

| | Contrato | Posee | Lado Glosa | Lado ATLAS (declarado) |
|---|---|---|---|---|
| **K1** | Versión de contrato y descubrimiento de capacidades | Glosa | **Parcial:** `/v1` previsto; sin descubrimiento ni contrato MCP | #52 declara mejoras de observabilidad y versiones |
| **K2** | Consulta: procedencia, puntuación, estrategia, límites, errores, respuestas parciales | Glosa | **Parcial:** documento y versión locales, puntuación y estrategia; faltan origen, hash, ubicación y correlación | Trata los resultados como candidatos |
| **K3** | Lectura de un documento y de una versión | Glosa | **Parcial:** `ReadDocument` en el núcleo; sin API ni MCP | — |
| **K4** | **Sincronización:** alta o actualización de versión, retirada, borrado y reindexación, con *namespace*, identificador, versión, hash e idempotencia | Glosa | **Pendiente** (no existen retirada, borrado ni reindexación) | Sin mecanismo completo de sincronización ni cursores (bloqueo 3) |
| **K5** | Credenciales de integración: mínimo privilegio, revocables, acotadas | Glosa | **Parcial:** tokens por colección con *scopes*; falta la clase de operación y el modo gobernado | Sin verificar |
| **K6** | Ámbito autorizado o contexto delegado, **solo si validable de extremo a extremo** (opcional) | Consumidor emite, Glosa valida | **Pendiente** | Sin protocolo completo para calcular el ámbito (bloqueo 1) |
| **K7** | Validación de los candidatos contra la ACL | **Consumidor** | No aplica: Glosa aporta la procedencia | Dirección declarada en #67 |
| **K8** | Correlación y evidencias de lo que hizo Glosa | Glosa | **Parcial:** registro encadenado y trazas; el `correlation_id` no viaja en el resultado | Sin verificar |
| **K9** | Estado y salud de los componentes | Glosa | **Pendiente:** sin *health* ni métricas | #52 declara observabilidad |

## 4. Invariantes

| | Invariante |
|---|---|
| **I1** | En una colección gobernada, un resultado **no se trata como autorizado** por haberlo estado al indexarse. La validación documental es del consumidor; Glosa garantiza retirada efectiva, aislamiento por colección y sus credenciales |
| **I2** | **Falla cerrada:** si Glosa no puede validar la credencial o el alcance, no sirve nada |
| **I3** | Todo fragmento servido referencia *namespace* y documento de origen, y versión |
| **I4** | Un derivado solo se reconstruye volviendo al contenido del origen, mientras siga disponible y autorizado |
| **I5** | Aplicar dos veces la misma entrada de sincronización deja el mismo estado |
| **I6** | Las entradas de un documento se aplican en orden por versión, o se detecta el hueco y se reconcilia |
| **I7** | La obsolescencia posible tiene un **límite explícito y medible** |

## 5. Problemas por resolver

Ninguna recomendación es una decisión: dependen de lo que el consumidor ofrezca de verdad.

- **Identidad estable.** Riesgo: la misma persona con identificadores distintos. Exige tratar el identificador del consumidor como opaco y estable. Prueba: mismo sujeto, mismo actor en toda operación.
- **Autenticación entre sistemas.** Riesgo: suplantar al consumidor para inyectar contenido. Provisional: credenciales de integración **de Glosa**, de mínimo privilegio, con rotación y revocables; nunca un secreto en una plantilla. Prueba: rechazo de credenciales caducadas, revocadas y manipuladas.
- **Transporte.** Provisional: petición y respuesta sobre un contrato versionado de Glosa; el consumidor decide si envía al instante o por lotes. Exige límites y *timeouts* (hoy no existen).
- **Versionado de contratos.** Versión explícita, descubrimiento de capacidades y fallo claro ante una versión no soportada. Prueba: contrato contra la versión actual y la anterior.
- **Procedencia.** `SourceRef` en documento, versión, fragmento y resultado, y `DerivationInfo`. Prueba: de cualquier resultado se llega al documento y la versión de origen; un derivado sin procedencia se rechaza.
- **Revocaciones y cambios de permisos** (el riesgo más grave: un índice sirviendo lo no autorizado). Reparto según el [ADR 0038](adr/0038-glosa-no-da-por-autorizado-un-resultado-por-habers.md): el **consumidor** conserva la ACL y valida los candidatos (puede enviar un ámbito autorizado antes de consultar, K6); **Glosa** garantiza retirada efectiva, aislamiento, credenciales revocables y falla cerrada. Dos patrones para el ámbito: (1) el consumidor lo calcula y lo envía, que es la dirección declarada en #67 y exige que Glosa lo **valide de extremo a extremo**, porque la Issue #1 prohíbe aceptar como prueba un identificador de colección, un filtro o un claim arbitrario; (2) el consumidor valida después los candidatos. Descartado como base: que Glosa pregunte al origen por cada resultado o guarde la ACL. Pruebas: revocar entre dos consultas; ámbito manipulado o caducado; consumidor inalcanzable.
- **Borrados y *tombstones*.** Un documento borrado no debe seguir vivo ni resucitar con una entrada atrasada. Glosa conserva un *tombstone* y elimina los fragmentos. Pendiente previo: no existe `DeleteDocument`. Pruebas: borrar y luego recibir un alta antigua; borrar durante una ingesta.
- **Sincronización y cursores.** Si el consumidor obtiene sus cambios de un registro de eventos, **el cursor es suyo**; Glosa ofrece operaciones **idempotentes** con identificador de operación. Pruebas: repetir una entrada; entradas desordenadas por versión.
- **Reconciliación.** Glosa puede **entregar un inventario** (referencias, versiones, huellas, estados) para que el consumidor lo compare con el suyo; lo que sobra se retira y lo que falta se reenvía. Prueba: introducir una diferencia a propósito.
- **Reindexación** ([ADR 0036](adr/0036-los-indices-son-derivados-y-reconstruibles.md)). Reconstruir desde el contenido, por versión de derivado, sin mezclar índices incompatibles; un índice se activa cuando está completo. Pruebas: reindexar con una consulta en curso o con un documento retirado entre medias.
- **Duplicados.** La identidad es el par *namespace* e identificador de origen, no el contenido; misma referencia y versión es idempotente.
- **Fallos parciales.** Lo que ya hace el worker (atomicidad por documento, reintentos, fallo definitivo con razón), más no servir un documento hasta que esté completo.
- **Consistencia eventual.** Declarar y medir la ventana de obsolescencia. Nunca puede significar servir lo retirado: la retirada efectiva es inmediata en Glosa.
- **Recuperación tras interrupciones.** Gran parte **ya existe y está probada** (trabajos con *lease*, ingestas idempotentes, fragmentos con identificador determinista, atomicidad). Lo nuevo son las entradas de sincronización idempotentes y la reconciliación.

## 6. Cómo se prueba sin el consumidor

Se escriben **pruebas de contrato** contra un **doble** identificado como tal. Un doble prueba que Glosa cumple *su* parte, **no que el consumidor cumpla la suya**, y **no es una prueba de integración**. Las pruebas reales (autorización, revocación, consistencia, fallos, extremo a extremo) esperan a que los contratos existan e estén implementados en **ambos** proyectos.

## 7. Preguntas que hay que responder con ATLAS

1. ¿Qué *namespace* e identificador de origen usará? ¿Las versiones son inmutables y hay hash del contenido?
2. ¿Cómo calculará el ámbito autorizado antes de consultar y cómo será **validable** por Glosa (firma, emisor, caducidad, alcance)?
3. ¿Validará él los candidatos? ¿Qué procedencia necesita?
4. ¿Qué garantías ofrecerá su registro de eventos (orden, entrega, repetidos)? ¿Borrados y revocaciones son eventos?
5. ¿Qué semántica tienen los borrados?
6. ¿Qué transporte y qué autenticación entre sistemas están previstos?
7. ¿Cómo se versionan los contratos y se descubren las capacidades?
8. ¿Qué evidencias de auditoría espera de Glosa?

## 8. Lo que no se hará

No crear endpoints ni operaciones de ATLAS que no existan; no inventar contratos a partir de nombres; no simular una autorización con un booleano local; no presentar un doble como prueba de integración; no crear una dependencia obligatoria con ATLAS (R10); no modificar nada de ATLAS.
