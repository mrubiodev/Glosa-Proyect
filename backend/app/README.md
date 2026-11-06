# glosa-app

Composición y arranque.

## Qué hace

- Es el **único lugar** donde se conectan los adaptadores concretos con los casos de uso.
- Ofrece la orden `check`, que valida la plantilla activa: esquema, guardia de producción y estado de los adaptadores.

## Por qué existe como pieza separada

Mantiene el resto de paquetes desacoplados: solo `app` puede importar de todos (lo comprueba `backend/tests/test_architecture.py`).

## Cómo se usa

```bash
python -m glosa_app check                    # plantilla "didactico" por defecto
GLOSA_TEMPLATE=profesional python -m glosa_app check
GLOSA_TEMPLATE=acme-legal GLOSA_TEMPLATE_DIRS=examples/templates python -m glosa_app check
python -m glosa_app check --strict           # falla si faltan adaptadores
```

Códigos de salida: `0` plantilla válida · `1` plantilla no válida (o `--strict` con adaptadores pendientes).

Variables de entorno: `GLOSA_TEMPLATE`, `GLOSA_TEMPLATE_DIRS` (ver `docs/SPEC.md` §17.3).

## Qué se puede cambiar

Cambiar de adaptadores modificando solo la composición.

## Estado

Implementado: la orden `check`, con tests.
Pendiente: componer los casos de uso con los adaptadores que pida la plantilla y arrancar API, MCP y worker. `check` descubre los adaptadores instalados por entry point; hoy faltan `embedder: none` y `authenticator: token`.
