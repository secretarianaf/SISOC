# Cambio: expedientes de pago de un comedor en React sobre G1 v1 (#2785, EX01)

## Alcance

Entregas EX01.01 (listado y ficha) y EX01.02 (alta, edición y baja lógica) del
[contrato EX01/EX02](../../../plans/2026-T4/2026-11-10-2785-expedientes-pagos-importacion-m2.md),
sobre el [protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md).
La importación de expedientes (EX02) queda fuera.

No cambia vistas, formularios, servicios, modelos, plantillas ni URLs nativas.
No activa React en producción.

Archivos:

- `src/backends/comedores/expedientespagos/web_api.py` y
  `src/backends/comedores/expedientespagos/web_api_urls.py`, incluidos desde
  `src/backends/comedores/comedores_runtime/web_api_urls.py`;
  `src/backends/config/url_registry.json` regenerado con `generar_registro_urls`.
- `src/backends/config/middlewares/admindocs.py`: las rutas nuevas quedan fuera
  del atajo HEAD de admindocs.
- `src/backends/comedores/expedientespagos/web_preview.py`: entradas React sin
  montar (`expedientes_preview_patterns`), assets en `/expedientespagos/react/assets/`.
- `src/frontends/apps/sisoc/src/routes/expedientesPagos.tsx` (ruta, ficha,
  formulario y baja) y `routes/expedientesPagosList.tsx` (listado y modal de
  columnas), registrados en `routes/index.ts`.
- Pruebas: `src/backends/comedores/expedientespagos/test_web_expedientespagos_api.py`,
  `src/backends/comedores/expedientespagos/test_web_preview_expedientespagos.py` y
  `src/frontends/apps/sisoc/src/routes/expedientesPagos.test.tsx`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/comedores/expedientespagos/comedores/<comedor_id>/` | `ExpedientesPagosListView`: orden por período, celdas de `_build_expediente_pago_list_item`, preferencias de columnas, botón de alta con los cuatro permisos; comedor inexistente sin filas; `page` fuera del paginador global 404 |
| `GET /api/web/comedores/expedientespagos/<pk>/` | `ExpedientesPagosDetailView`: valores con los filtros del template (`monto_sin_decimales`, `d/m/Y`, «-»); inexistente o dado de baja 404 |
| `GET/POST .../comedores/<comedor_id>/crear/` | Alta nativa: servicio y `form_valid`; 400 con `reset_form: true` (la página nativa muestra el formulario vacío); comedor inexistente 404 |
| `GET/POST .../<pk>/editar/` | Edición nativa con las banderas de rol; 400 con el formulario ligado |
| `GET/POST .../<pk>/eliminar/` | Confirmación con `cascade_preview` y baja lógica con actor; mensaje «Expediente dado de baja correctamente.» y destino `/acompanamientos/acompanamiento/` |

Acceso (sin cambios, ver
[brechas de acceso conservadas](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md)):
G1 primero (401 sin sesión, 403 con `state` si hay un requisito pendiente);
después, lectura con cualquier sesión y operaciones con uno de
`comedores.view_comedor`, `admisiones.view_admision`,
`acompanamientos.view_informacionrelevante` o
`expedientespagos.view_expedientepago` (superusuario incluido), en GET y POST.

Solo los 23 campos que la página renderiza llegan al formulario: `deleted_at`,
`deleted_by`, `comedor` y `mes_convenio` nunca se leen del pedido. Las
escrituras exigen CSRF y la pantalla no reintenta: un resultado incierto se
informa sin reenviar.

Hallazgo fijado por pruebas (no corregido): el alta nativa guarda dos filas.
`ExpedientesPagosService.crear_expediente_pago` crea la del comedor y después
`CreateView.form_valid` vuelve a guardar el formulario, que excluye `comedor`,
así que queda una segunda fila con `comedor` nulo que no aparece en ningún
listado. La API reproduce lo mismo por paridad.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: pruebas nuevas en rojo sobre la base (módulo inexistente) y en verde
  (36). El alta nativa con doble fila se caracterizó en la base antes de escribir
  la API.
- Frontend: prueba de ruta en rojo (módulo inexistente) y en verde (10); Vitest
  completo tres veces, `tsc`, ESLint y build de Vite.
- Visual (S13), 10 estados (listado con y sin botón de alta, vacío, ficha con y
  sin observaciones, alta vacía, alta inválida, edición, edición con errores,
  baja) en 1440x900 y 390x844: contenido fuera del menú igual, desvío máximo
  0,02 px, diferencia de píxeles 0,000 % y orden de Tab fuera del menú igual.
  Anónimo, sin permiso, página inválida y objeto inexistente responden igual.
- Recorrido: el alta desde React y desde el HTML deja el mismo par de filas y
  llega al mismo listado; la baja desde React lleva al listado de
  acompañamiento con el mensaje nativo.
- G1 de punta a punta (core y runtime de Comedores con gunicorn): listado,
  ficha, alta, edición y baja por core → compuerta → runtime; anónimo 401,
  requisito pendiente 403 con `state`, alta sin permiso 403, POST sin CSRF 403 y
  el header del cliente se descarta.

## Limitaciones

- Diferencias del marco compartido (`SisocShell`): nombre accesible del logo y
  menú móvil, igual que en las otras pantallas.
- El modal de columnas repite el de `routes/acompanamientosList.tsx`, que no lo
  exporta; conviene extraerlo a un módulo compartido.
- La ficha de un expediente sin comedor falla en la página nativa (`{% url %}`
  sin `comedor_id`); la API falla igual. No hay enlace vivo a esas filas.
