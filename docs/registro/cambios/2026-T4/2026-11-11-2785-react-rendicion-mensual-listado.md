# Cambio: listado global de rendiciones mensuales en React sobre G1 v1 (#2785, RM01.01)

## Alcance

Primera entrega de RM01.01 del
[contrato RM01](../../../plans/2026-T4/2026-11-10-2785-rendicion-cuentas-mensual-m2.md),
sobre el [protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md):
el listado global `/rendicioncuentasmensual/rendicioncuentasmensual/listado/`
con sus filtros, columnas, paginación y el enlace al CSV nativo. La lista por
comedor, el detalle, las acciones del circuito (RM01.02) y los documentos
(RM01.03) quedan para entregas siguientes. El contrato se refrescó contra
82cfd28a1 en el mismo cambio (descarga asincrónica del PDF de #2845, textos de
auditoría y líneas de fuente).

No cambia vistas, formularios, servicios, modelos, plantillas, JavaScript ni
URLs nativas. Las URL conservan el prefijo duplicado
`/rendicioncuentasmensual/rendicioncuentasmensual/`. No activa React en
producción.

Archivos:

- `src/backends/comedores/rendicioncuentasmensual/web_api.py` y
  `src/backends/comedores/rendicioncuentasmensual/web_api_urls.py`, incluidos
  desde `src/backends/comedores/comedores_runtime/web_api_urls.py`;
  `src/backends/config/url_registry.json` regenerado con `generar_registro_urls`.
- `src/backends/config/middlewares/admindocs.py`: la ruta nueva queda fuera del
  atajo HEAD de admindocs.
- `src/backends/comedores/rendicioncuentasmensual/web_preview.py`: entrada
  React sin montar (`rendicion_preview_patterns`), assets en
  `/rendicioncuentasmensual/react/assets/`.
- `src/frontends/apps/sisoc/src/routes/rendicionMensual.tsx`, registrado en
  `routes/index.ts`.
- Pruebas:
  `src/backends/comedores/rendicioncuentasmensual/test_web_rendicion_listado_api.py`,
  `src/backends/comedores/rendicioncuentasmensual/test_web_preview_rendicion_listado.py`
  y `src/frontends/apps/sisoc/src/routes/rendicionMensual.test.tsx`.

## Comportamiento

`GET /api/web/comedores/rendicioncuentasmensual/listado/` ejecuta
`RendicionCuentaMensualGlobalListView`: mismo queryset (activas, orden
`-ultima_modificacion, -id`), filtros avanzados por tipo, filtros propios de
territorial asignado y estado, JSON roto ignorado, preferencias de columnas
`rendiciones_global_list`, 25 por página y 404 con página inválida. Cada celda se
arma con el include nativo `components/rendicion_global_list_cell.html`: el
texto visible y la clase del badge de Etapa y Estado. React no formatea fechas,
períodos ni estados.

Acceso (sin cambios, ver
[brechas de acceso conservadas](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md)):
G1 primero (401 sin sesión, 403 con `state` si hay un requisito pendiente);
después, superusuario o uno de los cinco permisos de `urls.py`
(`view_rendicioncuentamensual` y los cuatro de etapa), sin alcance por objeto.
«Nueva Auditoría» aparece con `perms.rendicioncuentasmensual.manage_auditoria_stage`
y «Exportar búsqueda» con superusuario o `auth.role_exportar_a_csv`, como en la
página. Solo GET y HEAD; la lectura no escribe en la base.

La pantalla reproduce `rendicioncuentasmensual_global_list.html`:
`search_bar.html` en modo filtros (`advanced_filters.js`: el operador sale del
tipo; número con `step`, `min` y `max`, fecha, choice y booleano con select;
valor desconocido agregado como opción), «Resetear», el modal de columnas
(`column_config.js`, POST a `/ajax/columnas-preferencias/` y recarga), la tabla,
«Ver», el vacío «No hay rendiciones registradas.», la paginación «Volver» /
«Continuar» con «Se encontraron N resultados» y el CSV
(`export_helper.js`: navega a `listado/?export=csv` con la query vigente; la
descarga sigue en la vista nativa).

Hallazgo fijado por pruebas (no corregido): la resolución de columnas obliga
«Proyecto», pero el modal nativo no lo marca como obligatorio
(`build_columns_context_from_fields` deja `required: false` en todas las
columnas); React reproduce lo mismo.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: pruebas nuevas en rojo sobre la base (25 de 25 sin ruta; la de vista
  previa sin módulo) y en verde (29). App, `test_web_gate`,
  `test_backend_proxy`, `test_servicios_backends`, registro de URLs y
  recolección completa sin errores. `comedores/tests`: solo las 9 fallas ya
  conocidas de la base. `black`, `pylint` 10/10 y `makemigrations --check` sin
  cambios.
- Frontend: prueba de ruta en rojo (módulo inexistente) y en verde (7); Vitest
  del proyecto tres veces seguidas, `tsc`, ESLint y build de Vite.
- Visual (S13), 7 estados (superusuario, lector, auditor en página 2, columnas
  guardadas con CSV, filtro por estado, filtros tipados, sin resultados) en
  1440x900 y 390x844: estructura y estilos iguales, desvío máximo 0,02 px y
  0,000 % de píxeles distintos. Anónimo, sin permisos y página inválida (9 y
  `x`) responden igual. Recorrido igual en las dos páginas: filtros tipados,
  agregar y quitar fila, envío, CSV con la misma query, paginación, «Resetear» y
  guardado de columnas.
- G1 de punta a punta (core y runtime de Comedores con gunicorn): listado y
  filtro desde el navegador, CSV descargado con el mismo nombre y encabezado;
  anónimo 401, sin permisos 403, requisito pendiente 403 con `state`, POST 403,
  página inválida 404, el header del cliente se descarta y el runtime rechaza
  firmas ausentes, alteradas, de otro usuario, destino o audiencia y vencidas.

## Limitaciones

- Diferencia del marco compartido (`SisocShell`): el logo tiene nombre accesible
  («Inicio de SISOC») en React y no en la página nativa; es el único cambio en el
  orden de Tab. El menú móvil abierto queda fuera de la comparación.
- El buscador y el modal de columnas repiten el código de
  `routes/duplasList.tsx` y `routes/cdfFilters.tsx`, que no cubren los cuatro
  tipos de campo o no exportan el modal; conviene unificarlos en un módulo
  compartido.
- La comparación usó la fuente de reemplazo (Google Fonts bloqueado sin red).
