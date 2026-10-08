# VPSL: compatibilidad de jornadas y registros previos al flujo por jornada

## Contexto

El PR #2566 trasladó sede, localidad, ubicación y checklist a cada jornada y
agregó graduación obligatoria en registros. Las jornadas y registros cargados
antes de ese cambio no tienen esos datos, y quedaban sin localidad visible, con
el checklist vacío o sin poder editarse.

## Cambios

- Detalle, listado y exportaciones usan la localidad propia de la jornada y,
  si no existe, la localidad de la sede del catálogo (`localidad_display`).
- La migración `0016_copiar_checklist_sede_a_jornadas` copia a cada jornada el
  checklist que antes se compartía por sede. No cambia estados: una jornada
  previa con checklist completo se habilita al volver a guardar su checklist.
  La reversa elimina solo las copias y conserva la fila original por sede.
- Al editar una jornada previa, localidad y enlace de ubicación son opcionales
  si nunca se informaron. En altas siguen siendo obligatorios.
- Al editar un registro previo con resultado que requiere graduación y sin
  graduación cargada, la graduación es opcional. En altas, y en registros que
  pasan a un resultado que la requiere, sigue siendo obligatoria.
- Al cambiar el enlace de ubicación, la dirección se actualiza si el usuario no
  la había editado.
- En enlaces de lugar se priorizan las coordenadas del pin (`!3d/!4d`) sobre
  el centro del mapa (`@lat,lng`).
- Las fallas de red al resolver enlaces cortos se registran en el log.

## Pendiente

- `SedeVPSL.checklist_aprobado` ya no se actualiza y el listado de sedes lo
  sigue mostrando.
- Confirmar que el servidor de producción puede conectarse a
  `maps.app.goo.gl`.
