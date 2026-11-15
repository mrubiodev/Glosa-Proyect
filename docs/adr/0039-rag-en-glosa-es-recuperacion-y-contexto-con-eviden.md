# ADR 0039: RAG en Glosa es recuperación y contexto con evidencias; la generación es opcional y la hace por defecto el consumidor

- **Estado:** Propuesta. Revisión del 2026-11-09: aceptación recomendada con condiciones; **pendiente de la aprobación expresa del propietario**
- **Fecha:** 2026-11-09

## Contexto

La visión habla de RAG y de respuestas fundamentadas. Hoy Glosa **solo recupera fragmentos**: no construye contexto (G-030) ni genera respuestas. Hay que fijar qué significa RAG en Glosa antes de diseñarlo.

## Decisión

1. Glosa es un **motor de recuperación y construcción de contexto fundamentado**: devuelve fragmentos con procedencia, puntuaciones, estrategia y limitaciones, construye el contexto con sus evidencias y **señala cuándo no hay contexto suficiente**.
2. La **generación** es una capacidad **opcional** (un adaptador) y, **por defecto, la hace el consumidor**: el modelo que consulta por MCP o el sistema que integra Glosa.
3. Si algún día se implementa: citas obligatorias, negativa a responder sin evidencia y registro del modelo y de la estrategia.
4. Glosa no depende de ningún proveedor de modelos de lenguaje para funcionar.

## Alternativas consideradas

- **Glosa genera siempre.** Rechazada: dependencia de un modelo y duplica una responsabilidad del consumidor.
- **Solo recuperar, sin construir contexto.** Rechazada: traslada a cada consumidor la complejidad y las reglas de evidencia.

## Consecuencias

- G-030 y G-031 son el objetivo; **hoy no existen**. G-032 (generación) es opcional.
- Mientras no existan, no debe decirse que Glosa «hace RAG»: hace recuperación.
- Las pruebas no necesitan ningún modelo de lenguaje.

## Condiciones de la revisión del 2026-11-09

Aceptar **separando la recuperación y el contexto de la generación** (puntos 1 y 2). Hasta que exista G-030, Glosa es un motor de recuperación, no un RAG completo.

## Relacionado

- [Issue #1](https://github.com/mrubiodev/Glosa-Proyect/issues/1) y su [matriz de aceptación](../ISSUE-1-ACEPTACION.md)
- [`ECOSISTEMA.md`](../ECOSISTEMA.md)
