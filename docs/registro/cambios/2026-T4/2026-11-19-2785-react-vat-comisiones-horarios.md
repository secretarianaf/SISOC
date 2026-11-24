# Cambio: lista y detalle de horarios de comisión de oferta de VAT en React (#2785, V04.01)

## Qué cambia

- **API.** `GET /api/web/vat/comisiones-horarios/` y `GET /api/web/vat/comisiones-horarios/<pk>/`
  (`VAT/web_api_comision_horario_lista.py`) corren `ComisionHorarioListView` y `ComisionHorarioDetailView` y proyectan
  el texto que imprimen `horario_list.html` y `horario_detail.html` (`H:i`, `d/m/Y H:i`, `—` en el aula vacía), los
  permisos de edición y baja, las URLs nativas, la paginación y los mensajes en cola. Acceso: `VAT.view_comisionhorario`,
  igual que la ruta nativa; el alcance, los filtros `comision_id` y `dia_semana` y los 404 (objeto fuera del alcance,
  página no válida) son los de las vistas nativas. Comparte el prefijo con las altas, ediciones y bajas ya migradas.
- **React.** `routes/vatComisionHorarios.tsx` (rutas `/vat/comisiones/horarios/` y `/vat/comisiones/horarios/<pk>/`)
  dibuja el buscador, la tabla ordenable por comisión, la insignia de vigencia, los botones según permiso y la
  paginación; el detalle dibuja la información, la auditoría y las acciones «Editar» y «Eliminar» (que la plantilla
  muestra a todos).
- La entrada local `VAT/web_preview_vat_comision_horarios.py` conserva la ruta, el permiso y el 404 nativos antes de
  servir el índice React. Se agregaron las rutas a `_OWNED_PATTERNS` de `admindocs.py` y a `url_registry.json`.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red): 401, 403, alcance, filas, filtros, página no válida, coincidencia con el
  texto de las páginas nativas, convivencia con las rutas de formularios, 405 y entradas de vista previa.
- Vitest, tsc y eslint; G1 (núcleo y runtime) y visual S13 contra las páginas nativas (escritorio y móvil).

## Limitaciones y diferencias conocidas

- El campo de búsqueda de la lista se envía como `busqueda`, pero la vista nativa no lo usa: no filtra, igual que en
  la página nativa.
- El bloque «Observaciones» de la plantilla de detalle no se dibuja: `ComisionHorario` no tiene ese campo, así que la
  página nativa tampoco lo muestra nunca.
- Los horarios de comisiones de curso no tienen lista ni detalle nativos (`comision_id` nulo queda fuera del queryset).
