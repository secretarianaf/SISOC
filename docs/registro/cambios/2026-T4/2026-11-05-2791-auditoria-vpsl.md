# Cambio: los modelos críticos de VPSL entran al log de auditoría

## Alcance

Issue #2791, cuarta parte (antes: VAT, Celiaquía y PAS, en
`docs/registro/cambios/2026-T4/`). Ver Para Ser Libre no tenía ningún modelo
registrado en django-auditlog: los cambios de estado quedaban en sus tablas
propias (`HistorialEstadoVPSL`, `HistorialLaboratorioVPSL`,
`HistorialCierreDiarioVPSL`, `HistorialChecklistSedeVPSL`), que no se ven en
el visor de auditoría (`/auditoria/`), y las ediciones de datos no quedaban en
ningún lado.

Se suman siete modelos a la lista única de
`src/backends/kernel/audittrail/constants.py`. No hay modelos, migraciones ni
permisos nuevos.

| Etiqueta en el visor | Modelo | Qué se registra |
|---|---|---|
| Itinerario VPSL | `ItinerarioVPSL` | todo menos `created_at` y `updated_at` |
| Evaluación de sede VPSL | `EvaluacionSedeItinerarioVPSL` | todo menos `updated_at` |
| Sede VPSL | `SedeVPSL` | todo |
| Jornada VPSL | `JornadaVPSL` | todo menos `created_at`, `updated_at` y `referente_datos_renaper` |
| Registro nominal VPSL | `RegistroNominalVPSL` | solo `estado`, `numero_acta`, `numero_sobre`, `validado_renaper` y `no_verificar_renaper` |
| Caso de laboratorio VPSL | `CasoLaboratorioVPSL` | todo menos `updated_at`, `destinatario` e `incidencia` |
| Cierre diario VPSL | `CierreDiarioVPSL` | todo |

## Criterio

- El registro nominal es la atención oftalmológica de un chico o chica:
  resultado, graduación, prescripción y datos personales son datos de salud de
  menores. El log es exportable y sobrevive al borrado, así que usa lista de
  campos permitidos (como "Nómina CDI" y "Legajo Celiaquía") y solo registra
  el circuito administrativo. El visor sigue mostrando el registro con su
  `__str__` (apellido, nombre y número de acta).
- En la jornada no se registra `referente_datos_renaper`, la respuesta cruda
  de RENAPER del referente.
- En el caso de laboratorio no se registran `destinatario` ni `incidencia`,
  que son texto libre sobre la persona. El estado y las fechas sí.
- Quedan afuera a propósito: las tablas `Historial*VPSL` (ya son registros),
  `ChecklistJornadaVPSL` (ya tiene `HistorialChecklistSedeVPSL`) y el catálogo
  `VehiculoVPSL`.
- Las relaciones M2M (sedes del itinerario, vehículos de la jornada) no se
  registran: la lista única no soporta M2M.

## Lo que no queda en el visor

VPSL no tiene actualizaciones masivas: los cambios pasan por `save()` y quedan
registrados. La única excepción es el borrado lógico y la restauración, igual
que en el resto de los modelos de la lista, y la asignación automática del
`codigo` del itinerario justo después del alta.

## Verificación

- `pytest src/backends/vpsl/ver_para_ser_libre/tests/test_auditoria_vpsl.py`:
  el cambio de estado de itinerario y jornada queda con `[viejo, nuevo]`, sin
  la respuesta de RENAPER ni timestamps; el registro nominal solo registra el
  cambio de estado, y ni el alta ni la modificación llevan DNI, nombre,
  resultado, prescripción ni teléfono.
- `pytest src/backends/kernel/tests/test_audittrail_registry_unit.py`: los
  siete modelos están en el allowlist con app label `ver_para_ser_libre`.
- Suite de VPSL: 169 pasan. Fallan 2 `test_listados_sin_n_mas_1` de
  `test_admin_operaciones_vpsl.py`, que fallan igual sin este cambio.


## Corrección de revisión: representación del objeto (2026-11-11)

`django-auditlog` guarda `str(modelo)` en `LogEntry.object_repr`, además del
mapa `changes`. La lista de campos permitidos no protege esa representación:
el registro nominal y el caso de laboratorio incluyen el nombre de la persona;
el legajo de Celiaquía incluye nombre y documento.

Las tres definiciones nuevas marcan `redact_object_repr` en la fuente única
`src/backends/kernel/audittrail/constants.py`. La señal `pre_save` de
`src/backends/kernel/audittrail/signals.py` reemplaza esa representación por
la etiqueta del modelo y su identificador, sin importar modelos de verticales.
No modifica los estados auditados ni las etiquetas de modelos no marcados.
Se conserva la trazabilidad sin duplicar datos personales en el texto del log.
No se reescriben en lote eventos históricos; solo afecta entradas guardadas
por el ORM después de incorporar la corrección.

Verificación de la corrección: tres regresiones fallaron antes del cambio y
pasaron después; la etiqueta institucional de Comedor se mantuvo sin cambios.
La prueba aislada usa Django 5.2.17 y django-auditlog 3.2.1 sin base de datos.
También se reforzaron los tests de integración de Celiaquía y VPSL para comprobar
la representación tanto en el alta como en la modificación. Estos dos módulos
requieren el entorno completo y quedan pendientes de CI; no se ejecutaron con
datos reales ni se hizo un deploy. Requiere revisión técnica (seguridad/kernel).
