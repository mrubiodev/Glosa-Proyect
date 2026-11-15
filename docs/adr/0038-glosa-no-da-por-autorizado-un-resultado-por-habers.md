# ADR 0038: Glosa no da por autorizado un resultado por haberse indexado: retirada efectiva, validación del consumidor y falla cerrada

- **Estado:** Propuesta. Sustituye a una versión anterior, en la que Glosa preguntaba al origen por cada resultado
- **Fecha:** 2026-11-09

## Contexto

Un índice derivado puede seguir sirviendo información que el consumidor ya no autoriza. Una primera propuesta hacía que Glosa **preguntase al sistema de origen** por cada resultado. La Issue #1 apunta a otra cosa: el consumidor conserva la ACL y un contexto delegado solo debe aceptarse si se valida de extremo a extremo, nunca por claims arbitrarios del cliente.

## Decisión

1. Un resultado **no se considera autorizado** por haberlo estado al indexarse.
2. **Por defecto, la validación documental de los candidatos corresponde al consumidor**. Glosa devuelve procedencia suficiente (origen, documento, versión, hash, ubicación) y presenta los resultados como **candidatos o evidencias**.
3. Glosa **garantiza**: aislamiento por colección; credenciales acotadas y revocables con efecto inmediato; **retirada efectiva** (una versión retirada o borrada deja de aparecer como vigente y sus fragmentos se eliminan, con un *tombstone* que impide resucitarla); y **falla cerrada** si no puede validar la credencial o el alcance.
4. **Extensión opcional:** contexto delegado o ámbito autorizado, aceptado **solo si puede validarse de extremo a extremo**. Nunca un claim arbitrario, ni un identificador de colección o un filtro tomados como prueba de autorización.
5. La **obsolescencia posible se declara y se mide**.

## Alternativas consideradas

- **Glosa pregunta al origen por cada resultado** (propuesta anterior). Rechazada como base: acopla Glosa al origen. Queda como extensión futura si existe un canal validable.
- **Copia de la ACL en Glosa.** Rechazada.
- **Confiar en lo autorizado al indexar.** Rechazada: es el fallo que se quiere evitar.
- **Solo sincronización periódica.** Rechazada: obsolescencia sin límite.

## Consecuencias

- Hacen falta `DeleteDocument` y la retirada (G-012), la procedencia en el resultado (G-010) y el contrato de sincronización (G-101).
- La seguridad depende de que el consumidor cumpla su parte: hay que **documentarlo** como responsabilidad suya.
- Con falla cerrada, una credencial no validable significa indisponibilidad, no un resultado dudoso.

## Relacionado

- [Issue #1](https://github.com/mrubiodev/Glosa-Proyect/issues/1) y su [matriz de aceptación](../ISSUE-1-ACEPTACION.md)
- [`ECOSISTEMA.md`](../ECOSISTEMA.md)
