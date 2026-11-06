# glosa-core

Dominio, permisos, puertos y casos de uso. **No depende de ningún otro paquete ni de frameworks.**

## Qué hace

- Define las entidades (`domain.py`) y los puertos o interfaces (`ports.py`).
- Decide los permisos de usuarios y tokens (`authorization.py`).
- Genera, hashea y autentica tokens de colección (`tokens.py`).
- Encadena los hashes del registro de operaciones y los verifica (`chain.py`).
- Define los casos de uso (`usecases/`), que autorizan, actúan y dejan rastro en el registro de operaciones.
- Ofrece dobles en memoria para tests (`testing.py`) y pruebas de contrato (`queue_contract.py`), reutilizables por otros paquetes.

## Por qué existe como pieza separada

Es lo único que no cambia aunque se cambie la base de datos, el framework web o el protocolo de entrada. Todos los demás paquetes dependen de él; él no depende de nadie.

## Cómo se usa suelto

```python
from glosa_core.authorization import AuthorizationService, Permission
from glosa_core.domain import Actor, ActorKind

authz = AuthorizationService(mi_repositorio_de_accesos)
usuario = Actor(ActorKind.USER, "ana")
authz.require(usuario, "col-a", Permission.SEARCH)  # lanza PermissionDenied si no puede
```

## Qué se puede cambiar

Cualquier adaptador que cumpla un puerto de `ports.py`. El dominio no se entera.

## Estado

Implementado:

- Entidades, puertos, autorización, tokens y encadenado de hashes.
- Casos de uso (14 de 25): colecciones y tokens, subir, leer, listar y buscar documentos, consulta y cancelación de trabajos, consulta y verificación del registro, `HandleIngest` y `ProcessNextJob`.
- Dobles en memoria de todos los puertos (`testing.py`), un mundo completo reutilizable (`testing_world.py`) y pruebas de contrato de la cola (`queue_contract.py`), pensados para que los adaptadores reales pasen las mismas pruebas.
- Las 14 pruebas obligatorias de la spec. Se pueden ejecutar contra cualquier conjunto de adaptadores: `GLOSA_TEST_ADAPTERS=glosa_storage.testing:make_adapters pytest packages/core/tests`.

Pendiente: 11 casos de uso y varias tareas del núcleo. La lista completa y al día está en [`docs/PENDIENTE.md`](../../../docs/PENDIENTE.md).

## Tests

```bash
pip install -e ".[dev]"
pytest
```
