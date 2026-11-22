# Cambio: credenciales masivas en React (#2785, U04)

## Alcance

Se implementa la unidad U04 del contrato
`docs/plans/2026-T4/2026-10-28-2785-usuarios-lotes-importacion-m2.md`: la
carga `/usuarios/credenciales-masivas/` y el detalle de lote
`/usuarios/credenciales-masivas/lotes/<id>/`, como transporte de sesión y
pantalla React. Se apoya en la unidad U05
(`2026-11-06-2785-react-importacion-usuarios.md`) y reutiliza su transporte,
marco y controles. No se activa React globalmente: las rutas HTML, la
plantilla, el Form, el worker y el envío de correo no cambian.

Archivos:

- `src/backends/sisoc_core/usuarios/web_bulk_credentials.py`: transporte JSON
  que hereda de las vistas nativas de `usuarios/views.py`
  (`BulkCredentialsUploadView`, `BulkCredentialsJobDetailView`,
  `BulkCredentialsJobResumeView`). El alta conserva el `form_valid` nativo
  (`create_bulk_credentials_job`, mensaje y redirección); el detalle convierte
  en JSON el mismo contexto que arma la vista nativa.
- `src/backends/sisoc_core/usuarios/web_bulk_credentials_urls.py`: rutas
  `/api/web/users/bulk-credentials/`, `.../jobs/<id>/` y
  `.../jobs/<id>/resume/`, incluidas con una sola línea desde
  `usuarios/web_api_urls.py`; entradas en
  `src/backends/config/url_registry.json` generadas con `generar_registro_urls`.
- `src/backends/config/middlewares/admindocs.py`: las rutas se suman a
  `_OWNED_PATTERNS`.
- `src/backends/sisoc_core/usuarios/identity_preview.py`: entradas del URLconf
  sintético local con la misma guarda que la URL nativa.
- `src/frontends/apps/sisoc/src/routes/bulkCredentials.tsx` y su prueba,
  registrada en `routes/index.ts`.

## Comportamiento

Guarda: sesión lista y, a la vez, `auth.change_user` y
`auth.role_enviar_credenciales_masivas`, con el bypass existente de
superusuario, antes de buscar el lote. `GET /api/web/users/bulk-credentials/`
devuelve el título, los campos reales del Form (`tipo_envio` con sus opciones,
inicial `standard`; `archivo` `.xlsx`), los tipos de envío con sus encabezados
y el historial reciente propio. El POST multipart con CSRF valida el libro antes
de crear el lote y responde
`{"ok": true, "redirect": "/usuarios/credenciales-masivas/lotes/<id>/"}`; un
error del Form o del libro responde 400 conservando el tipo elegido. Repetir el
POST crea otro lote. «Descargar plantilla» sigue siendo el envío GET nativo del
formulario a `/usuarios/credenciales-masivas/plantilla/`.

Detalle: 50 filas por página ordenadas por fila e id, contadores, último
usuario enviado e intentado, último error y reanudaciones. Leer el estado nunca
inicia ni reintenta el lote; React consulta una vez por carga y «Actualizar
estado» recarga la página. Detalle y reanudación no se limitan al solicitante,
igual que la fuente; no se agrega descarga ni cancelación. La reanudación es un
POST URL-encoded que solo pasa `failed` a `pending` con su punto de control y
contador; React no la reintenta. Ninguna respuesta ni aviso incluye contraseñas
ni el indicador `password_actualizada`.

React reproduce `user/bulk_credentials_form.html` y
`user/bulk_credentials_job_detail.html`, con la hora local y el formato
`d/m/Y H:i` de los templates.

## Verificación

Local y sintética, sin datos reales ni envío de correo:

- Backend (imagen fijada): RED de las 22 pruebas nuevas (rutas inexistentes) y
  de la entrada local (`test_identity_preview.py`), luego GREEN. Con las suites
  de usuarios, importación, credenciales, sesión web, admin y
  `registro_de_urls_al_dia`: 335 pasan, 2 omitidas. black, pylint 10/10 y
  `makemigrations --check` sin cambios.
- Diferencial HEAD vs candidato (1332 solicitudes, 9 actores): 0 diferencias
  fuera de las rutas nuevas salvo el largo del XLSX de plantilla, que también
  varía entre dos corridas de la misma base. Alta y reanudación por API dejan el
  lote y sus filas igual que el HTML.
- Frontend: RED de la ruta y la pantalla; vitest del workspace, tsc, eslint y
  build de Vite pasan.
- Visual (escritorio y móvil; formulario con y sin historial, error de
  validación y detalle pendiente, en proceso, completado y fallido): 0 píxeles
  de diferencia y geometría idéntica en los 14 casos. La descarga de plantilla
  en navegador produce la misma URL y archivo que la página nativa. Diferencias
  de Tab fuera de la pantalla, iguales a U05: nombre del logo y del botón de
  menú móvil del marco compartido, y «Volver» del detalle apunta a `/` en lugar
  de `/usuarios/credenciales-masivas/`.

No se probó en navegador una carga real con worker ni el envío de correo. Falta
la prueba humana.
