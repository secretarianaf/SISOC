# Cambio: confirmación y baja de comunicados en React sobre G1 v1 (#2785, CM02.02: eliminar)

## Alcance

Cuarta entrega del
[contrato CM01-CM03](../../../plans/2026-T4/2026-11-10-2785-comunicados-mailing-m2.md):
la pantalla de confirmación `/comunicados/eliminar/<pk>/` (`comunicado_confirm_delete.html`)
y su baja. Crear y editar siguen en las pantallas nativas, igual que el mailing masivo
(el envío sigue en el worker nativo y no se envía correo). No cambia vistas, plantillas,
modelos ni la API PWA. La ruta nativa `GET|POST /comunicados/eliminar/<pk>/` sigue
respondiendo igual (POST: 302 a la gestión).

Archivos:

- `src/backends/comedores/comunicados/web_api_views.py`, `web_api_serializers.py` y
  `web_api_urls.py`: `GET` y `POST /api/web/comedores/comunicados/<pk>/eliminar/`.
  `src/backends/config/middlewares/admindocs.py` y `src/backends/config/url_registry.json`
  (regenerado) con la ruta nueva.
- `src/backends/comedores/comunicados/web_preview.py`: entrada de vista previa local de la
  pantalla (misma guarda nativa).
- `src/frontends/apps/sisoc/src/routes/comunicadosEliminar.tsx` y ruta en `comunicados.tsx`.
- Pruebas: `test_web_comunicados_eliminar_api.py`, `test_web_preview_comunicados.py`,
  `routes/comunicadosEliminar.test.tsx`.

## Comportamiento

Mismo orden de chequeos que `ComunicadoDeleteView.dispatch`, en GET y en POST: primero el
objeto (404) y después el permiso (403 «No tiene permisos para eliminar este
comunicado.»: solo administradores y solo borradores). El GET devuelve lo que imprime la
plantilla (título, «Creado el d/m/Y H:i por creador», cantidad de adjuntos); el POST llama
al `post()` de la vista nativa (baja física en cascada de los adjuntos, sin tocar archivos
en el almacenamiento), deja en cola «Comunicado eliminado correctamente.» y devuelve
`{"ok": true, "redirect": "/comunicados/gestion/"}`; el siguiente GET de gestión muestra el
mensaje. Acceso: G1 primero (401 sin sesión) y CSRF obligatorio.

En React se conservan los textos («Confirmar Eliminación», «¿Estás seguro de que deseas
eliminar el siguiente comunicado?», «Este comunicado tiene N archivo(s) adjunto(s) que
también serán eliminados.», «Esta acción no se puede deshacer.», «Cancelar», «Sí,
Eliminar»). El botón se deshabilita mientras espera, no se reenvía y, si no se puede
confirmar el resultado, se muestra «No se pudo confirmar el resultado. Revise la gestión de
comunicados antes de volver a intentar.».

## Verificación

Entorno sintético, sin red, imagen fijada: pruebas de backend por interfaz pública
(estado, JSON, permisos, efectos persistidos, mensaje, CSRF) y suite existente de
comunicados sin cambios; Vitest del proyecto, `tsc`, ESLint y build de Vite; `black` y
`pylint`; e2e G1 y comparación visual nativo/React de la confirmación (con y sin adjuntos)
en escritorio y móvil.

## Limitaciones

- No se borran los archivos del almacenamiento (igual que el nativo).
- Diferencia del marco compartido (`SisocShell`): el logo tiene nombre accesible en React y
  cambia el primer elemento del orden de Tab.
