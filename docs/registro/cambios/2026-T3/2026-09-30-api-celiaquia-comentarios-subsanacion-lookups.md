# 2026-09-30 - API de Celiaquía: comentarios, subsanación, lookups e importación

Continuación de `2026-09-30-api-celiaquia-registros-erroneos.md`.

## Endpoints nuevos

| Método | Ruta | Delegado en |
| --- | --- | --- |
| GET | `legajos/{id}/comentarios/` | `ComentariosTecnicosService.historial` |
| POST | `legajos/{id}/comentarios/tecnico/` | `ComentariosTecnicosService.registrar` |
| GET | `legajos/{id}/motivo-preview/` | `lineas_concatenadas` + `texto_concatenado` |
| POST | `legajos/{id}/responder-subsanacion/` | `SubsanacionService.responder` |
| POST | `expedientes/{id}/importar/` | `ImportacionService.importar_legajos_desde_excel` |
| GET | `expedientes/plantilla-excel/` | `ImportacionService.generar_plantilla_excel` |
| GET | `expedientes/localidades/` | `apply_territorial_scope` |
| GET | `expedientes/{id}/excel-masivo/` | — |

El contrato pasó de 54 a 62 rutas.

## Dos reglas más que se extrajeron

Igual que con los registros erróneos, la lógica que vivía en la vista se movió
para que la API y la pantalla apliquen lo mismo:

- **`SubsanacionService.exigir_puede_responder`**: el legajo tiene que estar en
  `SUBSANAR` y no tener una subsanación RENAPER pendiente. Estaba en
  `SubsanacionRespuestaUploadView`. Sin esto, un legajo con subsanación RENAPER
  pendiente se podía responder por la API y no por la pantalla.
- **`permissions.exigir_acceso_nacion_a_comentarios`**: estaba en
  `_resolver_legajo_para_nacion`. Es la regla más delicada de este lote: un
  usuario **territorial no ve los comentarios internos aunque acumule permisos
  de Nación**, porque se publican recién al subsanar o rechazar. Duplicarla del
  lado de la API habría filtrado comentarios internos a la provincia.

## Gaps que ya estaban cubiertos

Al auditar, tres de los pendientes declarados no existían:

- **Eliminar legajo**: ya lo cubre `POST legajos/{id}/revisar/` con
  `accion: ELIMINAR`, que está en `ACCIONES_REVISION`.
- **`cruce-cuit`**: `POST expedientes/{id}/cruce/` ejecuta el mismo cruce.
- **`exportar-nomina-actual`**: `GET pagos/{id}/exportar-nomina/` ya llama a
  `PagoService.exportar_nomina_actual_excel`. Solo cambia el nombre del archivo.

## Front v2

`packages/api/src/celiaquia.ts` suma 8 requests. Las descargas piden
`responseType: "blob"`; `responderSubsanacion` arma el `FormData` con varios
archivos bajo la misma clave, como espera el `ListField` del serializer.

## Validación

- `pytest`: **5556 passed, 14 skipped**. 399 en celiaquía.
- 8 tests nuevos en `test_api_escrituras.py` (34 en total), enfocados en el
  permiso: que la provincia reciba 403 en comentarios internos, que el lookup de
  localidades no devuelva otra provincia, y que el Excel masivo solo lo baje
  coordinación.
- Front: 15 tests, `lint`, `typecheck`, `build` y `api:check` en verde.
- `pylint` en `api_views.py`: 8.68 contra 8.51 de baseline.

## Pendiente

Queda **RENAPER**: `validar-renaper` y `respuesta-subsanacion-renaper`.
`celiaquia/views/validacion_renaper.py` son 772 líneas con 24 helpers de módulo
y un `_consultar_renaper` de 219, que integra el servicio externo con reintentos.
Necesita la misma extracción a service que se hizo con los registros erróneos, y
no entra como apéndice de este lote.

También queda `legajos/{id}/editar` y `corregir-evaluacion`, con la lógica dentro
de sus vistas.
