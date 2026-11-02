# Cambio: los logs diarios se escriben en la carpeta de la fecha real (#2750, punto 8)

## Alcance

En PRD, cada proceso escribía sus logs en
`/sisoc/SISOC/logs/<fecha de arranque>/` y no en la carpeta del día. El
21/10, los errores del día estaban en `2026-10-15/` y `2026-10-20/`, mientras
la carpeta del día seguía casi vacía. `DailyFileHandler`
(`src/backends/kernel/core/utils.py`) calculaba la fecha una sola vez, en
`__init__`.

Ahora `DailyFileHandler.emit` compara la fecha local de cada registro con la
del archivo abierto. Si cambió, cierra el archivo, crea la carpeta del día con
permiso de escritura de grupo y sigue escribiendo ahí. El cambio de archivo
pasa con el lock del handler tomado (`Handler.handle`).

La fecha sale de `record.created` (el momento del registro) en la zona horaria
de Django, no de `timezone.now()`: así un `timezone.now` parcheado en tests no
rompe el logging. Si calcular la fecha o cambiar de archivo falla, el handler
usa `handleError` como el resto de `logging` y no propaga la excepción al
código que loguea. Cada proceso abre su propio archivo en modo append; no hay
renombrado ni rotación compartida, así que varios workers pueden escribir el
mismo día sin pisarse.

## Comportamiento

- Los errores de hoy quedan en `logs/<hoy>/error.log`, aunque el proceso haya
  arrancado otro día. Lo mismo para `info`, `warning`, `critical` y `data`.
- No cambia la ruta base (`LOG_DIR`) ni el formato de los logs.

## Otros temas del punto 8 (sin código)

- `SENTRY_DSN invalido ... Missing public key`: la variable del `.env` de PRD
  está mal formada y Sentry no reporta nada. Es tarea de infraestructura.
- `manage.py showmigrations` con `NodeNotFoundError` en el contenedor core:
  es lo esperado. El core no tiene el grafo completo de migraciones
  (`users.0031_bootstrap_cdf_referente_centro_group` depende de
  `centrodefamilia.0014_accesocdf`), y `docs/operacion/backends_por_servicio.md`
  indica correr `migrate` y `showmigrations` en el migrador. No se cambian
  dependencias, como pide `docs/desarrollo/verticales_independientes.md`.

## Verificación

- `test_daily_file_handler_cambia_de_carpeta_cuando_cambia_el_dia` en
  `src/backends/kernel/core/tests/test_utils.py`: un registro del 15/10 y otro
  del 21/10 con el mismo handler terminan en carpetas distintas, con permiso de
  grupo. Falla con el handler anterior y pasa con el nuevo. El test que ya
  existía sigue pasando.
- `test_daily_file_handler_no_depende_de_timezone_now`: con `timezone.now`
  parcheado a un string, loguear no lanza. La primera versión del PR rompía
  3 tests de `comedores` que parchean `timezone.now` y loguean un error.
- black sin cambios; pylint 10/10.
- No verificado en PRD: se ve al día siguiente de desplegar.
