# glosa-retrieval

Estrategias de búsqueda.

## Qué hace

Reúne las estrategias de recuperación: texto, vectorial, híbrida y reranker.

## Por qué existe como pieza separada

Separa la lógica de ordenar resultados de dónde se guardan los datos.

## Cómo se usa

Compone sobre el puerto `ChunkIndex` de `glosa-core`. Ejemplo previsto: búsqueda híbrida que fusiona resultados de texto y vectoriales.

## Qué se puede cambiar

Cambiar la fusión de puntuaciones o añadir un reranker.

## Estado

Esqueleto: pendiente de implementar. Ver `docs/SPEC.md`.
