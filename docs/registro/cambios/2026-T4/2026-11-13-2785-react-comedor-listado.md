# Cambio: listado y baja de comedores en React (#2785, CO07.01)

## Qué cambia

- **API.** `GET /api/web/comedores/comedores/` (`src/backends/comedores/comedores/web_api_comedores.py`,
  incluida desde `src/backends/comedores/comedores_runtime/web_api_urls.py`) corre
  `ComedorListView` con su `setup()`, su queryset (alcance del usuario y filtros avanzados),
  `NoCountPaginator` y las preferencias de columnas, y proyecta el contexto de
  `comedor_list.html` y `components/comedor_table.html`: migas, configuración de filtros,
  columnas activas, filas con los mismos valores por defecto («Sin información», «S/N», etc.),
  enlaces de ver, editar y eliminar, botón de exportar y paginación por ventana sin total.
  Acceso igual que hoy: `view_comedor`, `view_admision` o `view_informacionrelevante`
  (cualquiera de las tres). Es de solo lectura: la exportación CSV, el alta, la edición y la
  baja siguen siendo las páginas nativas.
- **React.** `src/frontends/apps/sisoc/src/routes/comedores.tsx` (`/comedores/listar`) dibuja
  la barra de filtros, el botón «Agregar», el modal de columnas y la tabla con el orden en el
  navegador de «Nombre» y «Validación» (como `listSort.js`: ascendente, descendente y vuelta
  al orden de la página).
- `src/backends/comedores/comedores/web_preview_comedores.py` mantiene la URL nativa con sus
  guardas y devuelve el índice React. Se agregó la ruta a `_OWNED_PATTERNS` y a
  `url_registry.json`.

- **Baja.** `GET/POST /api/web/comedores/comedores/<pk>/baja/` corre `ComedorDeleteView`:
  `comedores.delete_comedor`, alcance del usuario (fuera de alcance es 404), vista previa de la
  cascada, baja lógica con el actor y el mensaje nativo «Comedor dado de baja correctamente.»,
  que queda en cola para el listado al que redirige. `routes/comedorBaja.tsx`
  (`/comedores/<pk>/eliminar`) dibuja la confirmación con los textos nativos; si el POST falla
  o no se puede confirmar, la página queda con un error y no reintenta. La entrada de vista
  previa suma esa URL (el POST nativo sigue siendo nativo).

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red): columnas por defecto, paginación por ventana sin
  total, filtros avanzados, búsqueda sin resultados (regresión: la página vacía no trae
  `page_range`), botón de exportar según rol, 401, 403, 405, cada permiso de acceso y que
  leer no escribe; baja con efecto persistido (fila dada de baja con actor y fecha, mensaje
  para el listado) y sin cambios ante permiso faltante, 404, CSRF, método no servido o
  sesión pendiente; entrada de vista previa; pruebas del core (gate, proxy, servicios).
- Vitest, tsc y eslint sin avisos. G1 y visual S13 contra la página nativa (listado y
  búsqueda sin resultados y confirmación de baja, escritorio y móvil; G1 incluye la baja y
  que el comedor deja de existir).

## Limitaciones y diferencias conocidas

- La ficha (`/comedores/<id>`) y los formularios de alta y edición siguen en Django; el
  enlace «Cancelar» de la baja lleva a la ficha nativa.
- La página 2 no se comparó visualmente (exenta por la regla de la migración).
