# Cambio: intervenciones de comedor en React, listado, ficha y baja de archivo (#2785, CO02)

## Alcance

Primera entrega de la lane K4 del contrato
[`2026-10-28-2785-comedores-intervenciones-observaciones-m2.md`](../../../plans/2026-T4/2026-10-28-2785-comedores-intervenciones-observaciones-m2.md):
el historial de intervenciones de un comedor, la ficha de una intervención y la
baja de su archivo adjunto. El formulario, la baja de la intervención y las
observaciones (CO06) quedan para entregas siguientes. No activa React en
producción y no cambia ninguna vista, ruta ni permiso nativo.

Archivos:

- `src/backends/comedores/intervenciones/web_api.py` y `web_api_urls.py`: API web.
- `src/backends/comedores/intervenciones/web_preview.py`: dos entradas de la
  vista previa local.
- `src/backends/comedores/comedores_runtime/web_api_urls.py`,
  `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado): alta del `include`.
- `src/frontends/apps/sisoc/src/routes/comedorIntervenciones.tsx` y su prueba.
- Prueba de backend:
  `src/backends/comedores/intervenciones/tests/test_web_intervenciones_lectura_k4.py`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/comedores/intervenciones/comedor/<pk>/` | Ejecuta `IntervencionDetailView` (filtros `fecha` por día local, `tipo_intervencion`, `destinatario` y `admision_id`) y devuelve filas, catálogos, convenios y mensajes pendientes |
| `GET /api/web/comedores/intervenciones/<pk>/` | Ejecuta `IntervencionDetailIndividualView` y devuelve la ficha |
| `POST /api/web/comedores/intervenciones/<pk>/documentacion/eliminar/` | Ejecuta `eliminar_archivo_intervencion`: borra el archivo, apaga `tiene_documentacion`, deja el mensaje nativo y devuelve `{"ok": true, "redirect": <ficha>}` |

Acceso, en este orden: G1 (sesión y requisitos web, o la constancia firmada
del runtime) y los mismos códigos de permiso que la URL nativa (listado y
ficha: `intervenciones.view_intervencion`; baja de archivo: cualquiera de
`comedores.view_comedor`, `admisiones.view_admision` o
`acompanamientos.view_informacionrelevante`; el superusuario pasa siempre). No
se agrega alcance por comedor: como en las rutas nativas, estas pantallas no
limitan por comedores del usuario. El botón Eliminar de la ficha y del listado
sigue siendo solo para superusuarios, aunque el endpoint de baja de archivo
acepta a quien tenga uno de los permisos (diferencia conservada).

Rarezas nativas conservadas: un subtipo, destinatario o descripción faltante
se muestra como el texto «None»; el filtro de fecha inválida se ignora; la
admisión solo cuenta si es del comedor y fue enviada a acompañamiento; la fila
del listado deja una celda vacía antes de las acciones (el `td` anidado de la
plantilla). Un comedor o una intervención inexistente responde 404 (en la
vista nativa es un error 500 y el 404 del framework).

Pantallas React: marco oscuro de `routes/MainFrame.tsx`. El filtro es un
formulario GET real (recarga la página como el nativo) y «Limpiar» vuelve a la
ruta conservando `admision_id`. La baja del archivo usa la modal de
`nativeParity` en su lugar, un solo envío y, si no se confirma, un aviso sin
reintento.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 9 pruebas nuevas en rojo (sin el `include`) y luego en verde;
  comprueban estado, JSON, permisos, mensajes y que un rechazo (sin permiso, sin
  CSRF) no borra el archivo ni cambia la fila.
- Frontend: 9 pruebas nuevas; `tsc`, `eslint` y la compilación sin errores.
- Visual (regla S13) con la harness compartida: listado (superusuario, lector,
  filtrado, vacío), ficha y modal de baja de archivo, en escritorio y móvil, sin
  diferencias salvo las exenciones conocidas.
- G1 de punta a punta: 401 anónimo, 403 sin permiso y con requisito pendiente,
  cabecera falsa ignorada, 403 sin CSRF, lectura y baja de archivo.

## Limitaciones

- La subida de archivo (`subir_archivo_intervencion`) no tiene pantalla en
  Comedores y no se migra; conserva su contrato actual.
- No se endurece ningún acceso ni alcance: las diferencias entre botón y
  endpoint y la falta de alcance por comedor siguen como hallazgos residuales
  del contrato.
