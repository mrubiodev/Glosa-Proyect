# glosa-http-api

API HTTP de gestión (capa fina).

## Qué hace

Expone colecciones, documentos, trabajos, tokens, operaciones y trazas por HTTP.

## Por qué existe como pieza separada

Traduce peticiones a casos de uso; no contiene lógica de negocio ni permisos propios.

## Cómo se usa

Contrato descrito en `docs/openapi.yaml`. Las escrituras responden `202` con `job_id`.

## Qué se puede cambiar

Cambiar el framework web sin afectar al dominio.

## Estado

Esqueleto: pendiente de implementar. Ver `docs/SPEC.md`.
