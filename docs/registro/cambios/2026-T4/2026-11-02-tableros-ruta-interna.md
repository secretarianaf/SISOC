# Cambio: el menú "Tableros" puede enlazar a una pantalla de SISOC

## Alcance

Hasta ahora cada entrada del menú "Tableros" (`sisoc_core/dashboard`, modelo
`Tablero`) llevaba siempre a `/dashboard/<slug>/`, que embebe en un iframe la
URL cargada (Power BI o Looker Studio). Un tablero programado dentro de SISOC
no tenía forma de aparecer en ese menú.

Se agrega el campo opcional `Tablero.ruta_interna` (migración
`dashboard/0004_tablero_ruta_interna`). El primer uso previsto es el tablero de
Celiaquía en código (PR aparte). La forma (un campo en `Tablero` en lugar de
otro menú o un iframe de la propia pantalla) la propuso el agente: reusa el
mismo menú, los mismos permisos por grupo y el mismo admin.

Rutas: `src/backends/sisoc_core/dashboard/models.py`, `admin.py`, `views.py`.

## Comportamiento

- Con `ruta_interna` cargada, el menú enlaza a esa ruta y la marca como activa
  cuando se está en ella.
- Si alguien entra por `/dashboard/<slug>/` de un tablero con `ruta_interna`, y
  tiene permiso, se lo redirige a la ruta. Sin permiso sigue el 403 de siempre:
  el control de acceso corre antes de la redirección.
- Solo se aceptan rutas internas: tienen que empezar con `/`, y se rechazan
  `//…`, `/\…`, URLs con esquema (`https://…`) y espacios. Así el campo no
  puede usarse para mandar a otro sitio.
- Compatibilidad: el campo arranca vacío en todas las filas existentes, que
  siguen embebiendo su URL igual que antes.

## Verificación

- `pytest src/backends/sisoc_core/dashboard/tests.py`: 18 pasan (11 existentes
  y 7 nuevos): enlace con y sin ruta, menú y activo, redirección con permiso,
  403 sin permiso, rutas externas o mal formadas rechazadas en el modelo y en
  el formulario del admin.
- `black --check` y `pylint` sin observaciones en los archivos de código;
  `makemigrations --check`: sin cambios pendientes.
- Corrido en el entorno local con Docker. La verificación visual en el admin y
  el menú queda en las pruebas manuales del PR.
