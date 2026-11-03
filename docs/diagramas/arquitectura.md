# Arquitectura general

Vista de alto nivel del backend (ver sección 3 de [SPEC.md](../SPEC.md)).

```
                    ┌──────────────────────────── BACKEND ────────────────────────────┐
 Frontend ─ HTTP ─► │  http-api ──┐                                                    │
 (cliente de la API)│             ├─► autorización ─► casos de uso ─► puertos          │
 LLM / cliente MCP ►│  mcp-server ┘        │               │                          │
                    │                      │               ├─ lecturas: síncronas     │
                    │                      │               └─ escrituras ─► JobQueue  │
                    │                      │                                  │       │
                    │  worker ◄────────────┼──────────────────────────────────┘       │
                    │    (ingesta, modificación, reindexado, borrado)                  │
                    │                      │                                          │
                    │                      ▼                                          │
                    │            OperationLog (solo se añade)                         │
                    │                      ▲                                          │
                    │  explain ────────────┘ (lee; nadie depende de él)               │
                    └─────────────────────────────────────────────────────────────────┘
```
