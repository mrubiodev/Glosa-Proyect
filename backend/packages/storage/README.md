# glosa-storage

Adaptadores de persistencia.

## Qué hace

Implementa los puertos de almacenamiento: documentos, índice, cola, registro de operaciones y accesos.

## Por qué existe como pieza separada

Es el único sitio donde viven SQLite y el sistema de archivos; el dominio no los conoce.

## Cómo se usa

Implementa `DocumentRepository`, `ChunkIndex`, `JobQueue`, `OperationLog` y `AccessRepository`. Adaptador inicial: SQLite con FTS5.

## Qué se puede cambiar

Sustituir SQLite por Postgres/pgvector, o la cola por Redis, sin tocar `core`.

## Estado

Esqueleto: pendiente de implementar. Ver `docs/SPEC.md`.
