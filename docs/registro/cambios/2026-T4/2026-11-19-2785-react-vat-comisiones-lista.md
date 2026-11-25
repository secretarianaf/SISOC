# Cambio: lista de comisiones de oferta de VAT en React (#2785, V04.01)

## Qué cambia

- **API.** `GET /api/web/vat/comisiones-lista/` (`VAT/web_api_comision_lista.py`, `ComisionListWebView`) corre
  `ComisionListView` y proyecta las filas con el texto que imprime `comision_list.html` (`d/m/Y`, `—` en la fecha
  vacía, estado legible), los permisos de edición y baja, las URLs nativas, la paginación y los mensajes en cola.
  Acceso: `VAT.view_comision`, igual que la ruta nativa; el alcance, los filtros `estado` y `oferta_id` y el 404
  de página no válida son los de la vista nativa. El prefijo no es `comisiones/` porque ese recurso es del front INET.
- **React.** `routes/vatComisionLista.tsx` (ruta `/vat/comisiones/`) dibuja el buscador, la tabla ordenable por código
  y nombre, las insignias por estado, los botones «Ver», «Editar» y «Eliminar» según permiso, la paginación y el
  ayudante del recorrido guiado de la sección `comision_list`.
- La entrada local `VAT/web_preview_vat_comision_lista.py` conserva la ruta, el permiso y el 404 nativos antes de
  servir el índice React. Se agregó la ruta a `_OWNED_PATTERNS` de `admindocs.py` y a `url_registry.json`.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red): 401, 403, alcance, filas, filtros, página no válida, paginación,
  coincidencia con el texto de la página nativa, 405 y entrada de vista previa.
- Vitest, tsc y eslint; G1 (núcleo y runtime) y visual S13 contra la página nativa (escritorio y móvil).

## Limitaciones y diferencias conocidas

- #2946: se corrigió el 500 de la búsqueda por texto (`busqueda`, `q`) en la vista nativa compartida.
  La consulta usaba `oferta__nombre`, que no existe. Busca por código y nombre de la comisión,
  y por nombre local de la oferta, nombre del plan o títulos asociados cuando no hay un nombre
  más específico. Conserva el alcance del solicitante y elimina duplicados antes de paginar.
  Las regresiones cubren HTML y JSON con fixtures sintéticos; no cambian la URL ni el frontend.
- `/vat/cursos/comisiones/<id>/resultados/` es solo POST (guarda el acta): no tiene página que migrar.
