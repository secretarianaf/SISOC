# Cambio: detalle de la rendición mensual en React sobre G1 v1 (#2785, RM01.01)

## Alcance

Segunda entrega de RM01.01 del
[contrato RM01](../../../plans/2026-T4/2026-11-10-2785-rendicion-cuentas-mensual-m2.md),
sobre el [protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md):
la pantalla `/rendicioncuentasmensual/rendicioncuentasmensual/detalle/<pk>/`
(`rendicioncuentasmensual_detail`) con la cabecera, los datos, las acciones del
proceso, la tarjeta de Auditoría y la tabla de documentación asociada.

Verificación de rutas (paso previo): el `urls.py` de la app se monta bajo
`rendicioncuentasmensual/` y cada patrón vuelve a empezar con
`rendicioncuentasmensual/`, por eso las URL nativas llevan el prefijo duplicado.
Estado en la base `adfc34e75`: el listado global ya tenía ruta React
(`routes/rendicionMensual.tsx`, `web_preview.py`) y no se toca; el detalle no la
tenía y es lo que entrega este cambio. La lista por comedor, el formulario
nuevo y de edición, la baja, la auditoría y su detalle quedan para las entregas
siguientes.

No cambia vistas, formularios, servicios, modelos, plantillas, JavaScript ni URLs
nativas. No activa React en producción.

Archivos:

- `src/backends/comedores/rendicioncuentasmensual/web_api_rendicion_detalle.py`,
  incluido desde `src/backends/comedores/rendicioncuentasmensual/web_api_urls.py`
  (`<pk>/`); `src/backends/config/middlewares/admindocs.py` suma la ruta nueva al
  atajo; `src/backends/config/url_registry.json` se regenera con
  `generar_registro_urls`.
- `src/backends/comedores/rendicioncuentasmensual/web_preview.py`: la entrada
  `DetalleEntry` se suma a `rendicion_preview_patterns` (sin montar).
- `src/frontends/apps/sisoc/src/routes/rendicionMensualDetalle.tsx`, registrado en
  `routes/index.ts`.
- Pruebas:
  `src/backends/comedores/rendicioncuentasmensual/test_web_rendicion_detalle_api.py`,
  `src/backends/comedores/rendicioncuentasmensual/test_web_preview_rendicion_detalle.py`
  y `src/frontends/apps/sisoc/src/routes/rendicionMensualDetalle.test.tsx`.

## Comportamiento

`GET /api/web/comedores/rendicioncuentasmensual/<pk>/` ejecuta
`RendicionCuentaMensualDetailView` (`get_object` con su 404, documentación por
categoría con borradores de revisión, alcance de proyecto y las once
capacidades). Las fechas, los números y los textos salen formateados del servidor
con los mismos filtros de la plantilla; React no formatea nada.

Acceso (sin cambios, ver
[brechas de acceso conservadas](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md)):
G1 primero (401 sin sesión, 403 con `state` si hay un requisito pendiente);
después, superusuario o uno de los cinco permisos de `urls.py`, sin alcance por
objeto. Solo GET y HEAD.

Las escrituras no se reimplementan: la página envía exactamente lo que enviaba la
nativa a la URL del detalle. Los botones de etapa («Iniciar revisión
territorial», «Finalizar revisión para Carga», «Iniciar regularización»,
«Finalizar regularización» con el archivo del acta complementaria) son
formularios `POST` con redirección; la revisión por documento y la «Solicitud de
documento faltante» son AJAX con `X-Requested-With`, con el mismo comportamiento
de `rendicioncuentasmensual_detail.js` (los controles se muestran u ocultan según
la selección, el guardado recarga la página y los errores del servidor van en
`#revision-feedback`). «Generar descarga» repite
`rendicioncuentasmensual_pdf_descarga.js` (solicitud, consulta de estado cada
3 segundos y descarga nativa al estar listo). «Ver» y los enlaces de acta siguen
siendo navegación nativa y, al volver del visor, la página se recarga salvo que
haya una revisión sin guardar. Los mensajes de Django pendientes se muestran como
en la página nativa.

## Limitaciones

- Diferencia del marco compartido (`SisocShell`): el logo tiene nombre accesible
  («Inicio de SISOC») en React y no en la nativa.
- Conservado de la nativa: la plantilla compara `categoria.codigo` con
  `'comprobantes'`, un código que no existe (la constante vale
  `comprobantes_alimentario`), así que solo «Documentación Adicional» usa el estilo
  plano del historial de subsanaciones; React lo reproduce.
- «Editar Datos de Rendición» y «Gestionar Auditoría» enlazan a pantallas todavía
  nativas.
