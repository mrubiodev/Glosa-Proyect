# glosa-app

Composición y arranque.

## Qué hace

- Es el **único lugar** donde se conectan los adaptadores concretos con los casos de uso.
- Ofrece la orden `check`, que valida la plantilla activa: esquema, guardia de producción y estado de los adaptadores.

## Por qué existe como pieza separada

Mantiene el resto de paquetes desacoplados: solo `app` puede importar de todos (lo comprueba `backend/tests/test_architecture.py`).

## Cómo se usa

Construir el sistema desde la plantilla activa y usarlo:

```python
from glosa_app.composition import build_from_env
from glosa_core.domain import Actor, ActorKind
from glosa_explain import build_trace

glosa = build_from_env({"GLOSA_DATA_DIR": "./data"})   # plantilla "didactico" por defecto
ana = Actor(ActorKind.USER, "ana")

col = glosa.create_collection.execute(glosa.context(ana), "Contratos")
subida = glosa.submit.execute(
    glosa.context(ana), col.id, title="Contrato", source_type="markdown",
    content="# Contrato\n\n## Rescisión\n\nPreaviso de quince días.".encode(),
)
glosa.process_next_job.execute()        # esto lo hace el worker en su propio proceso

for hit in glosa.search.execute(glosa.context(ana), col.id, "rescision"):   # sin tilde
    print(hit.chunk.metadata["heading_path"], "->", hit.chunk.text)
print(build_trace(glosa.view_trace.execute(glosa.context(ana), col.id, subida.correlation_id)).to_text())
glosa.close()
```

Desde la línea de órdenes:

```bash
python -m glosa_app check                       # valida la plantilla activa
python -m glosa_app check --strict              # y que estén todos los adaptadores
GLOSA_TEMPLATE=profesional python -m glosa_app check
python -m glosa_app worker                      # procesa la cola hasta que se le pida parar
python -m glosa_app worker --once               # procesa lo que haya listo y termina
```

`build_app` se niega a arrancar si la plantilla de producción es insegura o si pide un adaptador que no está registrado, y deja en el registro una entrada `template.applied` con la huella de la plantilla.

Códigos de salida: `0` correcto · `1` plantilla o configuración no válida (o worker rendido).

Variables de entorno: `GLOSA_TEMPLATE`, `GLOSA_TEMPLATE_DIRS`, `GLOSA_DATA_DIR`, `GLOSA_WORKER_ID`, `GLOSA_WORKER_LEASE_SECONDS` (ver `docs/SPEC.md` §17.3).

## Qué se puede cambiar

Cambiar de adaptadores modificando solo la composición.

## Estado

Implementado, con tests: la composición, la orden `check` y la orden `worker`.
Pendiente: arrancar la API y el servidor MCP (todavía no existen) y los datos de demostración. Ver `docs/PENDIENTE.md`.
