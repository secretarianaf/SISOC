# Cambio: listado de ciudadanos en React (#2785)

## Qué cambia

- **API.** `GET /api/web/ciudadanos/listar/` (`ciudadanos/web_api_listado.py`, montada en el core) corre
  `CiudadanosListView` con su `dispatch`: permiso `ciudadanos.view_ciudadano` (403), el formulario propio
  (estado de identidad y de revisión), los filtros combinables, el orden por `pk` y las páginas de 25 sin
  `COUNT`. Proyecta lo que imprimen `ciudadano_list.html` y `components/search_bar.html`: la configuración
  de filtros, los valores del formulario (con los rótulos y opciones del `Form`), las filas (texto de cada
  celda y valor `data-*` con el que ordena `listSort.js`), la identidad, la paginación con el prefijo de los
  enlaces, el permiso de exportar (`auth.role_exportar_a_csv` o superusuario), los botones adicionales
  («IMPORTACION MASIVA» solo con `ciudadanos.add_ciudadano`) y los mensajes en cola. Solo lee.
- **React.** `routes/ciudadanoListado.tsx` (`/ciudadanos/listar`) dibuja la barra de búsqueda con los
  filtros combinables (`Filters`), el formulario de identidad con su `GET` nativo (el estado de revisión se
  oculta y deshabilita fuera de «Todos», «Sin DNI» y «DNI no validado RENAPER»), la tabla con el orden local
  de `listSort.js` y la paginación de `pagination.html` («Volver»/«Continuar», sin total porque la página no
  tiene `COUNT`).
- **Exportación.** «Exportar búsqueda» sigue siendo la descarga nativa: navega a `/ciudadanos/exportar` con la
  consulta actual y el orden activo, como `export_helper.js`. No cambió la vista ni el CSV.
- La entrada local `ciudadanos/web_preview_listado.py` mantiene la URL nativa con sus guardas (login y
  permiso) y devuelve el índice React. Se agregó la ruta a `_OWNED_PATTERNS` y a `url_registry.json`.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red): proyección de filas y celdas, filtros del formulario (modo UI y
  modo API) y combinables, páginas de 25 y enlaces, permisos de exportar e importar, 401/403/405 y que mirar
  el listado no escribe; entrada de vista previa.
- Vitest, tsc y eslint sin avisos nuevos.
- G1 (core y runtime con gunicorn) y visual S13 contra la página nativa, escritorio y móvil.

## Limitaciones y diferencias conocidas

- #2946: se recuperó el enlace de importación masiva en Django y React. Antes, la clase `btn-export-csv`
  hacía que el manejador de exportación cancelara la navegación, y React reproducía esa cancelación.
  La clase `btn-import-xlsx` conserva el estilo sin disparar el exportador. El enlace conserva su URL y
  su permiso de alta; allí siguen aplicándose las validaciones de importación.
- La segunda página y el menú móvil quedan fuera de la comparación visual.

La prueba de importación masiva verifica la nueva clase visual del botón y sigue comprobando que no se muestra sin permiso.
