# Cambio: bloque RENAPER compartido y «Generar usuario» CDI en React sobre G1 v1 (#2785, CDI01.01)

## Alcance

Primera y segunda entrega del carril C7 del backend CDI sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md):

- el bloque de validación RENAPER por persona (`partials/renaper_bloque.html` y
  `static/custom/js/cdiRenaperBloques.js`), que comparten el centro, el
  destinatario y «Generar usuario»;
- «Generar usuario referente» (`/centrodeinfancia/<centro>/generar-usuario/`) y su
  pantalla de resultado, parte de CDI01.01 del contrato
  `2026-10-28-2785-cdi-usuarios-reportes-documentacion.md`, con la regla de
  credenciales CDI-CR1 de `2026-10-28-2785-cdi-centros-y-credenciales.md`.

Los formularios de destinatario y de centro, que consumen el mismo bloque, quedan
nativos en esta entrega (ver Limitaciones). No activa React en producción y no
cambia el comportamiento nativo. Ninguna prueba consulta RENAPER real: la consulta
va siempre simulada.

Archivos:

- `src/backends/cdi/centrodeinfancia/web_api_formularios.py`: transporte común
  (G1, permiso de la URL nativa, despacho nativo), proyección de un campo de
  formulario y consulta RENAPER por bloque.
- `src/backends/cdi/centrodeinfancia/web_api_usuario_generar.py` y
  `web_api_urls_formularios.py`; el `include` va en `cdi_runtime/web_api_urls.py`.
- `src/backends/cdi/centrodeinfancia/web_preview_formularios.py`: entrada de vista previa.
- `src/backends/config/middlewares/admindocs.py` y `url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/cdiRenaperBloque.tsx` (bloque y hook),
  `cdiRenaperBloqueCampos.tsx` (campo crispy) y `cdiUsuariosGenerar.tsx`; registro
  en `routes/index.ts`.
- Pruebas: `tests/test_web_usuario_generar_c7.py`,
  `tests/test_web_preview_formularios_c7.py` y `routes/cdiUsuariosGenerar.test.tsx`.

## Comportamiento

**Consulta RENAPER.** `GET /api/web/cdi/renaper/<bloque>/?dni=` ejecuta la función
nativa `consultar_renaper_bloque` detrás de G1 y de los mismos cuatro permisos de la
URL nativa: bloque inexistente 404, veto de auditoría 403, límite por usuario 429,
fallo o ausencia 400, éxito con `valores` y el token firmado (usuario, bloque y
valores, una hora). El servidor sigue tomando la identidad del token y no del POST.

**Generar usuario.** `GET` y `POST /api/web/cdi/centros/<pk>/usuarios/generar/`
heredan `GenerarUsuarioCDIView`: formulario, precarga del referente de la ficha,
identidad verificada bloqueada, cupo, regla del responsable, usuario por DNI si el
email está en uso y `generar_usuario_delegado` son los nativos. El acceso es, en
orden, G1, `centrodeinfancia.view_centrodeinfancia` y el despacho nativo (404 centro
inexistente, 403 sin cupo o sin permiso de gestión). Un formulario inválido responde
400 con sus errores y sin efectos.

**Credenciales (CDI-CR1).** La contraseña temporal sale solo en la respuesta del POST
que crea el usuario, que es `private, no-store`, con lo mismo que muestra la página
nativa: usuario, email, estado del correo y contraseña. Nunca en un GET, en un
rechazo, en el registro ni con datos del usuario (sin hash, perfil ni ids). En el
navegador vive únicamente en el estado del componente: sin almacenamiento, sin URL y
sin entrada de historial. Como en la página nativa, recargar la pantalla de resultado
no la recupera.

**Pantalla.** El bloque reproduce los cuatro estados del script nativo (agregar,
DNI, verificado, manual): columnas que se ocultan según el estado, tarjeta de datos
verificados con CUIL con guiones y fechas locales, «Cambiar persona» y «Cancelar», Enter
en el DNI que valida en lugar de enviar, mensaje al fallar la consulta con el botón
«Cargar manualmente» (que no se ofrece si la ficha ya tiene a la persona verificada) y
el aviso cuando un campo obligatorio oculto bloquea el envío. El formulario envía solo
los campos que el HTML dibuja y no tiene deshabilitados, más el token. Tras un rechazo
vuelve arriba y vuelve a dibujar el estado que calcula el servidor.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 18 pruebas de la API en rojo (18 fallaban sin el `include`) y luego en
  verde, y 4 de la vista previa. Cubren forma del formulario, identidad verificada
  bloqueada, 404/403, alta con token (la identidad sale del token y no del POST),
  contraseña solo en esa respuesta (no en el registro ni en un GET posterior),
  rechazo sin efectos, token de otro usuario, responsable del propio centro, centro
  sin cupo, 401, CSRF, métodos y formato, y la consulta (éxito, fallo, 429, veto,
  permiso, solo GET).
- Frontend: 14 pruebas de ruta (efectos con `waitFor`).
- Visual (regla S13), escritorio y móvil, formulario vacío, formulario verificado
  y rechazo del servidor: mismas etiquetas, controles, orden y Tab, diferencia
  geométrica máxima de 0,02 px y diferencia de píxeles de 0,000 %, y mismos 403 y 404
  de guardas. La pantalla de resultado no se compara píxel a píxel porque la
  contraseña es aleatoria en cada alta; su texto y controles están cubiertos por
  la prueba de ruta.

## Limitaciones

- Destinatario y centro (U3 y U4 de este carril) siguen nativos; el bloque ya está
  listo para ellos (`useRenaperBloque` admite varios bloques, bloque opcional y
  campo de tipo de documento).
- Un POST con resultado incierto (red) no se reintenta: la pantalla avisa que se
  recargue y verifique antes de reintentar, porque el usuario pudo crearse.
