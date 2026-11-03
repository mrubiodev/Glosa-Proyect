# glosa-worker

Worker de la cola de trabajos (capa fina).

## Qué hace

Consume la cola y ejecuta ingesta, modificación, reindexado y borrado.

## Por qué existe como pieza separada

Las escrituras son asíncronas y se procesan en orden por colección.

## Cómo se usa

Toma trabajos con lease y latido; los manejadores son idempotentes.

## Qué se puede cambiar

Escalar a varias réplicas o cambiar el broker de la cola.

## Estado

Esqueleto: pendiente de implementar. Ver `docs/SPEC.md`.
