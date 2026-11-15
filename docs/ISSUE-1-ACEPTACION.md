# Issue #1: matriz de aceptación

> **Fuente:** [Issue #1 de Glosa](https://github.com/mrubiodev/Glosa-Proyect/issues/1), *«[Architecture][P1] Definir perfil neutral de interoperabilidad como proveedor documental»*. Leída el 2026-11-09. Estado en GitHub: **abierta, ningún criterio marcado.**
>
> **Conclusión: la Issue #1 no se puede cerrar.** De 11 criterios, **2 se cumplen, 6 en parte y 3 no se cumplen**; de 7 entregables, ninguno está completo.
>
> **Una omisión que hay que reconocer.** La primera auditoría ([`AUDITORIA.md`](AUDITORIA.md)) se hizo **sin haber podido leer esta issue**. Varias decisiones propuestas entonces contradicen lo que pide; están en el apartado 4.

## 1. Criterios de aceptación

| | Criterio | Estado | Evidencia | Qué falta |
|---|---|---|---|---|
| 1 | Glosa funciona completamente como producto independiente | **Parcial** | Sin referencias a sistemas externos en el código ni dependencias externas; recorrido completo en `backend/app/tests/test_end_to_end.py` | «Completamente»: faltan la API, el MCP y los *embeddings* |
| 2 | La interoperabilidad es opcional y no añade dependencias externas | **Cumplido** (por ausencia) | No hay interoperabilidad implementada ni dependencia | Se volverá a comprobar cuando exista código de interoperabilidad |
| 3 | Se separa claramente la autoridad de Glosa de la del consumidor | **Parcial** | [`ECOSISTEMA.md`](ECOSISTEMA.md) | Nombra un producto concreto y modelaba mal a Glosa: la issue la define como autoridad sobre los documentos y versiones que ingiere (ver 4.2) |
| 4 | El perfil público no contradice la SPEC ni el OpenAPI | **No cumplido** | — | El perfil público no existe |
| 5 | Se distingue el MCP de solo lectura de las operaciones administrativas y de la API | **Parcial** | SPEC §12 y §13 | No se ha evaluado qué superficie corresponde a cada operación del perfil |
| 6 | Se documentan scopes, aislamiento por colección y límites de autorización | **Parcial** | SPEC §7 y §14; implementado y probado (pruebas obligatorias 1 a 6, también contra SQLite) | Qué garantiza el scope de un token y qué debe garantizar el consumidor; condiciones para no mezclar políticas incompatibles en una colección; reglas del contexto delegado |
| 7 | Se cubren versiones, idempotencia, retirada, borrado, reindexación y fallos parciales | **Parcial** | Versiones inmutables, idempotencia, reintentos y fallos parciales: implementados y probados | **Retirada, borrado y reindexación no están implementados** (A-13) y no hay contrato público de sincronización |
| 8 | Los resultados conservan procedencia suficiente para volver al origen | **No cumplido** | Un resultado lleva fragmento, documento y versión **locales**, ruta de encabezados, puntuación y estrategia | Faltan identificador y *namespace* de origen, hash, ubicación exacta y correlación de la consulta |
| 9 | Se diferencian capacidades diseñadas, implementadas, probadas y desplegadas | **Parcial** | [`AUDITORIA.md`](AUDITORIA.md) usa seis categorías propias | La issue pide cuatro niveles; falta «validada en despliegue» y nada lo está (ni siquiera se ha construido la imagen Docker) |
| 10 | Documentación enlazada desde los índices | **Cumplido** (lo existente) | [`README.md`](README.md), README raíz y SPEC | Se repetirá con los documentos nuevos |
| 11 | Informe final con archivos, decisiones, dudas, pruebas de documentación y lo **no** implementado | **No cumplido** | — | No existe como documento |

## 2. Entregables

| | Entregable | Estado |
|---|---|---|
| 1 | Arquitectura de interoperabilidad **neutral** | **No existe.** `ECOSISTEMA.md` es específico de un producto |
| 2 | Perfil público de proveedor (operaciones, esquemas, errores, capacidades, versionado) | **No existe** |
| 3 | Matriz de responsabilidades Glosa/consumidor | **Parcial:** la tabla de `ECOSISTEMA.md` es con un producto concreto |
| 4 | Diagramas de secuencia (consulta, autorización, sincronización, invalidación) | **No existen** |
| 5 | ADR de contratos y seguridad | **Parcial:** ADR 0035 a 0039 completos en esta revisión; siguen **propuestos** |
| 6 | Matriz de capacidades en cuatro niveles | **Parcial** (ver criterio 9) |
| 7 | Issues futuras propuestas | **Parcial:** propuestas en [`HOJA-DE-RUTA.md`](HOJA-DE-RUTA.md); no creadas |

## 3. Restricciones de la issue

| Restricción | Estado |
|---|---|
| No mencionar ni depender de un producto, repositorio o implementación externa concreta | **Incumplida por los documentos específicos de un producto** si se consideran trabajo de esta issue. **Resolución:** quedan **fuera de su alcance** (consta en su cabecera); el perfil neutral es un documento nuevo (G-100, G-101). SPEC, ADR y README se han **neutralizado** |
| No consultar ni modificar repositorios externos para completar esta issue | **Cumplida** para esta matriz (el repositorio de ATLAS, además, no es accesible desde este entorno) |
| No implementar conectores ni asumir cómo funciona el consumidor | Cumplida: no hay código |
| No convertir a Glosa en autoridad de identidad o ACL externa | Cumplida |
| No debilitar roles, scopes, aislamiento ni la autorización centralizada | Cumplida: el código no se ha tocado |
| No implementar herramientas MCP de escritura | Cumplida |
| No presentar como operativas las capacidades pendientes | Cumplida |
| Inspeccionar primero SPEC, PENDIENTE, OpenAPI, ADR y código | **Incumplida** en la primera auditoría (no se leyó la issue); corregida aquí |

## 4. Contradicciones entre lo propuesto antes y la issue

| | Lo propuesto antes | Lo que pide la issue | Corrección |
|---|---|---|---|
| **4.1** | Documentos que nombran un producto concreto | Perfil **neutral** | Documentos específicos fuera del alcance; perfil neutral como trabajo nuevo; SPEC, ADR y README neutralizados |
| **4.2** | En «modo gobernado», Glosa «no guarda el documento como fuente de verdad» | Glosa **es** autoridad sobre lo que ingiere (documentos, versiones, derivados, trabajos, operaciones); las copias **no la convierten en fuente de verdad del consumidor** | ADR 0035 reescrito |
| **4.3** | Reglas M3 y M4: sin tokens ni permisos locales en modo gobernado | «Glosa aplica siempre sus propias barreras»; credenciales de **mínimo privilegio, revocables y acotadas a la colección** | M3 y M4 sustituidas; autorización efectiva = **intersección** |
| **4.4** | Sincronización por *tirón* (`DocumentSource`, `ChangeFeed`) | Un contrato **de Glosa** para *recibir* contenido, con *namespace*, identificador, versión, hash e idempotencia | Entradas públicas que **posee Glosa**; los puertos de tirón pasan a segundo orden |
| **4.5** | Glosa preguntaría al origen por cada resultado (`AuthorizationProvider`) | El consumidor conserva la ACL; el contexto delegado «solo si puede validarse de extremo a extremo» | ADR 0038 reformulado: **el consumidor valida los candidatos**; Glosa garantiza retirada efectiva y sus barreras |
| **4.6** | Matriz de capacidades con seis categorías | Cuatro niveles, con «validada en despliegue» | Pendiente (G-104) |

## 5. Qué hace falta para cerrarla

1. **G-100.** Arquitectura de interoperabilidad **neutral** y matriz de responsabilidades (entregables 1 y 3).
2. **G-101.** **Perfil público de proveedor** versionado (entregable 2). Depende de G-016 y G-010.
3. **G-102.** **Diagramas de secuencia** (entregable 4).
4. **G-103.** ADR de contratos y seguridad, completos y aceptados (entregable 5).
5. **G-104.** Matriz de capacidades en **cuatro niveles** (entregable 6).
6. **G-105.** Informe final y creación de las issues de implementación (criterio 11, entregable 7).

Hasta que existan, **la Issue #1 sigue abierta**.

## 6. Lo que esta revisión no ha hecho

- No ha implementado nada ni consultado repositorios externos para esta matriz.
- No ha creado ni modificado issues en GitHub.
- No ha dado por buenas las decisiones de los ADR 0035 y 0039: están **propuestas**, pendientes de la aprobación expresa del propietario.
