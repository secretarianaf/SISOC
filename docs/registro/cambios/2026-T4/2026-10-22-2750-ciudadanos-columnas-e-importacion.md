# Cambio: columnas de ciudadanos alineadas y lote que no se traba por una fila (#2750, punto 2)

## Alcance

En PRD, la importación masiva de ciudadanos fallaba con
`DataError (1264) Out of range value for column 'codigo_postal'`, y celiaquía
con `OperationalError (1366) Incorrect integer value: 'c 14' for column 'altura'`.
El job #16 (200.000 filas) quedó trabado en la fila 34.521, se reanudó 134
veces sin avanzar y terminó `failed`.

Causas:

- Las `AlterField` de `altura`, `codigo_postal` y `observaciones` quedaron solo
  en `state_operations` de
  `src/backends/kernel/ciudadanos/migrations/0009_squashed_0028.py`. Django cree
  que son `varchar`/`longtext`, pero en MySQL siguen como `int` y `varchar(500)`.
  Se confirmó en PRD con `information_schema` y también aparece en una base
  local creada desde cero.
- Cuando una fila lanzaba una excepción al guardarse, el lote quedaba en
  `processing`. `mark_stale_ciudadanos_import_jobs_as_failed` lo volvía a
  `pending` y se reintentaba la misma fila para siempre.

Se implementó:

- `src/backends/kernel/ciudadanos/migrations/0034_alinear_columnas_ciudadano_con_modelo.py`:
  compara el tipo real de cada columna con el del modelo y corrige solo las que
  difieren, con un único `ALTER TABLE` por tabla. No hace nada fuera de MySQL ni
  en bases ya alineadas, y el reverso no hace nada (volver a `int` perdería datos).
- `src/backends/kernel/ciudadanos/services_importacion_masiva_jobs.py`:
  - `_save_row_with_recovery`: un error de datos de una fila (`DataError` o los
    códigos MySQL 1264, 1265, 1292, 1366 y 1406) marca la fila como fallida
    (`error_type="invalid_row_data"`) y el lote sigue. Los otros errores de base,
    como una conexión caída, se siguen propagando.
  - `_fail_job_after_unexpected_error`: cualquier otro error inesperado deja el
    lote `failed` con el detalle, para reanudarlo a mano. La recuperación de
    lotes colgados queda solo para un worker que murió.

## Comportamiento

- `codigo_postal` acepta valores alfanuméricos (`B1636ABC`), `altura` acepta
  texto (`c 14`) y `observaciones` deja de cortar en 500 caracteres.
- Una fila con datos inválidos aparece como fallida en el detalle del lote, con
  el motivo, y no frena las demás.
- Un lote que falla por un error inesperado queda en "fallido" y muestra el
  error, en vez de reintentarse en silencio cada 15 minutos.
- **Despliegue:** en PRD, `ciudadanos_ciudadano` tiene unos 4,1 millones de
  filas (4,1 GB). El `ALTER TABLE` copia la tabla y bloquea las escrituras
  mientras dura, así que hay que correrlo en una ventana de mantenimiento. Los
  valores actuales entran en los nuevos tipos: el máximo es de 10 caracteres
  para `altura` y `codigo_postal`, y de 157 para `observaciones`.
- No incluye reanudar el job #16: es una decisión del responsable funcional.

## Verificación

- Migración aplicada sobre la base MySQL local, creada desde las migraciones.
  Después, la comparación entre `information_schema` y el modelo no muestra
  diferencias. Revertirla y volver a aplicarla no cambia nada.
  `makemigrations --check --dry-run`: sin cambios.
- `src/backends/kernel/tests/test_ciudadanos_columnas_mysql.py` (`mysql_compat`):
  pasa contra MySQL real con una base de test creada desde cero.
- Tests del worker en `src/backends/kernel/tests/test_ciudadanos_importacion_masiva.py`:
  fila con datos inválidos en el medio (`DataError` 1264 y `OperationalError`
  1366), error de base que no es de datos (se propaga) y error inesperado del
  lote (queda `failed` y no se reencola). Pasan en SQLite. Sobre MySQL, los tests
  del worker fallan por el entorno de test (`OperationalError 2006` en
  `close_old_connections` dentro de la transacción del test), igual que el test
  ya existente `test_process_ciudadanos_import_job_creates_existing_and_failed_rows`.
  En CI no corren sobre MySQL.
- `pytest src/backends/kernel/tests/ -n auto`: 1758 passed, 11 skipped.
- black sin cambios; pylint 10/10 en el servicio.
- No validado en QA/HML ni con el archivo real del job #16.
