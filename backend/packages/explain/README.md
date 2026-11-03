# glosa-explain

Lectura didáctica del registro de operaciones.

## Qué hace

Agrupa las entradas del registro por `correlation_id` y las presenta paso a paso.

## Por qué existe como pieza separada

Explicar el sistema no debe acoplarlo: este paquete solo lee, nadie depende de él.

## Cómo se usa

Consume `OperationLog` y devuelve trazas que el frontend dibuja.

## Qué se puede cambiar

Cambiar el formato de las trazas o añadir nuevas vistas sin afectar al resto.

## Estado

Esqueleto: pendiente de implementar. Ver `docs/SPEC.md`.
