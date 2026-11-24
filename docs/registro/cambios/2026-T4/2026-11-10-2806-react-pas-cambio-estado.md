# Cambio: cambio de estado de titulares PAS en React sobre G1 v1 (#2785, PAS06.03)

## Alcance

Modal «Cambiar estado PAS» del panel de control, del
[contrato PAS05-PAS06](../../../plans/2026-T4/2026-11-10-2785-pas05-pas06-contratos.md).
Se apoya en el panel React de
[buscador, panel y áreas](2026-11-10-2806-react-pas-backoffice.md).

No cambia la vista, el formulario (`PasCambioEstadoForm`), el servicio
(`cambiar_estado`), la plantilla ni `pas.js`. La ruta nativa
`/pas/<pk>/cambiar-estado` responde igual. No activa React en producción.

Archivos:

- `src/backends/pas/pas/web_api_views.py` (`PasCambioEstadoWebView` y las
  opciones del modal en la respuesta del panel) y
  `src/backends/pas/pas/web_api_urls.py`.
- `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/`: `pasCambioEstado.tsx` (modal y
  recarga del panel) y `pasSelect2.tsx` (Select2 simple y múltiple del modal).
- Pruebas: `src/backends/pas/pas/tests/test_web_pas_cambio_estado.py` y
  `src/frontends/apps/sisoc/src/routes/pasCambioEstado.test.tsx`.

## Comportamiento

`POST /api/web/pas/personas/<pk>/cambiar-estado/` con `estado` y `avisos`:

- Válido: en una transacción cambia el estado y `fecha_actualizacion`,
  reemplaza los avisos y crea el historial con estado y avisos anteriores y
  nuevos y el usuario. No toca invitaciones ni DDJJ. Responde 200
  `{"message": "Estado PAS actualizado correctamente.", "persona": {...}}`. Se
  acepta el mismo estado actual, como hoy.
- Inválido: 400 con los errores del formulario y `messages`, la lista que la
  vista nativa pasa a `messages.error`, en el mismo orden y con los textos de
  Django. Sin efectos.
- Titular inexistente, 404; solo POST (otros métodos, 405); CSRF obligatorio.

Acceso: G1 y después la regla nativa `permissions_any_required(["pas.change_paspersona"])`.
La API no deja mensajes en la sesión.

Pantalla: el botón «Cambiar estado» (con `change_paspersona`) abre el modal de
Bootstrap 5.3 (fondo, `modal-open`, foco en el diálogo, foco atrapado, Esc,
«Cancelar» y la cruz; al cerrar el foco vuelve al botón). «Nuevo estado» y
«Nuevos avisos» reproducen los Select2 de `pas.js`: placeholders «Seleccione
una opcion» y «Seleccione avisos», `allowClear` y avisos filtrados por estado
(se conservan los que el nuevo estado también ofrece). Como la vista nativa,
el éxito y cada error terminan en `pas/panel-control/<pk>` (sin los filtros de
la lista) con el mensaje como toast. Un resultado que no se puede confirmar
no se reintenta: recarga el panel y muestra «No se pudo confirmar el
resultado. Verificá el estado antes de reintentar.».

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: pruebas nuevas en rojo sobre el árbol anterior (13 de 15) y luego en
  verde. Suite de PAS, `test_web_gate`, `test_backend_proxy` y
  `test_servicios_backends` (284 pasan, 1 omitida), registro de URLs al día,
  recolección completa sin errores, `black`, `pylint` 10/10 y
  `makemigrations --check` sin cambios.
- Frontend: prueba nueva en rojo (7 de 7) y luego en verde; Vitest de `sisoc`
  (380) y `pas`, `tsc`, ESLint y build de Vite.
- Visual (regla S13), nativo contra React en 1440x900 y 390x844: panel, modal
  abierto, modal con estado elegido, lector sin botón y pestaña DDJJ, 10 de 10
  pasan, desvío máximo de 0,23 px y 0,000 % de píxeles distintos.
- G1 de punta a punta: core y runtime de PAS en dos contenedores gunicorn. En
  el navegador, el cambio de estado por core → compuerta → runtime muestra el
  toast, vuelve a `/pas/panel-control/<pk>` y el historial nuevo. Un POST sin
  CSRF responde 403. Contra el runtime directo, un POST firmado para GET
  responde 403 sin escribir.

## Limitaciones

- La lista abierta de los Select2 se probó por recorrido (pruebas y G1), no con
  la comparación visual completa.
- Los errores «Seleccione al menos un aviso.» y «Hay avisos que no corresponden
  al estado seleccionado.» del formulario no se alcanzan hoy: antes responden
  el obligatorio o la opción inválida de Django. Se conserva.
