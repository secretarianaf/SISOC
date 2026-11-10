# Cambio: el relevamiento conserva los datos del comedor de cuando se hizo (#2797)

## Alcance

El detalle del relevamiento (`/comedores/<pk>/relevamiento/<pk>`) leía los datos
generales del comedor en vivo: editar el comedor (nombre, domicilio, referente)
cambiaba lo que mostraban relevamientos ya finalizados. Ahora cada relevamiento
finalizado guarda una copia de esos datos.

Código, todo en `src/backends/comedores/relevamientos/`:

- `models.py`: campo `Relevamiento.datos_comedor_snapshot` (JSON) y propiedad
  `datos_comedor` (el snapshot si existe; si no, los datos vivos, con la misma forma).
- `services/datos_comedor_snapshot.py`: `armar_snapshot`, función pura que arma el
  dict plano (comedor, domicilio con nombres, programa, referente y responsable).
- `migrations/0024_relevamiento_datos_comedor_snapshot.py`: agrega el campo y
  completa los finalizados existentes (por lotes de 500).
- Templates `relevamiento_detail.html`, `relevamiento_detail_secciones.html` y
  `relevamiento_pdf.html`: leen `relevamiento.datos_comedor`.

Se hizo como `admisiones` con `datos_organizacion_snapshot`.

## Comportamiento

- El snapshot se arma en `Relevamiento.save()` cuando el estado es `Finalizado` o
  `Finalizado/Excepciones` y todavía no hay snapshot. Se eligió ahí porque el PATCH
  de la app actualiza el comedor y el referente (`RelevamientoService.update_comedor`
  y `create_or_update_responsable_y_referente`, en el `clean` del serializer) antes de
  guardar el relevamiento: el snapshot captura lo cargado en esa visita. El comedor se
  lee de la base, no de la instancia en memoria.
- Relevamientos no finalizados siguen mostrando los datos vivos.
- `set_referente_como_responsable` ya no reasigna el responsable de un relevamiento
  finalizado con snapshot.
- Corrige `localida` (typo) en el template: la localidad nunca se mostraba.
- Los breadcrumbs del detalle siguen mostrando el nombre actual del comedor, porque
  enlazan a su ficha.
- Límite: los finalizados anteriores a este cambio quedan con los datos del comedor
  al momento de la migración; no hay historial para reconstruir los anteriores.
- La migración importa `armar_snapshot` del servicio; si ese módulo se renombra,
  hay que ajustar la migración.

## Verificación

`pytest src/backends/comedores/relevamientos/tests` (9 tests: snapshot, congelado al
finalizar, pendiente en vivo, captura al pasar a finalizado, responsable no
reasignado, detalle HTML y backfill) y los tests de relevamientos existentes
(`test_relevamiento_api_patch`, `test_relevamiento_estado_visible_2630`,
`test_relevamiento_pdf_2630`). Migración incluida: requiere revisión técnica.
