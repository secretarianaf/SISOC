# Cambio: auditoría de la rendición mensual en React sobre G1 v1 (#2785, RM01.03)

## Alcance

Cuarta entrega de RM01 del
[contrato RM01](../../../plans/2026-T4/2026-11-10-2785-rendicion-cuentas-mensual-m2.md),
sobre el [protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md):
las dos pantallas de `RendicionAuditoriaView`, con el prefijo duplicado de la app
(`/rendicioncuentasmensual/rendicioncuentasmensual/`):

- `auditoria/` (`rendicioncuentasmensual_auditoria_nueva`): búsqueda de la rendición
  a auditar (filtro, texto, tabla de rendiciones disponibles y paginación de 20).
- `auditoria/<pk>/` (`rendicioncuentasmensual_auditoria`): información general,
  formulario de auditoría y documentación de las rendiciones seleccionadas. Es el
  destino de «Gestionar Auditoría» del detalle y de «Gestionar» de la búsqueda.

Verificación de rutas (paso previo) en la base `5e9821eb5`: ninguna de las dos tenía
ruta React. La redirección nativa `auditoria/?rendicion=<id>` sigue siendo nativa.

No cambia plantillas, formularios, servicios, modelos, JavaScript ni URLs nativas.
No activa React en producción.

**Edición en una vista compartida (`views.py`).** Para ejecutar la vista nativa y
reutilizar su contexto, `RendicionAuditoriaView` extrae sin cambiar su comportamiento
`_contexto_busqueda` (el cuerpo del `get` de la búsqueda) y `_contexto` (el contexto
que armaba `_render`); `get`, `post` y `_render` los llaman y devuelven lo mismo. Es
una refactorización pura: las pruebas nativas existentes y las nuevas comparan la
salida con la página nativa.

Archivos:

- `src/backends/comedores/rendicioncuentasmensual/web_api_rendicion_auditoria.py`,
  incluido desde `src/backends/comedores/rendicioncuentasmensual/web_api_urls.py`;
  `src/backends/config/middlewares/admindocs.py` suma la ruta al atajo;
  `src/backends/config/url_registry.json` se regenera con `generar_registro_urls`.
- `src/backends/comedores/rendicioncuentasmensual/web_preview.py`: `AuditoriaEntry`
  se suma a `rendicion_preview_patterns` (sin montar).
- `src/frontends/apps/sisoc/src/routes/rendicionMensualAuditoria.tsx`, registrado en
  `routes/index.ts`.
- Pruebas:
  `src/backends/comedores/rendicioncuentasmensual/test_web_rendicion_auditoria_api.py`,
  `src/backends/comedores/rendicioncuentasmensual/test_web_preview_rendicion_auditoria.py`
  y `src/frontends/apps/sisoc/src/routes/rendicionMensualAuditoria.test.tsx`.

## Comportamiento

`GET /api/web/comedores/rendicioncuentasmensual/auditoria/` y
`.../auditoria/<pk>/` ejecutan el `get` nativo; `POST .../auditoria/<pk>/` ejecuta el
`post` nativo (`AuditoriaForm`, `AuditoriaService.guardar` con sus bloqueos y el
mensaje de éxito). Una redirección nativa vuelve como `{"ok": true, "redirect": ...}`
(React navega de página completa) y un formulario rechazado como 400 con los datos de
la página, incluidos los valores escritos.

Acceso (sin cambios, ver
[brechas de acceso conservadas](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md)):
G1 primero (401 sin sesión, 403 con `state` si hay un requisito pendiente, 403 sin
CSRF); después, superusuario o `rendicioncuentasmensual.manage_auditoria_stage`, el
código de las URL nativas. Un POST con otro tipo de contenido que
`multipart/form-data` o `application/x-www-form-urlencoded` es 415. Una rendición ya
auditada, borrada o inexistente es 404, como en la nativa.

La búsqueda es el formulario GET nativo; el texto de ayuda y el marcador cambian con
el filtro como en `rendicioncuentasmensual_auditoria.js`. En el formulario, elegir
«Sí» en «¿Se genera acta de auditoría?» muestra las rendiciones incluidas, el acta y
el resultado; «Finalizada con Observaciones» muestra las observaciones y el acta
complementaria; los resúmenes de documentación se ven solo para la rendición actual y
las incluidas. Los campos ocultos van deshabilitados y no se envían. Se envía multipart
solo lo que dibuja la plantilla, a la URL con su `?origen=` para conservar el botón de
retorno.

## Limitaciones

- Diferencia del marco compartido (`SisocShell`): el logo tiene nombre accesible
  («Inicio de SISOC») en React y no en la nativa.
- Conservado: el formulario nativo valida con `AuditoriaForm`; React no repite reglas.
- Conservado: el atributo `aria-describedby="id_validada_error"` apunta a un elemento
  que la nativa no dibuja.
