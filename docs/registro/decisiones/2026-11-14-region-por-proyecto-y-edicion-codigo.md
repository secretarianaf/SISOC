# 2026-11-14 - Región y subzona por proyecto; código de proyecto editable

## Estado
- propuesta (pedido funcional; el diseño de datos y los resguardos los propuso el agente y quedan a revisión en el PR)

## Contexto
- La Región y Subzona de Abordaje Comunitario (#2642) estaban en
  `Organizacion.region_abordaje` / `subzona_abordaje`. El área pidió que sean
  datos de cada proyecto (Proyecto / Línea / Región / Subzona / Territoriales /
  Convenio).
- El código de proyecto se guarda en `ProyectoOrganizacion.codigo` y también,
  como texto, en `Comedor.codigo_de_proyecto`. Rendiciones y territoriales PNUD
  encuentran comedores y rendiciones por FK o por ese texto.
- La línea de las rendiciones nuevas se deduce del código o nombre del proyecto
  (`inferir_linea_programatica`: prefijo AMBA => Secos), en SISOC y en la API de
  la PWA.

## Decision
- `ProyectoOrganizacion` suma `region_abordaje` y `subzona_abordaje`
  (`organizaciones.0027`). La migración copia los de la organización a cada
  proyecto que no tenga ninguno de los dos; no pisa ni borra datos. Los campos
  de `Organizacion` quedan como dato anterior y ya no se editan.
- "AMBA" se agrega como Región y como Subzona/Aglomerado dentro de ella.
- Corregir el código de un proyecto guardado se hace en una pantalla propia
  (`cambiar_codigo_proyecto`): en una transacción cambia el código del proyecto
  y el `codigo_de_proyecto` de sus comedores (por FK o por organización + código
  anterior, incluidos los dados de baja). Rechaza códigos repetidos en la
  organización, sin distinguir mayúsculas, y si el cambio altera la línea
  deducida de las rendiciones nuevas pide confirmarlo.
- Un proyecto todavía no guardado se corrige en el mismo formulario, sin tocar
  la base.

## Consecuencias
- Las vinculaciones por texto siguen coincidiendo porque proyecto y comedores
  cambian juntos. Las rendiciones guardan su línea: las creadas no se recalculan.
- Los comedores se actualizan con `update()`: no se envía a GESTIONAR (su
  payload no incluye el código) y el cambio por comedor no queda en auditlog;
  el del proyecto sí, y el log lista los comedores tocados.
- Los filtros de región/subzona leen el proyecto: en Organizaciones, cualquiera
  de sus proyectos; en Comedores, el proyecto del comedor (FK). Una organización
  sin proyectos o un comedor sin proyecto vinculado no entra en esos filtros.
  Rendiciones usa la región del proyecto y, si falta, la anterior de la
  organización.
- Una PWA con datos en caché muestra el código anterior hasta refrescar.

## Referencias
- [Cambio](../cambios/2026-T4/2026-11-14-organizacion-region-por-proyecto.md)
- [Variantes AMBA en la línea](../cambios/2026-T4/2026-10-28-2642-variantes-amba.md)
- `src/backends/comedores/gestion_organizaciones/services/proyectos.py`
- `src/backends/kernel/organizaciones/migrations/0027_proyecto_region_subzona.py`
