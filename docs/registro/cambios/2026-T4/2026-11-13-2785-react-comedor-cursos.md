# Cambio: catálogo global de cursos de la app mobile en React sobre G1 v1 (#2785, CO04.01)

## Alcance

Tercera entrega de la lane K6 del contrato
[`2026-10-28-2785-comedores-colaboradores-actividades-catalogos.md`](../../../plans/2026-T4/2026-10-28-2785-comedores-colaboradores-actividades-catalogos.md):
listado, alta, edición y baja lógica de los cursos de la app mobile
(`/comedores/configuracion/cursos-app-mobile/`). Con esta entrega la lane queda
completa: los colaboradores y las actividades de un espacio van en sus
[propios registros](2026-11-13-2785-react-comedor-colaboradores.md) y el
catálogo PNUD ya estaba en
[`2026-11-10-2785-react-actividades-pnud.md`](2026-11-10-2785-react-actividades-pnud.md).
No activa React en producción y no cambia ninguna vista, formulario, modelo,
plantilla, ruta ni permiso nativo.

Archivos:

- `src/backends/comedores/comedores/web_api_cursos.py` y
  `web_api_cursos_urls.py`: API web.
- `src/backends/comedores/comedores/web_preview_cursos.py`: cuatro entradas de la
  vista previa local.
- `src/backends/comedores/comedores_runtime/web_api_urls.py`,
  `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/comedorCursos.tsx` y su prueba.
- Pruebas: `src/backends/comedores/comedores/tests/test_web_cursos_app_mobile_k6.py`
  y `test_web_preview_cursos_k6.py`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/comedores/cursos-app-mobile/` | Listado global nativo: 20 por página, columnas nombre, programa, link, orden, recomendado, estado e imagen (sí o no) |
| `GET/POST /api/web/comedores/cursos-app-mobile/crear/` | `CursoAppMobileForm` con la carga de imagen (multipart); el POST fija creador y modificador en una transacción |
| `GET/POST /api/web/comedores/cursos-app-mobile/<pk>/editar/` | Mismo formulario con los valores actuales; el POST fija el modificador |
| `GET/POST /api/web/comedores/cursos-app-mobile/<pk>/eliminar/` | Confirmación; el POST es la baja lógica nativa (`deleted_at`, `deleted_by`), no `activo=False` |

Cada endpoint ejecuta el `dispatch` de la vista nativa
(`comedores/views/cursos_app_mobile.py`). Una redirección nativa se devuelve como
`{"ok": true, "redirect": ...}` y un formulario inválido como 400 con los errores
de Django; un rechazo no escribe nada. Solo se aceptan POST
`application/x-www-form-urlencoded` o `multipart/form-data` (otro formato responde
415) y las escrituras exigen CSRF. Una página fuera de rango, un curso inexistente
o ya dado de baja responden 404.

Acceso, en este orden: G1 y `auth.role_admin`, como la URL nativa. Sin cambios
respecto de hoy.

Mensajes nativos conservados: «Curso para app mobile creado correctamente.»,
«Curso para app mobile actualizado correctamente.» y, en la baja, los dos que
encola la vista: «Baja lógica realizada correctamente.» y «Curso para app mobile
eliminado correctamente.».

Pantalla React: mismo marcado que las tres plantillas. El formulario usa el
`form.as_p` de Django (etiqueta con «:», lista de errores antes del párrafo) y,
como la plantilla, no es `novalidate`: el navegador valida los campos
obligatorios antes de enviar. La imagen viaja como parte del multipart. Los
mensajes se ven como toast al final de `<body>`, como en la plantilla base.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 11 pruebas de la API y 2 de la vista previa (acceso, CSRF y 415,
  paginado de 20, proyección de columnas, alta con imagen real, alta sin
  imagen ni indicadores, todas las causas de rechazo sin escritura, edición con
  sello de modificador, baja lógica con sus dos mensajes y 404 posterior).
- Frontend: 9 pruebas de la ruta, Vitest del workspace, `tsc`, ESLint y build.
- Visual (regla S13), nativo contra React, 5 estados (listado, alta, alta
  rechazada por el servidor, edición, baja) en 1440x900 y 390x844, y las guardas.
- G1 de punta a punta en dos contenedores gunicorn, con el alta en multipart como
  lo envía el navegador.

## Limitaciones

- No se prueba la transformación física de la imagen (`IMAGE_SIZE` 96x96): el
  productor que la usa no se leyó en esta entrega y sigue pendiente, como indica
  el contrato.
- No se comprueba la conexión con los enlaces ni el consumo de las imágenes por
  la app mobile.
