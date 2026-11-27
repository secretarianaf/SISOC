# 2026-11-26 - Audiencias y alcance de tableros (#2912)

## Estado

Aceptada para el alcance indicado; implementación integral pendiente.

## Contexto

El acceso al tablero no demuestra el alcance efectivo de sus datos. Una persona puede recibir concesiones individuales y de varias audiencias. Los CDI pertenecen a otra vertical y no deben importarse directamente desde core.

## Decisión

Las concesiones se acumulan por usuario y tablero. El rol de la audiencia se limita a tableros y no cambia roles generales. Los tipos nacional, provincia y CDI se representan por separado; no se deduce acceso provincial de una concesión CDI. Un CDI no concede acceso nuevo sin validación explícita por un contrato de su vertical. Los accesos heredados sin alcance verificable permanecen bajo su política anterior mientras se revisan.

## Consecuencias

La unión es explicable, pero una concesión amplia amplía el acceso del tablero correspondiente. Las rutas y fuentes deben aplicar el alcance antes de entregar datos; incorporar el modelo no es suficiente. La validación de CDI y los mecanismos de proveedor externo requieren coordinación antes de activar rutas. Los métodos auditables no deben reemplazarse por escrituras masivas que omitan señales.

## Referencias

- Issue: https://github.com/secretarianaf/SISOC/issues/2912
- Cambio: `docs/registro/cambios/2026-T4/2026-11-26-2912-base-audiencias-tableros.md`.
