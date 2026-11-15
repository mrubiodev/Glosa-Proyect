# G-014: revalidar permisos al ejecutar un trabajo

> **Estado:** especificación lista para implementar. **No hay código todavía.** Es la primera implementación recomendada, y no depende de ningún consumidor externo.

## Problema

Un trabajo se ejecuta con la identidad de **quien lo encoló**, y nadie vuelve a comprobar sus permisos al ejecutarlo:

- `ProcessNextJob` construye el contexto con `job.actor` (`usecases/jobs.py`).
- `HandleIngest` no llama al servicio de autorización (`usecases/handlers.py`).

Si entre encolar y ejecutar se revoca el rol del usuario, se revoca o caduca su token, o se le quita de la colección, **el trabajo sigue adelante y escribe**.

### Un matiz que cambia el diseño

Para un **usuario**, `AuthorizationService.permissions_of` consulta el rol en el repositorio cada vez: volver a llamar a `require` basta. Para un **token** no: usa los *scopes* que el `Actor` **trae consigo**, y el actor guardado en el trabajo es una **copia del momento de encolar**. Un token revocado o caducado después **seguiría pasando** un nuevo `require`. Revalidar exige **releer el token** (`AccessRepository.get_token`) y comprobar `revoked`, `expires_at` y sus scopes.

## Alcance

- Trabajos `ingest` y `modify` (los únicos manejadores que existen). `delete` y `reindex` heredarán la regla cuando se implementen (G-012, G-013).
- Permiso exigido: `SUBMIT_DOCUMENT` para ambos.
- Actores `user` y `token`. El actor `system` no pasa por este control.

## Diseño propuesto

1. Un método de revalidación en el servicio de autorización, que para un token **relee su estado** y para un usuario consulta su rol actual, y devuelve el motivo concreto (`rol retirado`, `token revocado`, `token caducado`, `no es miembro`).
2. **Dos comprobaciones en el manejador:**
   - **Temprana,** antes de extraer y trocear: falla rápido y no malgasta trabajo.
   - **Definitiva, dentro de la misma transacción que las escrituras** (`uow.transaction()`): es la que cuenta.
3. **Sin condición de carrera (TOCTOU).** En SQLite la transacción toma el bloqueo de escritura desde el principio, y revocar un rol o un token es también una escritura. Por tanto, o la revocación se confirma antes (la comprobación definitiva la ve y el trabajo no escribe nada) o después (el trabajo ya se confirmó entero). **Nunca queda a medias.**
4. **Si se deniega:**
   - El trabajo pasa a `dead` sin reintentos (un permiso retirado no se arregla reintentando) y con la razón.
   - No se escribe nada. Un documento nuevo queda `failed`; en una modificación, el documento sigue sirviendo su versión vigente.
   - Quedan en el registro la denegación (`denied`, con la razón, el actor y el `correlation_id` de la subida) y el `job.dead`.

## Pruebas

Contra los dobles en memoria **y contra SQLite** (`GLOSA_TEST_ADAPTERS`):

1. Usuario con rol retirado entre encolar y ejecutar: el trabajo muere sin escribir; sin fragmentos; documento `failed`.
2. Usuario quitado de la colección.
3. **Token revocado** después de encolar.
4. **Token caducado** después de encolar.
5. Modificación denegada: el documento conserva su versión vigente y se sigue pudiendo buscar.
6. Permiso vigente: el trabajo se completa (no se rompe el flujo normal).
7. La denegación y el `job.dead` aparecen en la traza de la subida, con la razón.
8. **Concurrencia (SQLite, con hilos):** una revocación confirmada antes de la transacción del manejador evita toda escritura; una confirmada después no deja un estado a medias.
9. Prueba obligatoria nueva, **la 15:** *un trabajo no se ejecuta con permisos revocados*.

## Criterios de aceptación

- Las pruebas 1 a 9 pasan en memoria y contra SQLite.
- Las 14 pruebas obligatorias existentes siguen pasando.
- La comprobación definitiva ocurre dentro de la transacción de escritura (revisión del código y prueba 8).
- Spec (§7 y §9) y `PENDIENTE.md` actualizados; ADR corto de la decisión.
- **No se modifica ningún contrato público.**

## Fuera de alcance

Autorización contra sistemas externos; cambios en la forma de los permisos; trabajos del actor `system`.

## Riesgos

- Un trabajo en curso cuando se revoca puede terminar si ya había tomado la transacción: es coherente (se confirmó antes) y debe quedar documentado.
- Hoy el trabajo guarda un **snapshot** del actor; conviene decidir si se sigue guardando solo para la traza, ya que no debe usarse para autorizar.
