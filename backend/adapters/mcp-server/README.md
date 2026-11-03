# glosa-mcp-server

Servidor MCP multitenant (capa fina).

## Qué hace

Expone `buscar`, `leer_documento` y `listar_documentos` a los LLM, con autenticación por token.

## Por qué existe como pieza separada

Los LLM se conectan directamente al backend; los permisos los decide `core`.

## Cómo se usa

El token determina la colección; el cliente nunca elige `collection_id`. Solo lectura en v0.x.

## Qué se puede cambiar

Añadir herramientas de escritura (con scope `write`, que encolan) o pasar a OAuth 2.1.

## Estado

Esqueleto: pendiente de implementar. Ver `docs/SPEC.md`.
