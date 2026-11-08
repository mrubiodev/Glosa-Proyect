# glosa-worker

El bucle del worker de la cola de trabajos (capa fina).

## Qué hace

- `run(process_next, stop=...)`: procesa trabajos hasta que se active `stop`. Sin trabajo, espera (la espera se interrumpe en cuanto se pide parar). Al parar, **termina el trabajo en curso** antes de salir.
- `drain(process_next)`: procesa los trabajos que haya listos y termina.
- Ante fallos de **infraestructura** (la base bloqueada, por ejemplo) avisa, espera con espera creciente y sigue; tras 20 seguidos se rinde con `WorkerError` para que el orquestador lo reinicie en lugar de quedarse colgado.

## Por qué existe como pieza separada

No sabe nada de colas, bases de datos ni plantillas: recibe una función que procesa un trabajo. Lo que hay que hacer con cada trabajo (reintentos con espera creciente, pasar a `dead`) está en `core` (`ProcessNextJob`) y se prueba sin lanzar procesos.

## Cómo se usa

El proceso completo se arranca desde `app`, que es quien compone el sistema:

```bash
python -m glosa_app worker              # se queda esperando trabajos; Ctrl+C o SIGTERM paran
python -m glosa_app worker --once       # procesa lo que haya listo y termina
docker compose --profile worker up worker
docker compose --profile worker up --scale worker=3
```

Suelto, con cualquier función que devuelva el trabajo procesado (o `None`):

```python
import threading
from glosa_worker import run

stop = threading.Event()
run(mi_funcion, stop=stop, idle_seconds=1.0)
```

## Qué se puede cambiar

El broker de la cola (cambia el adaptador, no este bucle) o la forma de arrancar el proceso.

## Estado

Implementado, con tests. Pendiente: renovar el lease mientras un trabajo largo está en curso. Ver `docs/PENDIENTE.md`.
