# Cambio: importación masiva de usuarios en React (#2785, U05)

## Alcance

Se implementa la unidad U05 del contrato
`docs/plans/2026-T4/2026-10-28-2785-usuarios-lotes-importacion-m2.md`: el
gestor masivo `/usuarios/importar/` y el detalle de lote
`/usuarios/importar/lotes/<id>/`, como transporte de sesión y pantalla React.
No se activa React globalmente: las rutas HTML de producción, la plantilla, la
descarga CSV, el Form y los servicios de lotes no cambian.

Archivos:

- `src/backends/sisoc_core/usuarios/web_user_import.py`: transporte JSON sobre
  las vistas nativas de `usuarios/views_user_import.py`. El alta usa
  `UserImportForm` y `create_user_import_job`; la reanudación usa la vista
  nativa `UserImportJobResumeView`. Son los únicos escritores.
- `src/backends/sisoc_core/usuarios/web_user_import_urls.py`: rutas
  `/api/web/users/import/`, `/api/web/users/import/jobs/<id>/` y
  `/api/web/users/import/jobs/<id>/resume/`, incluidas con una sola línea desde
  `usuarios/web_api_urls.py`; sus entradas en
  `src/backends/config/url_registry.json` se generaron con
  `generar_registro_urls`.
- `src/backends/config/middlewares/admindocs.py`: las tres rutas se suman a
  `_OWNED_PATTERNS`, donde HEAD responde la API y no el diagnóstico `X-View`.
- `src/backends/sisoc_core/usuarios/identity_preview.py`: entradas del URLconf
  sintético local para el formulario y el detalle, con la misma guarda
  `auth.add_user` y el 404 del lote antes de servir la UI.
- `src/frontends/apps/sisoc/src/routes/userImport.tsx` y su prueba, registrada
  en `routes/index.ts`; `identityFrames.tsx` agrega `userJobsFrame`.

## Comportamiento

Guarda: sesión lista (si falta un requisito de acceso responde 401/403 con el
requisito) y permiso `auth.add_user`, con el bypass existente de superusuario,
antes de buscar el lote. `GET /api/web/users/import/` devuelve los campos
reales del Form (`archivo` obligatorio `.xlsx`, `enviar_credenciales` inicial
verdadero, `es_pwa` inicial falso), la URL de la plantilla y el historial
reciente propio. El POST multipart con CSRF solo encola: un archivo válido
guarda el lote y sus filas `pending` y responde
`{"ok": true, "redirect": "/usuarios/importar/lotes/<id>/"}`; no hay etapa de
confirmación ni deduplicación (repetir el POST crea otro lote). Errores del
Form o del libro: 400 con los errores sobre `archivo`.

Detalle: 50 filas por página ordenadas por fila e id, con `estado` y `page`
conservados, contadores, último error, reanudaciones y estado del lote. Leer el
estado nunca inicia ni reintenta el lote; React consulta una vez por carga y
«Actualizar estado» recarga la página. El detalle y la reanudación no se
limitan al solicitante, igual que la fuente. La reanudación es un POST
URL-encoded que solo pasa `failed` a `pending` conservando el punto de
control; en otro estado informa el error nativo sin cambios. React no la
reintenta: ante un resultado no confirmado lo informa y deshabilita el botón.

El CSV sensible sigue en la ruta nativa
`/usuarios/importar/lotes/<id>/descargar-csv/` (solo solicitante o
superusuario, 404 para otros). El DTO solo indica el enlace cuando existen
filas creadas; ninguna respuesta ni aviso incluye contraseñas.

Las fechas usan la hora local y el formato `d/m/Y H:i` de los templates. React
reproduce el marcado de `user/user_import_form.html` y
`user/user_import_job_detail.html`, carga `hitos.css` como la base nativa y,
tras un 400, vuelve al inicio de la página y del recorrido con Tab, como la
recarga nativa.

## Verificación

Local y sintética, sin datos reales ni envío de correo:

- Backend (imagen fijada): RED de la hora local (la API mostraba UTC) y luego
  GREEN; `test_web_user_import.py`, `test_identity_preview.py` y las suites de
  usuarios, importación, credenciales masivas, sesión web, admin y
  `registro_de_urls_al_dia`: 312 pasan, 2 omitidas. black, pylint 10/10 y
  `makemigrations --check` sin cambios.
- Diferencial HEAD vs candidato (1332 solicitudes, 9 actores, rutas `/api/web`
  existentes y páginas HTML de importación y credenciales): 0 diferencias fuera
  de las rutas nuevas salvo el largo variable del XLSX de plantilla generado,
  que también varía entre corridas de la misma base. Los efectos de alta y
  reanudación por API son iguales a los del HTML.
- Frontend: RED de las corridas de texto, la hoja `hitos.css` y el foco tras
  400; vitest del workspace, tsc, eslint y build de Vite pasan.
- Visual (escritorio 1440x900 y móvil 390x844; formulario con y sin historial,
  error de validación y detalle pendiente, en proceso, completado, con errores,
  fallido y filtrado): 0 píxeles de diferencia y geometría idéntica en los 18
  casos. Diferencias de Tab fuera de la pantalla: nombre accesible del logo y
  `aria-label` del botón de menú móvil del marco compartido (preexistentes), y
  «Volver» del detalle apunta a `/` en lugar de `/usuarios/importar/`, porque
  el marco compartido no recibe destino propio (pendiente de ajuste en
  `routes/SisocShell.tsx`).

No se probó en navegador una carga real con worker ni el envío de correo; lo
cubren las pruebas de componente y backend. Falta la prueba humana.
