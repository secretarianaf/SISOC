# Cambio: alta y edición de destinatarios CDI en React sobre G1 v1 (#2785, CDI nómina)

## Alcance

Carril C8 del backend CDI sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): la ficha de
destinatario (`/centrodeinfancia/<centro>/nomina/crear/` y
`/centrodeinfancia/<centro>/nomina/<ficha>/editar/`, template
`destinatario_form.html`), con la búsqueda por DNI, la precarga, los tres bloques
RENAPER y las diez secciones plegables, según el contrato
`2026-10-28-2785-cdi-nomina-asistencia-m2.md`. No activa React en producción y no
cambia el comportamiento nativo. Ninguna prueba consulta RENAPER real.

Archivos:

- `src/backends/cdi/centrodeinfancia/web_api_destinatario.py` y
  `web_api_urls_destinatario.py`; el `include` va en `cdi_runtime/web_api_urls.py`.
- `src/backends/cdi/centrodeinfancia/web_preview_destinatario.py`: entradas de vista previa.
- `src/backends/config/middlewares/admindocs.py` y `url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/cdiDestinatarioForm.tsx` (pantalla y ruta),
  `cdiDestinatarioCampos.tsx` (controles y validadores) y
  `cdiDestinatarioForm.behavior.ts` (progreso, edad y geografía); registro en
  `routes/index.ts`.
- Pruebas: `tests/test_web_destinatario_c8.py`, `tests/test_web_preview_destinatario_c8.py`
  y `routes/cdiDestinatarioForm.test.tsx`. Se actualizaron dos aserciones de
  `cdiNomina.test.tsx` y `cdiNominaLista.test.tsx`, que daban `crear/` y `editar/`
  como rutas sin dueño.

## Comportamiento

**API.** `GET` y `POST /api/web/cdi/centros/<pk>/nomina/crear/` y
`.../nomina/<id>/editar/` heredan `NominaCentroInfanciaCreateView` y
`NominaCentroInfanciaEditView`: alcance (404 fuera del alcance), búsqueda por DNI con
ciudadanos locales primero, consulta RENAPER y token de precarga de 15 minutos,
formulario, alta del ciudadano, bloqueo de la nómina, mensajes y veto de auditoría
SIMEPI son los nativos. El acceso es, en orden, G1, el permiso de la URL nativa
(`add_nominacentroinfancia` o `change_nominacentroinfancia`) y el despacho nativo. La
API envía los 102 campos que dibuja el template (etiqueta, widget, valor tal como lo
formatea el widget nativo, opciones y errores), los cuatro grupos de casillas y los
bloques RENAPER. Una redirección nativa es `{"ok": true, "redirect": ...}` y los
mensajes quedan para la página de destino; toda respuesta a un POST que vuelve a
dibujar el formulario (inválido, rechazado) es 400 con el mismo contenido y sin
efectos.

**Pantalla.** Búsqueda por DNI, tarjeta de progreso (diez secciones, estado de cada
una), secciones plegables con Enter o espacio, el script de la ficha (edad calculada
desde la fecha de nacimiento, filas condicionales de pueblo originario, discapacidad y
CUD, listas de departamento, municipio y localidad con el decil IPI, y la casilla «No
posee CUIL») y los bloques RENAPER del niño/a (solo si está verificado o en edición) y
de los responsables 1 y 2 (este último opcional). Envía una sola vez solo los campos
que el template dibuja y no tiene deshabilitados, más los tokens; un resultado incierto
no se reintenta. Tras un rechazo vuelve arriba y dibuja los errores del servidor.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 17 pruebas de la API y 3 de la vista previa (formulario, búsqueda, precarga
  desde ciudadano y desde RENAPER simulado, alta, rechazo sin efectos, ficha ya en la
  nómina, edición, edición rechazada, otro centro 404, permiso por pantalla, veto de
  auditoría, 401, CSRF, métodos y formato).
- Frontend: 12 pruebas de ruta y de comportamiento (efectos con `waitFor`).
- G1 de extremo a extremo: 401 anónimo, 403 sin permiso y con requisito pendiente,
  cabecera falsificada ignorada, 403 sin CSRF, alta feliz y rechazo.
- Visual (regla S13), escritorio y móvil, búsqueda con formulario vacío, formulario
  precargado desde un ciudadano, edición y rechazo del servidor: mismas etiquetas,
  controles, orden y Tab, diferencia geométrica máxima de 0,03 px y diferencia de
  píxeles de 0,000 % (0,013 % y 0,032 % en el rechazo, de escritorio y móvil), y mismos
  401/403/404 de guardas. El rechazo mostró que el marcado nativo de un grupo de casillas
  con error marca cada casilla como inválida y pone el mensaje dentro de la última; la
  pantalla lo reproduce.

## Limitaciones

- La consulta RENAPER de cada bloque usa el endpoint del carril C7 y va siempre
  simulada en las pruebas.
- Un POST con resultado incierto (red) no se reintenta: la pantalla pide verificar el
  estado antes de reintentar.
- El progreso de secciones se deriva del estado del formulario; el script nativo solo
  lo recalcula con eventos de entrada, de modo que un valor cargado por RENAPER se
  refleja al instante en lugar de al siguiente cambio.
