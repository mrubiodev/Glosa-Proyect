# ADR 0032: El worker es un bucle sin lógica de negocio: reintentos y `dead` viven en `core`

- **Estado:** Propuesta
- **Fecha:** (completar)

## Contexto

(Describir el problema y las fuerzas en juego.)

## Decisión

El worker es un bucle sin lógica de negocio: reintentos y `dead` viven en `core`.

## Motivo

El adaptador es intercambiable y la política de reintentos se prueba sin procesos.

## Alternativas consideradas

(Completar.)

## Consecuencias

(Completar: qué se gana, qué se complica, qué habrá que revisar.)
