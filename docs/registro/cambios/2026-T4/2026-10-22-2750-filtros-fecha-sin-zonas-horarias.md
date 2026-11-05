# Cambio: filtros por fecha que no dependen de las zonas horarias de MySQL (#2750, punto 4)

## Alcance

El MySQL de PRD no tiene cargadas las tablas de zonas horarias:
`CONVERT_TZ(NOW(),'UTC','America/Argentina/Buenos_Aires')` devuelve `NULL`.
Con `USE_TZ=True`, todo `campo__date` sobre un `DateTimeField` se traduce a
`DATE(CONVERT_TZ(...))` y en PRD **devuelve cero resultados sin dar error**.
Se verificó en PRD: de 1616 rendiciones, `fecha_creacion__date >= 2020`
devuelve 0. El reporte VAT de inscripciones se corrigió aparte, en
`docs/registro/cambios/2026-T4/2026-10-22-2750-vat-reporte-sin-tablas-zonas-horarias.md`.

Cambios:

- `src/backends/kernel/core/utils.py`: `rango_del_dia_local(fecha)` devuelve el
  inicio y el fin (exclusivo) del día en la zona local, como datetimes aware.
  Python resuelve la zona, no MySQL.
- `src/backends/kernel/core/services/advanced_filters/`: cuando un campo de tipo
  `date` está mapeado como `campo__date`, el motor arma la comparación con ese
  rango (`build_local_day_q`) para eq, ne, gt, lt, gte y lte. El operador
  `empty` usa `campo__isnull`; antes, `campo__date__isnull` devolvía todo en
  PRD. Corrige de una vez los filtros avanzados que mapean `__date`:
  rendiciones (`fecha_creacion`, `ultima_modificacion`), gestión de
  organizaciones (`fecha_vencimiento`, `fecha_creacion`), importación de
  expedientes (`fecha_subida`), expedientes de celiaquía (`fecha_creacion`) y
  beneficiarios y responsables de CDF (`fecha_creado`). Los `filter_config` no
  cambian.
- Usos directos:
  - papelera, `src/backends/kernel/core/trash_views.py` (`deleted_at`);
  - auditoría, `src/backends/kernel/audittrail/services/query_service/impl.py`
    (`start_date`);
  - detalle de intervenciones, `src/backends/comedores/intervenciones/views.py`
    (`_filtrar_por_dia`).

Fuera de alcance, porque ya usaban rangos explícitos: inspecciones, el reporte
de celiaquía y PAS. `periodo__year/__month` (comedores) y
`fecha_inicio__year` (VAT) son `DateField`, que no convierten zona horaria.

## Comportamiento

- Los filtros por fecha de esas pantallas vuelven a devolver resultados en PRD.
- Un registro de las 23:30 del 30/04, hora argentina, cuenta como del 30/04.
- En intervenciones, una fecha con formato inválido ahora se ignora en vez de
  llegar al ORM.

## Verificación

- `src/backends/kernel/tests/test_filtros_fecha_dia_local.py`: el motor con los
  6 operadores sobre `User.date_joined` en los bordes 23:30 del 30/04 y 00:30
  del 01/05 (en UTC, los dos el 01/05), el operador `empty`, la papelera y la
  auditoría. `test_engine_no_usa_convert_tz_en_mysql` (`mysql_compat`) revisa
  que no haya `CONVERT_TZ` en el SQL. Todo pasa en SQLite y en MySQL real. Con
  el motor anterior fallan el test de `CONVERT_TZ` y el de `empty`.
- `src/backends/comedores/tests/test_intervenciones_filtro_fecha.py`.
- `pytest` de kernel, comedores, cdf y celiaquía con `-n auto`: 2466 passed,
  7 skipped.
- black sin cambios. pylint 10/10 en los archivos que lintea CI. En
  `advanced_filters/`, que CI no lintea, las advertencias de complejidad ya
  existían en `development`.
