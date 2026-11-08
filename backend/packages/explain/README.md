# glosa-explain

Lectura didáctica del registro de operaciones: de entradas sueltas a una traza que se lee paso a paso.

## Qué hace

`build_trace(entries)` toma las entradas del registro que comparten un `correlation_id` y devuelve una `Trace`: cada paso con su título y detalle en lenguaje llano, el canal por el que pasó (`api`, `worker`...), el actor, la hora y la duración, más un resultado global (`succeeded`, `failed`, `denied` o `in_progress`).

```text
Traza corr-e608e85cec47 · resultado: correcto · 7 pasos · 2 ms
 1. 21:31:40.663 [api] ana — Se recibió el documento
      Versión 1, 52 bytes; trabajo job-9256c716c638 en cola
 2. 21:31:40.663 [worker] ana — El worker tomó el trabajo
      Intento 1 (ingest)
 3. 21:31:40.664 [worker] ana — Texto extraído del archivo
      50 caracteres
 ...
 7. 21:31:40.665 [worker] ana — Trabajo terminado
```

## Por qué existe como pieza separada

Explicar el sistema no debe acoplarlo: este paquete solo **lee** y solo depende de `core`. Quitarlo no rompe nada.

## Cómo se usa suelto

```python
from glosa_explain import build_trace

entries = glosa.view_trace.execute(ctx, collection_id, correlation_id)  # caso de uso de core
trace = build_trace(entries)
print(trace.outcome, trace.channels)   # succeeded ('api', 'worker')
print(trace.to_text())                 # para una terminal o un informe
```

## Qué decide el resultado

- Cualquier denegación → `denied`.
- Un trabajo muerto, o un paso fallido sin reintento → `failed`.
- Un trabajo que empezó o espera un reintento, o una subida aún sin procesar → `in_progress`.
- Si no, `succeeded`. Un reintento que acaba bien es `succeeded`, y el fallo intermedio **se conserva**.

## Qué se puede cambiar

Los textos de `trace.py` (hoy en español, fijos) o añadir descripciones para acciones nuevas. Una acción que no conozca se muestra con su nombre técnico en lugar de romper la traza, y una prueba comprueba que toda acción del sistema tiene su descripción.

## Estado

Implementado, con tests. Pendiente: sacar los textos para poder traducirlos. Ver `docs/PENDIENTE.md`.
