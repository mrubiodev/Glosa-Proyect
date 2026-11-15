# ADR 0037: Los contratos de interoperabilidad los define Glosa de forma explícita y neutral, y no se implementan conectores hasta verificarlos

- **Estado:** Propuesta
- **Fecha:** 2026-11-09

## Contexto

La Issue #1 pide un **perfil público de proveedor documental, neutral**, sin nombrar ningún consumidor, y prohíbe implementar conectores o asumir cómo funciona el consumidor. Una primera propuesta definía contratos desde las necesidades de un producto concreto y puertos para que Glosa tirase de su contenido.

## Decisión

1. Los contratos los **define Glosa**, de forma explícita, versionada y neutral, como un perfil público de proveedor documental. Los consumidores se adaptan a él.
2. **No se implementa ningún conector ni integración** con un sistema concreto hasta que el contrato exista y esté **verificado en ambas partes**.
3. Los dobles de prueba se identifican como tales, prueban **solo el lado de Glosa** y nunca cuentan como prueba de integración.
4. No se inventan operaciones ni endpoints ajenos.
5. Todo contrato lleva versión y permite descubrir las capacidades.

## Alternativas consideradas

- Implementar contra una API supuesta del consumidor. Rechazada.
- Adaptar Glosa a cada consumidor. Rechazada: acopla el núcleo a productos concretos.
- Simulaciones presentadas como pruebas de integración. Rechazada.

## Consecuencias

- Los entregables de la Issue #1 (G-100 a G-105) son el camino para definir el perfil.
- Cualquier adaptador hacia un consumidor concreto vive fuera del núcleo y se escribe cuando haya un contrato verificado.
- Se necesitan pruebas de contrato por versión.

## Relacionado

- [Issue #1](https://github.com/mrubiodev/Glosa-Proyect/issues/1) y su [matriz de aceptación](../ISSUE-1-ACEPTACION.md)
- [`ECOSISTEMA.md`](../ECOSISTEMA.md)
