# Cambio: publicar, archivar y destacar comunicados en React sobre G1 v1 (#2785, CM02.03)

## Alcance

Tercera entrega del
[contrato CM01-CM03](../../../plans/2026-T4/2026-11-10-2785-comunicados-mailing-m2.md):
los botones «Publicar», «Archivar» y «Quitar destacado»/«Marcar como destacado» del
listado de gestión `/comunicados/gestion/` y del pie del detalle `/comunicados/ver/<pk>/`
dejan de enviar un formulario nativo y hacen un único POST a la API web. Crear, editar,
eliminar y mailing masivo siguen como estaban; el envío masivo sigue en el worker
nativo y no se envía correo. No cambia vistas, plantillas, modelos ni la API PWA
(`/api/comunicados/`). Las rutas nativas `POST /comunicados/publicar|archivar|toggle-destacado/<pk>/`
siguen respondiendo 302 a la gestión.

Archivos:

- `src/backends/comedores/comunicados/web_api_views.py` y `web_api_urls.py`: tres
  endpoints `POST /api/web/comedores/comunicados/<pk>/publicar/`, `/archivar/` y
  `/destacado/`. `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado) con las rutas nuevas.
- `src/frontends/apps/sisoc/src/routes/comunicados.tsx`: el botón envía una vez,
  espera y navega al `redirect` confirmado.
- Pruebas: `test_web_comunicados_acciones_api.py` y `routes/comunicados.test.tsx`.

## Comportamiento

Cada endpoint llama al `post()` de la vista nativa (`ComunicadoPublicarView`,
`ComunicadoArchivarView`, `ComunicadoToggleDestacadoView`): el permiso se evalúa antes
de buscar el objeto (sin permiso, un ID inexistente da 403 con el mensaje nativo; con
permiso, 404), las reglas de estado y los mensajes son los nativos (publicado repetido:
advertencia; archivado: error; destacado en borrador: error) y el destacado acepta
externos como la vista nativa. El 302 a la gestión se convierte en
`{"ok": true, "redirect": "/comunicados/gestion/"}` y el mensaje queda en cola: lo
devuelve el siguiente GET de gestión, que React muestra como toast. Acceso: G1 primero
(401 sin sesión, 403 de requisito web), CSRF obligatorio y solo POST (GET devuelve 405).

En React se conservan la confirmación («¿Publicar este comunicado?», «¿Archivar este
comunicado?»), el marcado y los títulos. El botón se deshabilita mientras espera, un
doble clic no genera dos POST y, ante 403, se muestra el mensaje nativo junto al botón.
Si no se puede confirmar el resultado se muestra «No se pudo confirmar el resultado.
Actualice la página antes de volver a intentar.» y no se reenvía.

## Verificación

Entorno sintético, sin red, imagen fijada: pruebas de backend por interfaz pública
(estado, JSON, permisos, mensajes, efectos persistidos, CSRF, 401/403/404/405) y la
suite existente de comunicados sin cambios; Vitest del proyecto, `tsc`, ESLint y build
de Vite; `black` y `pylint` 10/10; e2e G1 (core y runtime) y comparación visual
nativo/React de la gestión y del detalle (borrador y publicado) en escritorio y móvil.

## Limitaciones

- El resultado de una transición entre lectura y envío es el del nativo (mensaje de
  advertencia o error), sin 409 ni bloqueo.
- Diferencia del marco compartido (`SisocShell`): el logo tiene nombre accesible en
  React y cambia el primer elemento del orden de Tab.
