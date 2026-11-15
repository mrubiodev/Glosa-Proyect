# ADR 0036: Los índices son derivados y reconstruibles

- **Estado:** Propuesta
- **Fecha:** 2026-11-09

## Contexto

Hoy el índice de texto es derivado y, en modo propio, el contenido original está en la base, de modo que se podría reconstruir. Pero no existe un caso de uso de reindexación y **no se registra con qué extractor y chunker se generó cada derivado** (A-04 de la auditoría).

## Decisión

1. Un índice **nunca es fuente de verdad**: debe poder descartarse y regenerarse desde el contenido del origen.
2. Todo derivado registra con qué extractor, chunker y, si procede, modelo, proveedor, dimensiones y versión se generó (`DerivationInfo`).
3. **No se mezclan índices incompatibles.**
4. Un índice nuevo **se activa solo cuando está completo**; hasta entonces se sigue sirviendo el anterior.
5. Reconstruir exige que el contenido siga disponible y autorizado.

## Alternativas consideradas

- Tratar el índice como fuente de verdad. Rechazada.
- Reindexación incremental sin metadatos de generación. Rechazada: no se sabe qué reconstruir.
- Servir resultados mezclados de dos generaciones. Rechazada.

## Consecuencias

- Nuevos `ReindexDocument`, `HandleReindex` (G-013) y `DerivationInfo`, con migración de la base.
- Coste de reconstrucción que hay que poder acotar y reanudar.
- Pruebas: reindexar con una consulta en curso; reindexar con un documento retirado entre medias.

## Relacionado

- [Issue #1](https://github.com/mrubiodev/Glosa-Proyect/issues/1) y su [matriz de aceptación](../ISSUE-1-ACEPTACION.md)
- [`ECOSISTEMA.md`](../ECOSISTEMA.md)
