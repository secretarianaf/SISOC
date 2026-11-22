# Cambio: mutaciones de relevamientos en React sobre G1 v1 (#2785, R01.02)

## Alcance

Cuarta entrega del
[contrato R01-R03](../../../plans/2026-T4/2026-11-10-2785-relevamientos-seguimientos-actas-m2.md),
sobre el
[listado y detalle](2026-11-12-2785-react-relevamientos-listado-detalle.md) y
el [detalle de seguimientos y actas](2026-11-12-2785-react-relevamientos-seguimientos-actas.md):

- Edición en línea del Número de IF en el listado (`POST /comedores/<c>/relevamiento/listar`).
- Baja del relevamiento (`/comedores/<c>/relevamiento/<pk>/eliminar`): la
  pantalla de confirmación con su vista previa en cascada pasa a React.
- Revisión del coordinador del relevamiento (`POST .../revision`) desde el modal
  del detalle.

R01.03 no agrega código: el botón «Descargar PDF» ya es el enlace GET nativo
(D3). `relevamiento_crear` y `relevamiento_editar` siguen nativos (D2) y React
no matchea esas URL. Los POST nativos siguen funcionando con las mismas
entradas. No cambia vistas, plantillas ni modelos. No activa React en producción.

Archivos:

- `src/backends/comedores/relevamientos/web_api_mutations.py` (nuevo) y
  `web_api_urls.py`: `POST .../relevamiento/numero-if/`,
  `GET/POST .../relevamiento/<pk>/eliminar/` y `POST .../relevamiento/<pk>/revision/`
  bajo `/api/web/comedores/relevamientos/<comedor>/`; `web_api_views.py` suma
  `urls.numero_if` y `urls.revision_api`; `src/backends/config/url_registry.json`
  regenerado y `src/backends/config/middlewares/admindocs.py` con las rutas nuevas.
- `src/backends/comedores/relevamientos/web_preview.py`: entrada React sin
  montar para la confirmación de baja (el POST sigue siendo la vista nativa).
- `src/frontends/apps/sisoc/src/routes/relevamientosApi.tsx` (POST sin
  reintento, mensajes entre pantallas), `relevamientosBaja.tsx`, y cambios en
  `relevamientos.tsx` (IF en línea, modal de revisión, ruta `.../eliminar`).
- Pruebas: `tests/test_web_relevamientos_mutaciones_api.py`,
  `routes/relevamientosMutaciones.test.tsx` y casos nuevos de
  `tests/test_web_preview_relevamientos.py`.

## Comportamiento

Cada endpoint repite la regla nativa y reutiliza su código:

- Número de IF: permiso de ruta `view_relevamiento` y además
  `has_perm("relevamientos.change_relevamiento")` (403 «No tiene permisos para
  editar el Número de IF.»); más de 255 caracteres, 400 con el error `max_length`
  del campo; el resto corre `RelevamientoListView.post` (`update()` sin señales,
  confirma aunque el id no exista o sea de otro comedor, vacío a `NULL`).
- Baja: permiso de ruta `change_relevamiento`, búsqueda por `pk` sin
  `comedor_pk`; GET con la vista previa de `build_delete_preview`; POST con
  `RelevamientoDeleteView` (baja lógica en cascada y la señal de baja en
  GESTIONAR); repetida, 404. El mensaje de éxito queda en la cola de Django para
  la ficha del comedor a la que redirige.
- Revisión: permiso `review_relevamiento`, transacción con `select_for_update`
  por `pk` y `comedor_id` y `aplicar_revision_coordinador`; ya validado o sin
  cargar, 409; resultado inválido u observación faltante, 400; comedor ajeno, 404.

El POST exige CSRF (`SessionAuthentication`); anónimo 401 por G1. En React un
504 `{"uncertain": true}` se muestra como «No se pudo confirmar el resultado.»
con un botón «Recargar» (GET) y el envío queda deshabilitado: nunca se reenvía.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada; hoja de AdminLTE
presente.

- Backend: pruebas nuevas, `black` y `pylint` 10/10.
- Frontend: Vitest del proyecto completo, `tsc`, ESLint y build de Vite.
- Visual (S13): confirmación de baja, modal de revisión del detalle y edición
  de IF en el listado, en 1440x900 y 390x844; anónimo, sin permiso y relevamiento
  inexistente responden igual.

## Limitaciones

- Tras guardar un IF la pantalla se actualiza en el lugar con el aviso (la vista
  nativa recarga la página); el estado guardado y el mensaje son los mismos.
- La asimetría de permisos de la baja (`change_relevamiento`, botón siempre
  visible) y la edición de registros validados se conservan (D12).
