# 2026-10-05 - Celiaquía API: permisos de módulo y paridad con la pantalla

Correcciones de la revisión del PR #2644, antes de mergear.

## Problema

La API `/api/celiaquia/` se armó suponiendo que "logueado" equivalía a
"autorizado". No declaraba `permission_classes`, así que aplicaba el default de
DRF (`IsAuthenticated`), mientras que las pantallas exigen
`celiaquia.view_expediente`, `view_cupo_dashboard` o `view_reporte_provincias`
(`celiaquia/urls.py`, `global_urls.py`). Además, `scope.is_provincial` es
verdadero para cualquier perfil con `es_usuario_provincial`, que también usan
CDI, VAT y VPSL.

Consecuencias:

- Un usuario provincial de otro programa listaba expedientes y legajos (DNI,
  nombre, archivos) de su territorio y podía crear, procesar e importar.
- Cualquier usuario logueado leía el reporte nacional con DNI, los titulares de
  cupo de todas las provincias y la nómina de pagos.

Algunas acciones tampoco aplicaban las reglas que la pantalla sí aplica:

- **Baja de legajos (provincia):** se podía eliminar en cualquier estado, porque
  la API no llamaba `can_delete_legajo`.
- **Pedir subsanación (provincia dueña):** podía hacerlo, cuando es una acción
  del revisor.
- **Carga de documentos:** se aceptaba en cualquier estado.
- **Asignar técnico:** aceptaba a cualquier usuario y en cualquier estado.
- **Confirmar envío:** no controlaba los registros erróneos pendientes.

## Cambios

- **Permiso de módulo** en `celiaquia/api_permissions.py`:
  - `TieneAccesoExpedientes` para expedientes, legajos y catálogos.
  - `TieneAccesoCupos` para cupos, movimientos y pagos. Los pagos se alcanzan
    desde el detalle de cupo.
  - `TieneAccesoReporte` para el reporte.
- **Baja provincial:** `RevisionService.eliminar` revalida **siempre** con
  `can_delete_legajo` y el expediente bloqueado. Antes dependía de que el
  llamador lo pidiera.
- **`solicitar-subsanacion`** exige `can_review_legajo`, como `LegajoSubsanarView`.
- **`archivos`** exige `can_edit_legajo_files` y responde 409 cuando el
  expediente ya se envió o el legajo está en subsanación.
  `documentos_legajo_bloqueados` pasó a `permissions.py` para que la pantalla y
  la API compartan la regla.
- **`asignar-tecnico`:**
  - Busca el técnico en `tecnicos_asignables()`.
  - `ExpedienteService.asignar_tecnico` exige RECEPCIONADO o ASIGNADO.
- **`confirmar-envio`** usa `ExpedienteService.exigir_sin_registros_erroneos`.
- **Procesar, importar, confirmar y crear legajos:** fuera de admin y provincia,
  solo se operan los expedientes propios, como en las vistas Django.
- **`cruce`:** admin o técnico asignado, como `SubirCruceExcelView`.
- **`revisar`** corre atómico: un adjunto inválido ya no deja el cupo liberado.

## Guards de estado

- `ESTADOS_PARA_CRUCE` vuelve a incluir `CRUCE_FINALIZADO`. El PR lo había
  dejado afuera y rompía **"Reprocesar cruce"** en la pantalla Django.
- La exportación de la nómina Sintys aplica el guard que el PR declaraba y no
  llamaba: estados ASIGNADO, PROCESO_DE_CRUCE o CRUCE_FINALIZADO.

## Contrato y front

- `motivo-preview` devolvía 500 porque usaba métodos que `development` quitó
  con el issue #2592. Ahora devuelve `opciones` y `tiene_observaciones`, igual
  que `LegajoMotivoPreviewView`.
- React elige las observaciones (`observaciones_ids`) y adjunta documentación
  complementaria al subsanar (#2523): `componentes/MotivoRevision.tsx`.
- Los pagos navegaban con el nombre de la provincia (`Number(nombre)` daba NaN).
  - Ahora navegan con `provincia_id`, que expone `PagoExpedienteSerializer`.
  - El back filtra `pagos/?provincia=`.
  - La lista pagina.
- El detalle de cupo usa `cupos/{id}/`. Antes buscaba en la primera página del
  listado, así que desde la provincia 11 no se encontraba.
- Los listados paginados calculan las páginas con `PAGE_SIZE` = 10. Antes
  suponían 20, lo que dejaba páginas sin alcanzar.
- `ocupados`, `suspendidos` y `fuera-de-cupo` hacen `select_related` y la
  cantidad de consultas no crece con los legajos. Siguen sin paginar, como la
  pantalla.
- El Excel del alta y de la previsualización valida `.xlsx` y 5 MB, igual que
  `ExpedienteForm`.

## Infra y CI

- `api/celiaquia/` se suma a los `url_prefixes` de celiaquía en
  `config/backends.json`. Sin eso, en el deploy separado el core no reenviaba la
  API y todo daba 404.
- `front_celiaquia` entra en `docker-compose.deploy.yml` con el mismo esquema
  que `front_vpsl`. El tag sale de `SISOC_RELEASE_SHA`.
- Se quitan el segundo router `/v2/` (`kernel/core/frontend_v2.py`,
  `FRONTEND_V2_SERVICIOS`), que nada usaba, y sus tests. Queda el de
  `kernel/core/v2_frontend.py`.
- Se quita el workflow duplicado `frontend_v2.yml`: sus `paths` eran previos a
  la reestructuración y comparaba el schema equivocado. El chequeo de contrato
  de Celiaquía pasa a `frontend-v2.yml`.
- Se regeneran `config/url_registry.json`, `openapi.celiaquia.yaml` y
  `openapi.d.ts`.
- El test de formato de fechas fija la zona horaria de Argentina. En UTC, que
  es como corre CI, fallaba.

## Validación

- `pytest -n 6` de la suite completa en la imagen de CI (SQLite).
- `npm run lint`, `typecheck`, `test`, `build`, `api:check` y `types:generate`
  en `node:22.14.0`.
- `black --check`, `lint-imports` y pylint sin mensajes nuevos.

## Decisiones

- **Paridad con la pantalla antes que reglas nuevas.** Cada guard replica lo que
  ya exige la vista Django equivalente. Coordinación pierde, en la API, la
  capacidad de procesar o importar expedientes ajenos y de ejecutar el cruce:
  tampoco la tenía en la pantalla.
- **Pagos con el permiso de cupos.** Las vistas Django de pagos no tienen
  decorador; se toma el de la pantalla desde la que se navega
  (`cupo_provincia.html`).
