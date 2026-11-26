# Cambio: los modelos críticos de Celiaquía entran al log de auditoría

## Alcance

Issue #2791, segunda parte (la primera fue VAT,
`docs/registro/cambios/2026-T4/2026-11-04-2791-auditoria-vat.md`). Celiaquía
no tenía ningún modelo registrado en django-auditlog: las decisiones sobre
expedientes y legajos solo quedaban en sus tablas de historial propias
(`ExpedienteEstadoHistorial`, `HistorialValidacionTecnica`, `HistorialCupo`),
que no se ven en el visor de auditoría (`/auditoria/`).

Se suman cinco modelos a la lista única de
`src/backends/kernel/audittrail/constants.py`. No hay modelos, migraciones ni
permisos nuevos.

| Etiqueta en el visor | Modelo | Qué se registra |
|---|---|---|
| Expediente Celiaquía | `celiaquia.Expediente` | todo menos `fecha_creacion`, `fecha_modificacion` y `observaciones` |
| Legajo Celiaquía | `celiaquia.ExpedienteCiudadano` | solo `estado`, `rol`, `archivos_ok`, `revision_tecnico`, `resultado_sintys`, `cruce_ok`, `estado_cupo`, `es_titular_activo` y `estado_validacion_renaper` |
| Cupo provincial Celiaquía | `celiaquia.ProvinciaCupo` | todo |
| Asignación de técnico Celiaquía | `celiaquia.AsignacionTecnico` | todo menos `fecha_asignacion` |
| Pago Celiaquía | `celiaquia.PagoExpediente` | todo menos `creado_en` y `modificado_en` |

## Criterio

- Estar en un legajo de Celiaquía ya es un dato de salud. El log es exportable
  y sobrevive al borrado, así que el legajo usa lista de campos permitidos
  (como "Nómina CDI"): se registran las decisiones del circuito y no los
  motivos en texto libre (`subsanacion_motivo`, `observacion_cruce`,
  `subsanacion_renaper_comentario`), los archivos ni las fechas automáticas.
  El nombre con que el visor muestra el legajo sigue siendo su `__str__`
  (DNI y nombre del ciudadano), igual que con "Ciudadano".
- Quedan afuera a propósito: las tablas de historial propias y
  `CupoMovimiento` (ya son registros), `PagoNomina` (una fila por persona y
  por pago, volumen alto), `Subsanacion*`, `DocumentoLegajo`,
  `HistorialComentarios` y `RegistroErroneo*`. Se pueden sumar después.

## Lo que no queda en el visor

auditlog registra solo lo que pasa por `save()`. En Celiaquía hay caminos
masivos con `.update()` o `bulk_create` que no generan evento:

- la importación del Excel crea los legajos con `bulk_create`;
- el cruce SINTYS marca `cruce_ok`/`resultado_sintys` en lote
  (`src/backends/celiaquia/celiaquia/services/cruce_service/impl.py`);
- la confirmación masiva de subsanación pasa los legajos a SUBSANADO en lote
  (`src/backends/celiaquia/celiaquia/views/expediente_subsanacion.py`);
- `ProvinciaCupo.usados` se ajusta con `.update()` en cada alta o baja de
  cupo (sí queda el cambio de `total_asignado`, que es la configuración);
- al asignar un técnico, la desactivación de la asignación anterior;
- el borrado lógico y la restauración, igual que en el resto de los modelos
  de la lista.

Las decisiones de a un legajo (revisión técnica, cupo, titularidad,
validación RENAPER, rol) sí pasan por `save()` y quedan registradas.

## Verificación

- `pytest src/backends/celiaquia/celiaquia/tests/test_auditoria_celiaquia.py`:
  la revisión técnica de un legajo queda con `[viejo, nuevo]` y sin motivo,
  observación de cruce, archivos ni timestamps; el cambio de estado del
  expediente queda sin `observaciones`; el cambio de cupo provincial y la
  asignación de técnico generan evento.
- `pytest src/backends/kernel/tests/test_audittrail_registry_unit.py`: los
  cinco modelos están en el allowlist del visor con app label `celiaquia`.
- Suite de Celiaquía: 665 pasan. Fallan 3 `test_listados_sin_n_mas_1` de
  `test_admin_operaciones_celiaquia.py`, que fallan igual sin este cambio.
