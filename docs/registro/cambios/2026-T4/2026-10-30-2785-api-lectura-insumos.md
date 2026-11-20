# Cambio: API de lectura de Insumos (#2785)

## Alcance

Se implementan los endpoints locales `GET`/`HEAD` `/api/web/insumos/` y
`/api/web/insumos/options/` para la lectura de INS-A. El circuito de creación,
edición y eliminación queda fuera de esta unidad y no se modifica la descarga
protegida Django. El dueño del código es `sisoc_core/insumos`.

## Comportamiento

- Ambos endpoints usan sesión Django, resuelven los requisitos de acceso web y
  requieren `insumos.view_insumo` en cada petición. Add, Change y Delete no
  otorgan implícitamente permiso de lectura.
- El listado reutiliza `get_insumos_queryset()` para conservar las relaciones y
  el orden existentes. `busqueda` busca en título o descripción; `categoria=sin`
  selecciona categoría nula y un ID numérico filtra por categoría. Los valores
  no numéricos de `categoria` se ignoran como en la vista heredada. La respuesta
  expone página, conteo y filtros aplicados, con 20 filas por página.
- El DTO de fila contiene solo ID, título, estado activo, categoría visible,
  fecha local formateada, persona que cargó y la ruta backend protegida de
  descarga. No expone rutas de almacenamiento.
- `options/` devuelve solo categorías activas, en el orden de
  `get_categorias_queryset()`. No exige permisos de administración de categorías.
- La middleware XView permite que `HEAD` de las dos rutas API nuevas llegue a
  Django REST Framework, además de la excepción previa de sesión. En otras rutas
  y métodos conserva la delegación al middleware upstream.

## Verificación

Se observaron RED para búsqueda/categoría y opciones antes de implementarlas;
después, los grupos focalizados de filtros y opciones pasaron. La prueba focal
completa del API pasó con 33 casos y 100% de cobertura en las dos vistas/DTOs.
También pasó la regresión combinada de Insumos heredado, sesión/readiness,
navegación, proxy, resolución URL, integridad y servicios del core: 1044 casos.
Pylint calificó los seis módulos Python con 10/10; Black normalizó los cinco
archivos Python propiedad de esta unidad. Se regeneró `url_registry.json` con
2804 rutas: el delta contiene solo `web_insumos_list` y `web_insumos_options`.
El verificador documental halló 0 referencias obsoletas o rotas.

Las pruebas se ejecutaron en la imagen local aislada, sin red, con base sintética
SQLite y almacenamiento temporal. Pytest reportó 23 advertencias preexistentes
de Django, WeasyPrint y paginación de otra vista; no hubo fallos.

Esta unidad no implementa aún la interfaz React completa, altas/cambios/bajas ni
aceptación visual/humana de INS-A.
