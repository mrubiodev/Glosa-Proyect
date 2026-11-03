# Licencias de las dependencias

Inventario generado con `pip-licenses` sobre un entorno limpio con todos los paquetes instalados. Se revisa al añadir cada dependencia (ver SPEC §19.4): no se admite copyleft fuerte (GPL, AGPL) en lo que se distribuye.

## Dependencias que se distribuyen con el producto

| Paquete | Versión | Licencia |
|---------|---------|----------|
| PyYAML | 6.0.3 | MIT License |

`glosa-core` no tiene ninguna dependencia de terceros; se comprueba en `backend/tests/test_architecture.py`.

## Dependencias solo de desarrollo y pruebas (no se distribuyen)

| Paquete | Versión | Licencia |
|---------|---------|----------|
| pytest | 9.2.0 | MIT |
| pluggy | 1.7.0 | MIT License |
| iniconfig | 2.3.1 | MIT |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| Pygments | 2.21.0 | BSD-2-Clause |

## Herramienta de construcción

`hatchling` se usa solo para construir los paquetes; no forma parte de lo que se distribuye.

> La licencia indicada es la que declara el metadato de cada paquete. Antes de publicar, conviene confirmarla en el repositorio de cada dependencia.
