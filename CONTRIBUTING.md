# Cómo contribuir

Gracias por querer ayudar. Antes de enviar código, lee esto.

## Contribuciones de código

1. **Firma el CLA** (`CLA.md`). Sin él no se puede aceptar código: el proyecto se ofrece con una licencia pública y con una comercial, y el CLA es lo que permite mantener ambas.
2. **Documenta primero.** Un cambio de comportamiento empieza en `docs/SPEC.md`; una decisión relevante, en un ADR (`docs/adr/`).
3. **Respeta la arquitectura.** Las reglas de dependencia (SPEC §5) las comprueba `backend/tests/test_architecture.py`.
4. **Escribe tests.** Todo cambio en `core` o en `templates` lleva tests.
5. **No añadas dependencias con copyleft fuerte** (GPL, AGPL) y actualiza `docs/licencias-dependencias.md`.

```bash
cd backend
make install
make test
```

## Contribuciones que no son código

Informar de errores, mejorar la documentación o proponer ideas en una incidencia no requiere CLA.

## Seguridad

Si encuentras un fallo de seguridad (sobre todo de aislamiento entre colecciones o de permisos), **no lo publiques en una incidencia abierta**: escríbelo por el canal privado que se indique en el README.
