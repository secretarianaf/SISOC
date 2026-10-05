# 2026-10-02 - Celiaquía React: asignar cupo a una provincia

## El hueco

`GET /api/celiaquia/cupos/` devuelve los `ProvinciaCupo` que **existen**, así
que una provincia sin cupo no aparecía en la pantalla React y no había forma de
asignarle uno.

La pantalla Django sí las lista: arma el cuadro con las configuradas y después
agrega las que no tienen, con los contadores en `None`. Son 23 de 24 provincias
en la base de desarrollo.

## Cambios

El armado de filas vivía en `CupoDashboardView.get`. Se extrajo a
`CupoService.filas_dashboard`, que devuelve una fila por cada provincia con
`cupo_id` y contadores en `None` para las no configuradas. La vista Django
delega, así que las dos pantallas listan lo mismo por construcción.

Endpoint nuevo: `GET cupos/dashboard/`. El listado principal queda como está
—es el CRUD de `ProvinciaCupo`— y este es el cuadro.

En React, el dashboard usa ese endpoint y ofrece **"Asignar cupo"** en las
provincias sin configurar y **"Editar"** en las que ya tienen, las dos sobre el
mismo modal. "Ver" solo aparece en las configuradas, porque el detalle necesita
un `ProvinciaCupo`.

Un detalle que importa: el modal manda `provincia_id`, no `cupo_id`. Una
provincia sin cupo no tiene `cupo_id`, y `configurar` espera el id de provincia.
Hay un test que lo fija.

## Verificación

Contra la base de desarrollo: se asignó cupo a una provincia sin configurar,
se creó el `ProvinciaCupo` (0 → 1 registros), el dashboard pasó a mostrarla como
configurada con el total correcto, y después se eliminó el registro de prueba.

- `pytest -n auto`: **5581 passed, 14 skipped**. 2 tests nuevos.
- Front: **67 tests**, 5 nuevos sobre el cuadro de cupos.
- `lint`, `typecheck`, `build` y `api:check` en verde.

## Tope del cupo

Cargar un número grande tiraba un 500: `ProvinciaCupo.total_asignado` es un
`PositiveIntegerField` y en MySQL la columna es `UNSIGNED INT`, con tope
4.294.967.295. Pasarse hacía que la base devolviera
`DataError: Out of range value for column 'total_asignado'`, una excepción sin
manejar.

El tope **se deriva del propio campo**, leyendo su `MaxValueValidator`
(`TOTAL_ASIGNADO_MAXIMO` en `cupo_service`). Hardcodear 4.294.967.295
significaría que si el campo cambia de tipo, el límite queda viejo y vuelve el
error.

Se valida en tres lugares, y cada uno cubre una entrada distinta:

| Dónde | Qué cubre |
| --- | --- |
| `ConfigurarCupoSerializer` | la API: devuelve 400 con el error en el campo |
| `CupoService.configurar_total` | la pantalla Django, que entra por el service |
| El input de React | avisa mientras se escribe, sin viaje al servidor |

Verificado por los bordes: 4.294.967.295 se acepta, 4.294.967.296 da 400. El
front deshabilita Guardar y muestra el rango; también rechaza decimales, porque
la columna guarda enteros.
