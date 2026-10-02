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
