# Integración con ATLAS: contratos y problemas por resolver

> **Qué es y qué no es este documento.** Describe lo que Glosa **necesita** de ATLAS y lo que **propone**. **No describe contratos que existan.** No se ha consultado ATLAS: todo lo que figura en la columna "ATLAS" está **sin verificar**. No hay endpoints inventados, ni nombres de operaciones supuestos, ni autorización simulada con un booleano.

## 1. Lo que no se ha podido verificar

El encargo menciona el trabajo en curso de ATLAS (las issues #50, #52, #53 y #67: inventario de interfaces, observabilidad y versiones, integración con Core real y arquitectura de proveedores externos) y la Issue #1 de Glosa. **Ninguna de esas issues se ha podido consultar desde este entorno**, así que:

- No se afirma que ATLAS tenga, o no tenga, ninguno de los contratos de la tabla.
- La Issue #1 de Glosa **no se da por cerrada ni por incumplida**: queda pendiente de contrastar (ver [`AUDITORIA.md`](AUDITORIA.md), apartado 3).
- Para completar este documento hace falta el contenido de esas issues o de la documentación de contratos de ATLAS.

Las preguntas concretas que hay que responder con ellas están en el apartado 7.

## 2. Matriz de contratos

**Leyenda de estados.** *Existe*: está definido y publicado. *Propuesto*: hay un diseño, sin implementar. *Implementado*. *Verificado*: probado contra la otra parte. *Pendiente*: ni siquiera diseñado. *Sin verificar*: no se ha consultado.

| | Contrato (capacidad que Glosa necesita) | Sentido | Lado Glosa | Lado ATLAS |
|---|---|---|---|---|
| **C1** | Referencia documental estable y versión de un documento | ATLAS → Glosa | Pendiente (`SourceRef` propuesto, no implementado) | Sin verificar |
| **C2** | Obtener el contenido autorizado de una versión concreta | Glosa → ATLAS | Pendiente (puerto `DocumentSource` propuesto) | Sin verificar |
| **C3** | Identidad y contexto de autorización del consultante, verificable y con caducidad | ATLAS → Glosa | Pendiente (`AuthorizedContext` propuesto) | Sin verificar |
| **C4** | Decisión de autorización sobre un conjunto de referencias, por lotes | Glosa → ATLAS | Pendiente (puerto `AuthorizationProvider` propuesto) | Sin verificar |
| **C5** | Cambios: altas, actualizaciones, borrados, cambios de permisos y revocaciones, con cursor | ATLAS → Glosa | Pendiente (puerto `ChangeFeed` propuesto) | Sin verificar |
| **C6** | Resultado de una consulta con procedencia | Glosa → consumidor | **Parcial**: el resultado ya lleva fragmento, documento, versión, puntuación y estrategia; faltan origen, limitaciones e información de recuperación | No aplica |
| **C7** | Evidencias de auditoría de lo que hizo Glosa | Glosa → ATLAS | **Parcial**: existe el registro de operaciones con cadena de hashes; no hay exportación | Sin verificar |
| **C8** | Autenticación entre sistemas | Ambos | Pendiente | Sin verificar |
| **C9** | Versionado de contratos y descubrimiento de capacidades | Ambos | **Parcial**: OpenAPI con `/v1` previsto; sin contrato de MCP ni de intercambio | Sin verificar |
| **C10** | Estado y salud de los componentes | Ambos | Pendiente (no hay *health* ni métricas) | Sin verificar |

Ninguno está *implementado* ni *verificado* por ninguna de las dos partes. Esta matriz se actualiza cuando se consulte ATLAS; cada cambio de estado exige evidencia.

## 3. Contenido conceptual de cada contrato

Son **requisitos mínimos de información**, no formatos ni operaciones. Los nombres de campo son provisionales.

- **C1, referencia documental.** Sistema de origen; referencia del documento, opaca y estable en el tiempo; referencia de versión (inmutable: una versión nunca cambia de contenido); tipo de contenido; título; metadatos; y, si es posible, una huella del contenido para comprobar lo recibido.
- **C2, contenido.** Dada una referencia y una versión, el contenido **solo si el contexto sigue autorizado**; si no, un error clasificable (no autorizado, no existe, borrado).
- **C3, contexto autorizado.** Quién consulta, quién lo emitió, hasta cuándo es válido y a qué alcance se refiere. Debe poder verificarse sin confiar en quien lo presenta.
- **C4, decisión por lotes.** Para varias referencias, cuáles siguen autorizadas para ese contexto. Debe poder responder "no sé" y Glosa lo tratará como "no" (ver invariante I2).
- **C5, cambios.** Eventos ordenados por documento, con un cursor para reanudar, e identificador de evento para detectar repetidos. Un borrado y una revocación son eventos de primera clase.
- **C6, resultado.** Fragmentos con puntuación, referencia al documento y su versión de origen, procedencia, cómo se recuperaron (estrategia, modelo, versión del índice) y las limitaciones relevantes (por ejemplo, "resultados incompletos por autorización no confirmada").
- **C7, evidencias.** Qué operación, quién, cuándo, sobre qué referencia, con qué resultado, de forma que ATLAS pueda incorporarlo a su auditoría sin fiarse del texto: con el encadenado de hashes ya existente.

## 4. Invariantes que debe cumplir cualquier diseño

| | Invariante |
|---|---|
| **I1** | En una colección gobernada, **nunca** se devuelve contenido sin una decisión de autorización **vigente** del sistema de origen. Haber estado autorizado cuando se indexó no basta |
| **I2** | **Falla cerrada:** si no se puede confirmar la autorización, no se devuelve el contenido |
| **I3** | Todo fragmento servido referencia sistema de origen, documento y versión |
| **I4** | Un derivado solo se reconstruye volviendo al origen, y solo si el origen sigue autorizando el contenido |
| **I5** | Aplicar dos veces el mismo evento deja el mismo estado (idempotencia) |
| **I6** | Los eventos de un mismo documento se aplican en orden, o se detecta el hueco y se reconcilia |
| **I7** | La obsolescencia posible tiene un **límite explícito y medible** (cuánto puede tardar una revocación en surtir efecto) |

## 5. Problemas por resolver

Para cada uno: qué puede salir mal, qué exige a Glosa, opciones, recomendación provisional y qué hay que probar. Ninguna recomendación es una decisión: todas dependen de lo que ATLAS ofrezca de verdad.

### 5.1 Identidad estable
- **Riesgo:** que la misma persona o agente aparezca con identificadores distintos, o que dos distintos compartan uno, y los registros de auditoría dejen de ser fiables.
- **Exige:** tratar el identificador de ATLAS como opaco y estable; no derivarlo ni normalizarlo.
- **Pruebas:** el mismo sujeto da el mismo `actor` en el registro en todas las operaciones.

### 5.2 Autenticación entre sistemas
- **Riesgo:** que alguien se haga pasar por ATLAS (para inyectar documentos o contexto) o por Glosa.
- **Opciones:** secreto compartido con rotación; autenticación mutua por certificados; credenciales de corta duración emitidas por ATLAS.
- **Recomendación provisional:** credenciales de corta duración y verificables, con rotación; nunca un secreto en una plantilla (la guardia de producción ya lo impide).
- **Pruebas:** rechazo de credenciales caducadas, de otro emisor y manipuladas.

### 5.3 Transporte
- **Opciones:** HTTP con contratos versionados; cola de mensajes; ambos (consulta síncrona y cambios asíncronos).
- **Recomendación provisional:** consulta e interrogación por petición/respuesta; cambios mediante un registro de eventos con cursor. Decidir cuando se conozca lo que ATLAS ofrece.
- **Exige:** límites y *timeouts* en toda llamada saliente (hoy no existen en Glosa).

### 5.4 Versionado de contratos
- **Riesgo:** que un cambio en ATLAS rompa a Glosa sin avisar, o al revés.
- **Exige:** versión explícita en cada contrato, descubrimiento de capacidades y fallo claro ante una versión no soportada. No se interpretan campos desconocidos como si fueran los conocidos.
- **Pruebas:** pruebas de contrato contra la versión actual y la anterior.

### 5.5 Procedencia
- **Exige:** `SourceRef` en documento, versión, fragmento y resultado (C1, C6); registrar con qué extractor, chunker y modelo se derivó cada fragmento (`DerivationInfo`).
- **Pruebas:** de cualquier resultado se llega al documento y la versión de origen; un derivado sin procedencia se rechaza al indexar.

### 5.6 Revocaciones y cambios de permisos
- **Riesgo (el más grave):** un índice derivado sigue sirviendo información que ya no está autorizada.
- **Defensa en dos capas, propuesta:**
  1. **Al consultar:** Glosa recupera más candidatos de los pedidos, pregunta al origen (C4) por los documentos distintos que aparecen y descarta los no autorizados. Puede guardar las decisiones en una caché de corta duración y acotada. Falla cerrada (I2).
  2. **Propagación:** el registro de cambios (C5) retira derivados cuando hay revocación o borrado, de modo que la capa 1 no sea la única defensa.
- **Alternativa descartada por ahora:** guardar en Glosa una copia de las ACL para filtrar antes de buscar. Duplica la autoridad de permisos (R4) y queda obsoleta en cuanto cambian.
- **Dos límites medibles (I7):** la vida de la caché de decisiones y el retraso del registro de cambios. Se proponen como configuración de la plantilla.
- **Pruebas:** revocar entre dos consultas; revocar con la caché caliente; ATLAS inalcanzable (debe fallar cerrado); revocación durante una reindexación.

### 5.7 Borrados y *tombstones*
- **Riesgo:** un documento borrado en el origen sigue vivo en el índice, o reaparece al reindexar un evento antiguo.
- **Exige:** el borrado es un evento con identificador; Glosa conserva un *tombstone* (referencia + versión + fecha) para que un evento atrasado no resucite el documento; el derivado desaparece, incluidos los fragmentos.
- **Pendiente previo en Glosa:** hoy no existe `DeleteDocument` (solo el puerto `mark_deleted`).
- **Pruebas:** borrar y luego recibir un evento de alta antiguo; borrar durante una ingesta en curso.

### 5.8 Sincronización y cursores
- **Exige:** consumir el registro de cambios con un cursor que Glosa guarda **después** de aplicar el cambio, en la misma transacción; así, tras una caída, se reanuda sin saltarse nada. Repetir lo ya aplicado es seguro por idempotencia (I5).
- **Pruebas:** caída entre aplicar y guardar el cursor; cursor inválido o caducado (debe provocar reconciliación, no ignorarse).

### 5.9 Reconciliación
- **Riesgo:** que el registro de cambios pierda eventos o que ambos sistemas deriven.
- **Exige:** una comparación periódica y barata (por ejemplo, por huellas de las referencias y versiones que Glosa tiene frente a las que el origen autoriza) que detecte lo que sobra, lo que falta y lo desactualizado, y lo corrija. Lo que sobra se retira (falla cerrada).
- **Pruebas:** introducir una diferencia a propósito y comprobar que se detecta y se corrige.

### 5.10 Reindexación
- **Cuándo ocurre:** cambia el modelo de *embeddings*, el chunker o el extractor.
- **Exige:** reconstruir desde el origen (I4), por versión de derivado, sin mezclar índices incompatibles (cada índice declara modelo, proveedor, dimensiones y versión), y sin servir resultados mezclados de dos generaciones. Un índice se activa cuando está completo.
- **Pruebas:** reindexar con una consulta en curso; reindexar con un documento revocado entre medias.

### 5.11 Duplicados
- **Riesgo:** el mismo documento recibido dos veces, o el mismo contenido en dos referencias.
- **Exige:** la identidad es la referencia de origen, no el contenido; la misma referencia y versión es idempotente. Dos referencias distintas con el mismo contenido son dos documentos (y sus permisos pueden diferir).

### 5.12 Fallos parciales
- **Riesgo:** un documento a medio indexar, o un lote con elementos que fallan.
- **Exige:** lo que ya hace hoy el worker (atomicidad por documento, reintentos y fallo definitivo con razón), más no servir un documento hasta que esté completo, y registrar el fallo como evidencia.

### 5.13 Consistencia eventual
- **Exige:** declarar la ventana de obsolescencia (I7), medirla y mostrarla en la observabilidad. En ningún caso la consistencia eventual puede significar servir lo no autorizado: la capa de consulta (5.6, capa 1) es la que lo garantiza.

### 5.14 Recuperación tras interrupciones
- **Exige:** poder reanudar tras una caída en cualquier punto: cursor transaccional, trabajos con *lease*, ingestas idempotentes y fragmentos con identificador determinista. **Gran parte de esto ya existe y está probado en Glosa**; lo nuevo es el cursor y la reconciliación.

## 6. Cómo se prueba sin ATLAS

- Se pueden escribir **pruebas de contrato** contra un **doble** (`FakeSource`, `FakeAuthorizationProvider`, `FakeChangeFeed`), siempre **identificado como doble** en su nombre y en su documentación.
- Un doble prueba que Glosa cumple *su* parte del contrato. **No prueba que ATLAS lo cumpla**, y **no es una prueba de integración**.
- Las pruebas de integración reales (autorización, revocación, consistencia, fallos, extremo a extremo) esperan a que los contratos existan y estén implementados en **ambos** proyectos (Fase 6 de [`HOJA-DE-RUTA.md`](HOJA-DE-RUTA.md)).

## 7. Preguntas que hay que responder con ATLAS

1. ¿Existe una operación para obtener el contenido de una versión concreta de un documento, con la decisión de autorización incluida?
2. ¿Existe una decisión de autorización **por lotes** sobre referencias? ¿Puede responder "no sé"?
3. ¿Cómo se representa el contexto autorizado de un agente o usuario (formato, emisor, caducidad) y cómo se verifica?
4. ¿Las versiones de un documento son inmutables y ordenables? ¿Hay una huella del contenido?
5. ¿Existe un registro de cambios con cursor? ¿Qué garantiza (orden, entrega, repetidos)? ¿Los borrados y las revocaciones son eventos?
6. ¿Qué semántica tienen los borrados (físicos, lógicos, con *tombstone*)?
7. ¿Qué transporte y qué autenticación entre sistemas están previstos?
8. ¿Cómo se versionan los contratos y cómo se descubren las capacidades?
9. ¿Qué evidencias de auditoría puede recibir ATLAS y en qué forma?

## 8. Lo que no se hará

- No crear endpoints ni operaciones de ATLAS que no existan.
- No inventar contratos a partir de nombres de operaciones.
- No simular una autorización real con un booleano local.
- No presentar un doble como prueba de integración.
- No crear una dependencia obligatoria con ATLAS: Glosa funciona sin él (R10).
- No modificar nada de ATLAS desde este proyecto.
