# Cambio: formularios de la rendición mensual en React sobre G1 v1 (#2785, RM01.02)

## Alcance

Tercera entrega de RM01 del
[contrato RM01](../../../plans/2026-T4/2026-11-10-2785-rendicion-cuentas-mensual-m2.md),
sobre el [protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md):
las tres pantallas de escritura de la rendición, con el prefijo duplicado de la
app (`/rendicioncuentasmensual/rendicioncuentasmensual/`):

- `nuevo/<comedor_id>/` (`rendicioncuentasmensual_create`, plantilla
  `rendicioncuentasmensual_form.html`),
- `editar/<pk>/` (`rendicioncuentasmensual_update`, plantilla
  `rendicioncuentasmensual_datos_form.html`; es el destino de «Editar Datos de
  Rendición» del detalle),
- `eliminar/<pk>/` (`rendicioncuentasmensual_delete`, confirmación con el
  componente compartido `delete_confirm.html`).

Verificación de rutas (paso previo) en la base `adfc34e75` más el detalle
entregado: ninguna de las tres tenía ruta React. Quedan fuera
`eliminar-archivo/<id>/` (solo lo usa el bloque de documentos existentes de la
plantilla de alta, que nunca se dibuja porque la vista no manda
`archivos_adjuntos`) y la auditoría, que va en la entrega siguiente.

No cambia vistas, formularios, servicios, modelos, plantillas, JavaScript ni URLs
nativas. No activa React en producción.

Archivos:

- `src/backends/comedores/rendicioncuentasmensual/web_api_rendicion_form.py`,
  incluido desde `src/backends/comedores/rendicioncuentasmensual/web_api_urls.py`;
  `src/backends/config/middlewares/admindocs.py` suma las rutas nuevas al atajo;
  `src/backends/config/url_registry.json` se regenera con `generar_registro_urls`.
- `src/backends/comedores/rendicioncuentasmensual/web_preview.py`: las entradas
  `NuevaEntry`, `EditarEntry` y `BajaEntry` se suman a `rendicion_preview_patterns`
  (sin montar).
- `src/frontends/apps/sisoc/src/routes/rendicionMensualForm.tsx`, registrado en
  `routes/index.ts`.
- Pruebas:
  `src/backends/comedores/rendicioncuentasmensual/test_web_rendicion_form_api.py`,
  `src/backends/comedores/rendicioncuentasmensual/test_web_preview_rendicion_form.py`
  y `src/frontends/apps/sisoc/src/routes/rendicionMensualForm.test.tsx`.

## Comportamiento

Las rutas `/api/web/comedores/rendicioncuentasmensual/{nuevo,editar,eliminar}/<id>/`
ejecutan `RendicionCuentaMensualCreateView`, `RendicionCuentaMensualUpdateView` y
`RendicionCuentaMensualDeleteView` con `dispatch`, así que el formulario, su
validación, la numeración, la baja lógica en cascada y los mensajes siguen siendo
los nativos. Una redirección nativa vuelve como `{"ok": true, "redirect": ...}`
(React navega de página completa, como el 302) y un formulario rechazado como 400
con los datos de la página.

Acceso (sin cambios, ver
[brechas de acceso conservadas](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md)):
G1 primero (401 sin sesión, 403 con `state` si hay un requisito pendiente, 403
sin CSRF); después, superusuario o `rendicioncuentasmensual.view_rendicioncuentamensual`
(el código de cada URL). La edición suma, como hoy, `edit_rendicion_data`
(403 sin él). Un POST con otro tipo de contenido que `multipart/form-data` o
`application/x-www-form-urlencoded` es 415.

Alta: la tarjeta «Datos asociados» (Mes, Año, Observaciones) y la de
«Documentación Adjunta» con las filas de archivo. «Agregar Archivo» suma una fila
vacía; «Eliminar Archivo» quita la última o, si queda una, la vacía (igual que
`rendicioncuentasmensual_form.js`). Se envía multipart solo con lo que dibuja la
plantilla.

Edición: convenio, número, período y nombre precargados (la fecha en ISO); un
campo vacío conserva su valor y el nombre se puede limpiar. Los errores de campo y
los generales salen del formulario nativo.

Baja: la confirmación con el desglose en cascada; confirmar da de baja la
rendición y vuelve al listado del comedor con el mensaje nativo.

## Limitaciones

- Conservado de la nativa: la página de alta **nunca guarda**. El formulario exige
  `linea_programatica` y `estado`, que la plantilla no dibuja, así que todo POST
  hecho desde la página se rechaza y la vista responde con un formulario nuevo,
  en blanco y sin errores (reemplaza el formulario enlazado de su contexto). React
  lo reproduce. Además, ningún enlace de la aplicación apunta a esa pantalla ni a
  la baja. Requiere decisión humana: corregirlo en la vista nativa (dibujar los
  dos campos) o retirar la ruta; este cambio no lo toca.
- Conservado: el nombre escrito en cada fila de documento se ignora (la vista
  nombra el documento con el nombre del archivo).
- Conservado: la plantilla de baja deja el segundo elemento del migas de pan sin
  texto (usa un atributo inexistente) y su primer enlace apunta a la propia
  página.
- Un `comedor_id` inexistente muestra el formulario de alta, como la nativa; solo
  un POST válido contra un comedor inexistente era un 500 nativo y aquí es 404.
- Diferencia del marco compartido (`SisocShell`): el logo tiene nombre accesible
  («Inicio de SISOC») en React y no en la nativa.
