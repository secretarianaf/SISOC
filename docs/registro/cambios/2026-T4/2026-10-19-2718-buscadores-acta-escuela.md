# Inspecciones escolares: buscadores por número de acta y por escuela

Fecha: 2026-10-19. Relacionado con #2718 (puntos 1 y 3).

## Alcance

- Actas: campo «Buscar por número de acta» en la barra de filtros.
- Asignaciones: filtro «Buscar por escuela», equivalente al de inspector.

## Cambio

- `inspecciones_actas` acepta `numero`: coincidencia parcial o completa, sin
  distinguir mayúsculas (`ACTA-2026-000230` o `230`), combinable con fecha,
  inspector, provincia y estado. Vacío, vuelve al listado según los demás
  filtros. Sin coincidencias, muestra «No hay actas con los filtros elegidos.».
- `inspecciones_asignaciones` acepta `escuela` (id): Select2 con la misma
  búsqueda AJAX que el alta de asignaciones (nombre, Cueanexo o domicilio, desde
  3 letras), combinable con jornada, inspector, provincia y estados. Sin
  coincidencias, muestra el vacío existente de la jornada.
- La lógica está en `services/panel_actas.py::listar_actas_panel`,
  `services/asignaciones.py::asignaciones_de_jornada` y
  `services/catalogo.py::opcion_escuela_por_id`. No hay rutas ni modelos nuevos.

## Verificación

- Tests nuevos en `src/backends/inspecciones/tests/test_inspecciones_panel.py`
  (búsqueda parcial/completa, combinación con filtros, vacío y filtro por escuela).
- `pytest src/backends/inspecciones`, `black --check` y `djlint --check`.
