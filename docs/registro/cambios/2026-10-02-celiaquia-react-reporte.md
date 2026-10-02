# 2026-10-02 - Reporte de Celiaquía en el front v2

## Qué se replicó

El reporte de `reporter-provincias/` en React, con todo lo que tenía: métricas
principales, las tres instancias de estado (revisión técnica, Sintys, cupo) con
sus resúmenes y porcentajes, la clasificación de aprobados, la tendencia
mensual, los expedientes por provincia, el detalle paginado y los 8 filtros
(provincia, rango de fechas, expediente, documento, revisión, Sintys, cupo).

## Cómo

**Las agregaciones no se reimplementaron.** Son 581 líneas de reglas finas:
qué cuenta como persona única, qué es una dupla, cómo se clasifica un aprobado.
Reescribirlas en TypeScript habría dado dos reportes que no cierran entre sí, y
el pedido era justamente que los resultados fueran correctos.

`celiaquia/views/reporter_provincias.py` eran 733 líneas: 21 funciones, 11
constantes y una vista de 7. Todo menos la vista se movió **verbatim** a
`celiaquia/services/reporte_service/`. La vista quedó en 21 líneas y reexporta
los helpers, que los tests importan desde ahí.

Se agregó `build_report_payload`, que llama a `build_report_context` entero y
solo aplana lo que no es JSON (el `Page` del paginador, el queryset de
provincias y los objetos de cada caso). No recalcula nada.

Endpoint: `GET /api/celiaquia/reporte/`, con los filtros como query params.

## Verificación de que los números son correctos

`celiaquia/tests/test_api_reporte.py` compara la API contra **el contexto del
template**, que es la referencia:

- totales, documentación OK/incompleta, casos con comentarios
- `casos_por_instancia` completo (los 11 contadores)
- los porcentajes, redondeados a 4 decimales
- la clasificación de aprobados, item por item
- que los filtros acoten igual
- que un usuario provincial solo vea su alcance

Además se corrió contra la base de desarrollo con tres filtros distintos
(sin filtro, `revision_tecnico=APROBADO`, `estado_cupo=NO_EVAL`): los totales,
porcentajes y conteos por instancia coinciden exactamente.

## Front

`ReportePage` en `/v2/celiaquia/reporte`, con su entrada en el Drawer. El
selector de provincia se oculta para usuarios provinciales, igual que en Django.

No suma ni promedia nada: todos los números salen del payload.

## Validación

- `pytest -n auto`: **5579 passed, 14 skipped**. 6 tests nuevos de paridad.
- Front: 62 tests; `lint`, `typecheck`, `build` y `api:check` en verde.
- `pylint` sobre el service nuevo: 9.91/10.
- El contrato quedó en **69 rutas**.
