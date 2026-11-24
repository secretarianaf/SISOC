# Cambio: cola de revisión de identidad en React (#2785, C02)

## Qué cambia

- **API.** `GET /api/web/ciudadanos/revision/?estado=&page=`
  (`ciudadanos/web_api_cola_revision.py`, montada en el core) corre `ColaRevisionView` con su
  `dispatch`: permiso `ciudadanos.revision_identidad` (403) y el 404 del `ListView` para una
  página fuera de rango. Proyecta lo que imprime `cola_revision.html`: el filtro de estado
  (`pendiente` por omisión; un valor inválido cae en pendiente), los totales, las filas de la
  página de 25 (nombre, identificador, documento, tipo de registro, motivo con la descripción
  truncada a 60 caracteres, provincia y estado de la revisión) y la paginación. La resolución usa
  `POST /api/web/ciudadanos/<pk>/marcar-revisado/` (existente) y el nuevo
  `POST .../<pk>/descartar-revision/`, que corre la vista nativa `descartar_revision`: escribe
  `requiere_revision_manual=False` y el estado `APROBADA` o `DESCARTADA`, deja «Ciudadano <nombre>
  marcado como revisado.» o «... como descartado.» en cola y devuelve `next` (solo rutas internas;
  si no, la ficha) como `{"ok": true, "redirect": ...}`. Sin el permiso es 403, también para un id
  inexistente.
- **React.** `routes/ciudadanoColaRevision.tsx` (`/ciudadanos/revision/`) dibuja el encabezado con
  el conteo (singular y plural como `pluralize`), el filtro (cambia y envía el `GET` nativo), la tabla
  y la paginación de `pagination.html` con el filtro en los enlaces. Solo las filas pendientes
  muestran «Editar» (enlace nativo), «Revisado» y «Descartar»; ambas piden la confirmación del
  navegador, envían una sola vez con `next` y siguen la redirección con una navegación de página
  completa, de modo que el mensaje nativo aparece en la cola recargada. Un rechazo o un resultado
  no confirmado se informan sin reenviar.
- La entrada local `ciudadanos/web_preview_cola_revision.py` mantiene la URL nativa con sus guardas
  (login, permiso, 404 de página) y devuelve el índice React. Se agregaron las rutas a
  `_OWNED_PATTERNS` y a `url_registry.json`.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red): proyección de filas, motivos y totales, filtro y valor
  inválido, paginación y página inexistente, resolver con el efecto persistido exacto (estado y
  bandera) y su mensaje, `next` externo ignorado, 401, 403 (también para un id inexistente), 404, 405 y
  CSRF 403 sin cambios, y la entrada de vista previa.
- Vitest, tsc y eslint sin avisos nuevos.
- G1 (core y runtime con gunicorn) y visual S13 contra la página nativa, escritorio y móvil.

## Limitaciones y diferencias conocidas

- La confirmación de «Revisado» y «Descartar» sigue siendo `window.confirm`, igual que el `onsubmit` nativo.
- La edición del legajo (`ciudadanos/editar/<pk>`) ya está en React; el resto de la cola sigue sin
  acciones masivas, igual que la página nativa.
