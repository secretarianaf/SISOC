# Cambio: consulta y acciones de la rendición de cuentas final en React sobre G1 v1 (#2785, RF01.01 a RF01.03)

## Alcance

Primera entrega de RF01 (consulta RF01.01, acciones RF01.02 y documentos RF01.03) del
[contrato RF01](../../../plans/2026-T4/2026-11-10-2785-rendicion-cuentas-final-m2.md),
sobre el [protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md):
el detalle `/comedores/<pk>/rendicion_cuentas_final/` y el listado
`/rendicion_cuentas_final/listar/` con su búsqueda AJAX, más las seis acciones
nativas: validar, subsanar, alternar «Revisión físicamente presentada»,
adjuntar, crear documento personalizado y eliminar. Los archivos se suben y se
sirven por el almacenamiento y las rutas nativas (`/media/rendicion_cuentas_final/`).
No cambia vistas, servicios, modelos, plantillas, JavaScript ni URLs nativas, ni
la entrega pública de `/media/rendicion_cuentas_final/`. No activa React en producción.

Archivos:

- `src/backends/comedores/rendicioncuentasfinal/web_api.py` y `web_api_urls.py`,
  incluidos desde `src/backends/comedores/comedores_runtime/web_api_urls.py`;
  `src/backends/config/url_registry.json` regenerado y
  `src/backends/config/middlewares/admindocs.py` (rutas nuevas fuera del atajo HEAD).
- `src/backends/comedores/rendicioncuentasfinal/web_preview.py`: entradas React sin
  montar, assets en `/rendicion_cuentas_final/react/assets/`.
- `src/frontends/apps/sisoc/src/routes/rendicionFinal.tsx`, registrado en `routes/index.ts`.
- Pruebas: `test_web_rendicion_final_api.py`, `test_web_preview_rendicion_final.py` y
  `rendicionFinal.test.tsx`.

## Comportamiento

- `GET /api/web/comedores/rendicion_cuentas_final/comedor/<pk>/` ejecuta la vista de
  detalle nativa: 404 si el comedor no existe; si no hay rendición la crea con sus
  documentos base (efecto del GET que se conserva). Devuelve documentos
  (`editable`, `validable`, `eliminable` de las propiedades del modelo), historial y
  fechas `d/m/Y H:i` en hora local.
- `GET /api/web/comedores/rendicion_cuentas_final/documentos/` usa el queryset nativo
  con alcance por área. Sin `busqueda` ni `page`: todas las filas y `page_size: null`;
  con cualquiera de los dos, paginador de 25 como el AJAX (página inválida no falla).
- Acciones: `POST .../documentos/<id>/{validar,subsanar,eliminar}/`,
  `POST .../documentos/adjuntar/`, `POST .../<rendicion_id>/{crear,fisicamente_presentada}/`
  repiten los efectos de las vistas nativas (estado, fecha, historial con el
  usuario de la sesión, archivo en el almacenamiento nativo) y sus mensajes:
  «Documento validado correctamente.», «Documento enviado a subsanar correctamente.»,
  «Documento eliminado correctamente.», «Archivo adjuntado correctamente.»,
  «Estado de revisión actualizado.»; adjuntar sin archivo responde 400 con
  «No se seleccionó ningún archivo.». Igual que hoy no hay guarda de estado, la
  observación vacía se acepta y repetir el POST repite el efecto. Exigen
  `view_rendicioncuentasfinal` (el nativo solo pide sesión; excepción de la
  decisión de brechas), CSRF y G1; 404 por id inexistente y 405 en GET.
  El cliente pide la confirmación nativa (`window.confirm`) en validar, eliminar,
  adjuntar y crear, envía una sola vez, y ante un 504 muestra «No se pudo confirmar
  el resultado.» y recarga con GET sin reenviar.
- Acceso: G1 primero (401/403 con `state`); después `view_rendicioncuentasfinal`
  (superusuario pasa), como la guarda de las URL nativas. Solo GET y HEAD. Ver
  [brechas de acceso conservadas](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md).
- La asimetría del alcance (usuario sin permisos de área y no coordinador ve todos los
  validadores) se conserva y está fijada por pruebas.
- Hallazgos conservados: el enlace del breadcrumb al comedor sale con texto vacío; el
  botón «Ocultar analizados» del script nativo es código muerto y React no lo muestra.

## Verificación

Entorno sintético, sin red, imagen fijada.

- Backend: lectura, 21 de 24 pruebas en rojo sin las rutas y 24 en verde; acciones,
  14 pruebas en verde (38 en total con la vista previa); `test_web_gate`,
  `test_backend_proxy` y `test_servicios_backends` en verde; `black`, `pylint` 10/10
  y `makemigrations --check` sin cambios.
- Frontend: lectura, ruta en rojo sin registrar (10 de 11) y en verde; con las
  acciones 20 pruebas de la ruta y 566 del proyecto; `tsc`, ESLint (0 errores) y build.
- G1 de punta a punta (core y runtime de Comedores con gunicorn, navegador): listado,
  validar con confirmación y mensaje, fila en «Validado», detalle y switch; anónimo 401,
  sin permiso 403, requisito pendiente 403 con `state`, POST sin CSRF 403, header
  del cliente descartado.
- Visual (S13), listado, búsqueda, error de búsqueda, modal de subsanar, detalle, modal
  de adjuntar y modal de observaciones, en 1440x900 y 390x844 con datos sintéticos:
  0,000 % de píxeles distintos y desvío de 0 px en escritorio (un caso móvil 0,017 %).

## Limitaciones

- Diferencias del marco compartido (`SisocShell`), fuera de esta pantalla: el logo
  tiene nombre accesible en React y no en la página nativa (único cambio en el orden de
  Tab) y el menú lateral móvil se arma con otro orden de nodos (mismo contenido y
  mismos píxeles).
- El detalle y el listado conservan el riesgo de carrera del `get_or_create` y el orden
  sin desempate descritos en el contrato.
