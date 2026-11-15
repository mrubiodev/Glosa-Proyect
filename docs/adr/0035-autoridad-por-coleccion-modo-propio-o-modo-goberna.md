# ADR 0035: Autoridad por colección: modo propio o modo gobernado por el sistema consumidor

- **Estado:** Propuesta. Revisión del 2026-11-09: aceptación recomendada con condiciones; **pendiente de la aprobación expresa del propietario**
- **Fecha:** 2026-11-09

## Contexto

Glosa debe funcionar de forma independiente (R10) y, a la vez, servir a sistemas consumidores que conservan la autoridad sobre sus documentos originales, su identidad y su ACL (R1–R5). Hoy Glosa solo tiene un modo: es autoridad de todo en cada colección (contenido, versiones, usuarios, roles, tokens y auditoría).

La [Issue #1](https://github.com/mrubiodev/Glosa-Proyect/issues/1) define el reparto: Glosa es autoridad sobre sus colecciones, los documentos y versiones que **ingiere**, sus trabajos, sus índices derivados y sus operaciones; el consumidor, sobre sus usuarios, sus recursos originales, su ACL y sus decisiones de negocio. Y añade que **Glosa aplica siempre sus propias barreras**.

## Decisión

1. La autoridad se decide **por colección**, al crearla: **modo propio** (la política de acceso a los documentos la define Glosa, con sus usuarios y roles) o **modo gobernado** (la política de acceso a nivel de documento la define el sistema consumidor).
2. En ambos modos Glosa es autoridad sobre **lo que guarda** (copias, versiones ingeridas, derivados, trabajos, operaciones) y sobre **el acceso a su propia interfaz**. En ninguno lo es sobre el documento original, la identidad ni la ACL del consumidor. Guardar una copia no la convierte en fuente de verdad del consumidor.
3. **Doble control** en modo gobernado: la autorización efectiva es la **intersección** de la de Glosa y la del consumidor. La de Glosa es de grano grueso: una credencial de integración válida, de mínimo privilegio, revocable y acotada a colecciones y clases de operación. **Nunca** una copia de la ACL por documento. Ninguna de las dos puede ampliar a la otra.
4. El modo se fija al crear la colección. No hay conversión silenciosa: cambiarlo sería una migración explícita y auditada.
5. La colección es la **frontera de seguridad**: no se mezclan en ella documentos con políticas de acceso incompatibles.
6. **Falla cerrada:** si Glosa no puede validar la credencial o el alcance, no sirve nada.
7. El código común (ingesta, extracción, chunking, indexación, recuperación) **no conoce el modo**. Solo cambia quién decide el acceso a nivel de documento, y eso se expresa con puertos.

## Alternativas consideradas

- **Glosa como autoridad de todo en cualquier caso.** Rechazada: obligaría a duplicar la identidad y la ACL del consumidor y a mantenerlas sincronizadas.
- **En modo gobernado, Glosa sin ningún control local** (la propuesta original, reglas M3 y M4). Rechazada: deja la interfaz de Glosa sin protección si se compromete la integración, y contradice «Glosa aplica siempre sus propias barreras».
- **Copiar la ACL por documento en Glosa.** Rechazada: duplica la autoridad y se desincroniza.
- **Un único modo global.** Rechazada: rompe el uso independiente.
- **Modo mixto dentro de una colección.** Rechazada por ahora: mezcla políticas incompatibles.

## Consecuencias

- Nuevo atributo `Collection.origin` y credenciales de integración con alcance por colección y por clase de operación (tokens nativos de Glosa).
- Las pruebas obligatorias se repiten en ambos modos, con pruebas de la intersección (con dobles identificados como tales).
- Hay que documentar qué garantiza el scope de una credencial y qué debe garantizar el consumidor (G-100, G-101).
- El consumidor es responsable de no cargar en una misma colección documentos con ACL incompatibles y de validar los candidatos (ADR 0038).
- Coste: dos controles en cada consulta. Riesgo a vigilar: que el control grueso de Glosa degenere en una ACL por documento.

## Condiciones de la revisión del 2026-11-09

Aceptar **incorporando el doble control** (punto 3). Se mantienen: modo fijado al crear la colección, sin conversiones silenciosas, sin mezclar políticas incompatibles, revocación con falla cerrada y ningún resultado servido sin autorización vigente.

## Relacionado

- [Issue #1](https://github.com/mrubiodev/Glosa-Proyect/issues/1) y su [matriz de aceptación](../ISSUE-1-ACEPTACION.md)
- [`ECOSISTEMA.md`](../ECOSISTEMA.md)
