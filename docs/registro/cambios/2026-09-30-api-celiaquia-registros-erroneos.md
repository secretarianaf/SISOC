# 2026-09-30 - API de Celiaquía: registros erróneos y extracción del service

## Contexto

La API REST de Celiaquía (`/api/celiaquia/`) cubría el alta de expedientes, la
revisión de legajos, cupos y pagos, pero no los **registros erróneos**: las filas
del Excel masivo que no se pudieron importar. Sin esos endpoints, el front v2 no
puede corregir una fila, reprocesarla ni descartarla, que es el flujo con el que
la provincia arregla una carga.

Esa lógica vivía **dentro de `celiaquia/views/expediente.py`**, no en un service.
Copiarla del lado de la API habría dejado dos validaciones vivas: el riesgo
concreto es que la API acepte una fila que la pantalla rechaza, o al revés.

## Cambios aplicados

### 1. Se extrajo `celiaquia/services/registros_erroneos_service/`

Se movieron **sin cambios** 19 funciones desde la vista:

- Normalización y consolidación del payload (`_normalizar_datos_registro_erroneo`,
  `_consolidar_datos_registro_erroneo`, `_limpiar_datos_registro_erroneo`,
  `_aplicar_defaults_registro_erroneo`).
- Resolución de localidad, municipio, nacionalidad y provincia.
- Validación (`_validar_datos_registro_erroneo`) y el parseo de campos inválidos
  que la pantalla usa para resaltar los inputs.
- La alerta persistente de la importación (4 funciones).

Y se sumaron tres operaciones que antes eran el cuerpo de las vistas:
`actualizar`, `reprocesar` y `eliminar`, más `puede_gestionar`.

La vista las reexporta con sus nombres viejos, así que el resto del módulo y sus
tests las siguen usando igual. Los permisos genéricos (`is_admin`,
`is_provincial`, `user_has_permission`) salen de `celiaquia/scope.py`, que ya los
centralizaba.

`celiaquia/views/expediente.py` pasó de 2679 a ~2130 líneas.

### 2. Endpoints nuevos

| Método | Ruta | Qué hace |
| --- | --- | --- |
| POST | `expedientes/{id}/registros-erroneos/{registro_id}/actualizar/` | Corrige una fila |
| POST | `expedientes/{id}/registros-erroneos/reprocesar/` | Reintenta crear los legajos |
| DELETE | `expedientes/{id}/registros-erroneos/{registro_id}/` | Descarta una fila |

Los tres delegan en el service, con el mismo permiso que la pantalla. El de
actualizar devuelve un 400 de DRF con `detail` e `invalid_fields`, que es lo que
el formulario necesita para resaltar los campos.

La transacción la abre ahora el service, que es el dueño de la operación; se le
sacó el `@transaction.atomic` a la vista para no anidarla.

### 3. Contrato

`frontends/packages/api/openapi.yaml` pasó de 51 a 54 rutas. Los tipos TS se
regeneraron y `npm run api:check` queda en verde.

## Decisiones

- **Se movió el código verbatim, no se reescribió.** El objetivo era que el
  comportamiento no cambiara; reescribir habría hecho imposible afirmarlo.
- **El alcance territorial no se duplica**: lo aplica el `get_queryset()` del
  ViewSet, así que un expediente de otra provincia da 404 y no 403. No confirmar
  la existencia es deliberado.

## Validación

- `pytest -n auto`: **5548 passed, 14 skipped**.
- `celiaquia/tests/test_api_escrituras.py`: 6 tests nuevos que verifican que cada
  endpoint entre por el service y que el técnico no pueda gestionar registros
  erróneos.
- `tests/test_celiaquia_expediente_view_helpers_unit.py`: los 29 pasan. Hubo que
  reapuntar los `patch` al service, porque el seam se movió con la lógica.
- Se arregló de paso `test_recepcionar_view_permission_and_success_paths`, que ya
  venía fallando desde que `recepcionar` se extrajo a `ExpedienteService`:
  parcheaba `_set_estado`, que la vista ya no llama.
- `black` limpio; `pylint` 8.60/10 sobre el service nuevo (el resto de los
  services del repo puntúa más bajo por el mismo artefacto de resolución de
  imports).

## Pendiente

La API todavía no cubre estas operaciones del front Django:

- Legajo: editar, eliminar y corregir evaluación final.
- Subsanación: responder con archivos, confirmar, y la respuesta vía RENAPER.
- Comentarios técnicos: listar, crear y la preview del motivo.
- Validación RENAPER de un legajo.
- Descargas y lookups: plantilla de Excel, descarga del Excel masivo,
  `localidades_lookup`, importar desde archivo, cruce por CUIT y exportar nómina
  actual del pago.

Los comentarios técnicos, la subsanación y RENAPER ya tienen service propio, así
que son directos. El resto tiene la lógica en la vista y necesita la misma
extracción que se hizo acá.
