# glosa-core

Dominio, permisos, puertos y casos de uso. **No depende de ningún otro paquete ni de frameworks.**

## Qué hace

- Define las entidades (`domain.py`) y los puertos o interfaces (`ports.py`).
- Decide los permisos de usuarios y tokens (`authorization.py`).
- Genera, hashea y autentica tokens de colección (`tokens.py`).
- Encadena los hashes del registro de operaciones y los verifica (`chain.py`).
- Ofrece dobles en memoria para tests (`testing.py`), reutilizables por otros paquetes.

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

Implementado: entidades, puertos, autorización, tokens, encadenado de hashes y 23 tests.
Pendiente: casos de uso (`usecases/`), según el orden sugerido en su `__init__.py`.

## Tests

```bash
pip install -e ".[dev]"
pytest
```
