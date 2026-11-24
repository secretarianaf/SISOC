# Cambio: alta y edición de comunicados en React sobre G1 v1 (#2785, CM02.02: crear y editar)

## Alcance

Quinta entrega del
[contrato CM01-CM03](../../../plans/2026-T4/2026-11-10-2785-comunicados-mailing-m2.md):
los formularios `/comunicados/crear/` y `/comunicados/editar/<pk>/`
(`comunicado_form.html`, `comunicadosForm.js`, `comunicadosDestinatarios.js`), el panel de
destinatarios con filtros combinables y los endpoints de búsqueda que usa. El mailing masivo
sigue en las pantallas nativas y su envío en el worker nativo; no se envía correo. No cambia
vistas, plantillas, modelos, formularios ni la API PWA. Las rutas nativas siguen respondiendo
igual (POST de alta: 302 a la gestión).

Archivos:

- `src/backends/comedores/comunicados/web_api_views.py`, `web_api_serializers.py` y
  `web_api_urls.py`: `GET` y `POST /api/web/comedores/comunicados/crear/` y
  `.../<pk>/editar/`, y `GET .../destinatarios/<universo>/buscar/` y `.../todos/`.
  `src/backends/config/middlewares/admindocs.py` y `src/backends/config/url_registry.json`
  (regenerado) con las rutas nuevas.
- `src/backends/comedores/comunicados/web_preview.py`: entradas de vista previa local.
- `src/frontends/apps/sisoc/src/routes/comunicadosForm.tsx`, `comunicadosDestinatarios.tsx` y
  rutas en `comunicados.tsx`.
- Pruebas: `test_web_comunicados_formulario_api.py`, `test_web_preview_comunicados.py`,
  `routes/comunicadosForm.test.tsx`.

## Comportamiento

El GET ejecuta `get_context_data()` de `ComunicadoCreateView` o `ComunicadoUpdateView` y
devuelve lo que imprime la plantilla: valor, obligatoriedad, opciones efectivas y errores de
cada campo (el técnico ve solo «Comunicación Externa» y los subtipos de comedores y
organizaciones; su «destacado» es un campo oculto), el management form del formset de
adjuntos, los adjuntos actuales con su casilla «Eliminar», el panel «Información» (edición),
la configuración de filtros y las etiquetas de la selección previa. El POST (multipart o
urlencoded; JSON da 415) ejecuta el `post()` de la vista nativa: mismos permisos y orden de
chequeos (crear: 403 en GET y POST; editar: 404 y luego 403; el editor no administrador solo
edita borradores), mismo `ComunicadoForm`, mismo formset y el mismo guardado atómico con
`_handle_comedores`. Un 302 se devuelve como `{"ok": true, "redirect": "/comunicados/gestion/"}`
y el mensaje nativo queda en cola; si el formulario o el formset se rechazan, 400 con el
formulario ligado (valores y errores). Los destinatarios llaman a las vistas nativas y
devuelven su JSON sin cambios (mismo 403 y 404 `{"error": "Universo desconocido."}`).

React reproduce el DOM, los textos y la visibilidad condicional del nativo (subtipo, destacado,
paneles de destinatarios y selector oculto con «para todos»). Los IDs elegidos viajan en un solo
input oculto con CSV por universo. Los archivos se envían como `archivos_adjuntos` repetido.
El botón se deshabilita mientras espera y no se reenvía; si el resultado no se puede confirmar
se muestra «No se pudo confirmar el resultado. Revise la gestión de comunicados antes de volver
a guardar.». Tras un rechazo, la pantalla vuelve arriba y conserva los valores y la selección.

## Verificación

Entorno sintético, sin red, imagen fijada: pruebas de backend por interfaz pública (estado,
JSON, permisos, validaciones y mensajes nativos, alcance del técnico, efectos persistidos,
CSRF, 415) y suite existente de comunicados sin cambios; Vitest del proyecto, `tsc`, ESLint y
build de Vite; `black` y `pylint`; e2e G1 y comparación visual nativo/React del formulario
(alta, búsqueda de destinatarios, error del servidor y edición) en escritorio y móvil.

## Limitaciones

- Los errores de `archivos_adjuntos` (extensión y tamaño) y del formset no se dibujan, igual
  que la plantilla nativa (que no los imprime); la API los devuelve en `attachment_errors` y
  `formset_errors`. Queda para decisión de producto mostrarlos.
- El nativo con JavaScript y archivos recarga la página tras un rechazo y pierde los errores;
  React muestra los errores del servidor (equivale al envío sin JavaScript) y conserva los
  archivos elegidos.
- Subidas grandes (varios adjuntos de hasta 10 MB) pueden superar la ventana del core: ante un
  resultado no confirmado se avisa y no se reenvía.
- Diferencia del marco compartido (`SisocShell`): el logo tiene nombre accesible en React y
  cambia el primer elemento del orden de Tab.
