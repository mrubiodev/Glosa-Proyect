# Frontend

Cliente de la API del backend. No contiene lógica de negocio ni permisos: solo consume la API pública descrita en [`../docs/openapi.yaml`](../docs/openapi.yaml), igual que lo haría cualquier tercero.

## Estructura

```
api-client/   cliente generado desde docs/openapi.yaml
src/          UI de subida y modo "ver por dentro"
```

## Qué debe enseñar (ver `docs/SPEC.md` §15)

- Ver por dentro la ingesta, la cola en vivo y el historial de un documento.
- Búsqueda explicada y traza de las llamadas MCP.
- Línea de tiempo de una operación (por `correlation_id`).
- Comparador RAG vs MCP y permisos en vivo.

## Estado

Pendiente. Aún no se ha elegido el framework.
