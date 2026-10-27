# Cambio: el reporte VAT de inscripciones no depende de las tablas de zonas horarias (#2750, punto 4)

## Alcance

`/vat/reportes/inscripciones-asistencias/` respondió 500 en PRD con
`ValueError: Database returned an invalid datetime value. Are time zone
definitions for your database installed?`. El MySQL de PRD no tiene cargadas
las tablas de zonas horarias: `CONVERT_TZ(NOW(),'UTC','America/Argentina/Buenos_Aires')`
devuelve `NULL`. `TruncMonth("fecha_inscripcion")`, con `USE_TZ=True`, depende
de ellas.

Los filtros `fecha_inscripcion__date__gte/lte` del mismo reporte tienen la misma
dependencia. No dan error, pero en PRD devuelven cero resultados sin avisar.
Se verificó con otro modelo: de 1616 rendiciones, `fecha_creacion__date >= 2020`
devuelve 0.

Cambios en `src/backends/vat/VAT/services/reportes_inscripciones_asistencia.py`:

- `_mes_de_inscripcion`: resta 3 horas a `fecha_inscripcion` (Argentina no
  tiene horario de verano desde 2009) y trunca en UTC con salida `DateField`.
  No genera `CONVERT_TZ`. La decisión de usar un desfase fijo con comentario fue
  del usuario en el issue.
- Las fechas desde/hasta se filtran con un rango explícito: del inicio del día
  local desde hasta el inicio del día siguiente al hasta. Es el mismo patrón que
  `_rango_del_dia` en `src/backends/inspecciones/inspecciones/services/panel.py`.

## Comportamiento

- El reporte agrupado por mes vuelve a generarse en PRD.
- Los filtros de fecha del reporte vuelven a devolver resultados en PRD. Antes
  devolvían cero.
- Una inscripción a las 23:30 del último día del mes, hora argentina, cuenta en
  ese mes y no en el siguiente.

## Pendiente: los 504

`EXPLAIN` en PRD (42.427 inscripciones) de la consulta agrupada por centro:
junta inscripciones (~21.700 filas) con asistencias (~37 por fila), con las
sesiones de la comisión de curso (~101) y de nuevo con `VAT_sesioncomision`
(`T19`, ~473.209 filas estimadas por combinación, por el índice de `estado`).
Los `Count(..., distinct=True)` de `_row_annotations` sobre esas relaciones
multiplican las filas. Este PR no lo corrige: hace falta reescribir la consulta
y medir antes y después.

## Verificación

- `test_reporte_por_mes_agrupa_en_hora_argentina` y
  `test_reporte_filtra_fechas_por_dia_argentino` en
  `src/backends/vat/VAT/test_reporte_inscripciones_asistencia.py`: pasan en SQLite
  y MySQL. Usan inscripciones a las 23:30 del 30/04 y 00:30 del 01/05, que en
  UTC caen las dos el 01/05.
- `test_reporte_no_depende_de_las_tablas_de_zonas_horarias` (`mysql_compat`):
  verifica que ninguna consulta del reporte use `CONVERT_TZ`. Falla con el código
  anterior y pasa con el nuevo. El MySQL local sí tiene las tablas, por eso el
  test mira el SQL y no el error.
- black sin cambios. pylint marca `too-many-branches` en `_apply_filters`, que
  ya existía en `development`; CI no lintea `services/`.
