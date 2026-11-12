# Cambio: contadores del listado de comisiones INET sin cruce de tablas (#2889)

## Alcance

`/api/inet/comisiones/` respondía 504 en PRD. El listado calculaba `inscriptos_count`, `clases_count` y `clases_realizadas` con `Count(..., distinct=True)` sobre dos relaciones a la vez (inscripciones y sesiones). Con eso, MySQL cruzaba inscripciones × sesiones de todas las comisiones y armaba una tabla temporal antes de aplicar el `LIMIT`.

El `EXPLAIN` en PRD muestra `Using temporary; Using filesort` sobre `VAT_comisioncurso`. Los datos de PRD:

| Dato | Valor |
|---|---|
| Comisiones | 10.313 |
| Inscripciones | 47.392 |
| Sesiones | 512.014 |
| Comisión más pesada | 49.378 filas cruzadas (3.527 inscripciones × 14 sesiones) |

Ruta: `src/backends/vat/VAT/services/inet_queries.py` (`_contar_por_comision` y `resource_queryset`).

## Comportamiento

- Cada contador es una subconsulta por comisión, así que solo se calcula para las filas de la página. La consulta principal ya no se une a inscripciones ni a sesiones, ni agrupa.
- Los números no cambian. Las inscripciones se cuentan con `all_objects`, igual que el `Count` por relación anterior, que no excluía las bajas lógicas.
- El contrato de la API y el frontend INET no cambian.

## Verificación

Validado en local, con SQLite en los tests y el MySQL local para el plan:

- `src/backends/vat/tests/test_inet_api.py`: 34 tests pasan. El test nuevo `test_commission_counters_match_and_are_not_grouped` verifica los tres contadores y que la consulta no agrupe por comisión. Con el código anterior falla.
- `pytest src/backends/vat -n auto`: 580 pasan, 4 se saltean y 2 fallan. Los 2 fallos son `test_listado_de_vouchers_sin_n_mas_1` y `test_listado_de_inscripciones_sin_n_mas_1`, de `src/backends/vat/tests/test_admin_operaciones_vat.py`. Son preexistentes: con el código de `HEAD` dan el mismo resultado.
- `pylint` da 10/10 en `inet_queries.py`.
- `EXPLAIN` en el MySQL local: la consulta principal ya no usa tabla temporal ni filesort.

Sin verificar:

- El `EXPLAIN` y el tiempo de la consulta nueva con datos de PRD.
- El endpoint desplegado en HML.
