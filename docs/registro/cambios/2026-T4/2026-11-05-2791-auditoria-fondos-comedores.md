# Cambio: pagos y rendiciones de comedores entran al log de auditoría

## Alcance

Issue #2791, quinta parte (antes: VAT, Celiaquía, PAS y VPSL, en
`docs/registro/cambios/2026-T4/`). Los expedientes de pago y las rendiciones
de cuentas de comedores no tenían ningún modelo registrado en
django-auditlog: un cambio de monto, de orden de pago o de estado de una
rendición no quedaba en el visor de auditoría (`/auditoria/`).

Se suman seis modelos a la lista única de
`src/backends/kernel/audittrail/constants.py`. No hay modelos, migraciones ni
permisos nuevos.

| Etiqueta en el visor | Modelo | Campos que no se registran |
|---|---|---|
| Expediente de pago | `expedientespagos.ExpedientePago` | `fecha_creacion` |
| Rendición de cuentas mensual | `rendicioncuentasmensual.RendicionCuentaMensual` | `fecha_creacion`, `ultima_modificacion`, `usuario_ultima_modificacion` |
| Documento de rendición mensual | `rendicioncuentasmensual.DocumentacionAdjunta` | `fecha_creacion`, `ultima_modificacion` y las marcas de visualización (`visualizacion_etapa`, `visualizacion_usuario`, `visualizacion_fecha`) |
| Solicitud de documento faltante | `rendicioncuentasmensual.SolicitudDocumentoFaltante` | `fecha_creacion` |
| Rendición de cuentas final | `rendicioncuentasfinal.RendicionCuentasFinal` | — |
| Documento de rendición final | `rendicioncuentasfinal.DocumentoRendicionFinal` | `fecha_modificacion` |

## Criterio

- Son datos institucionales de fondos públicos, no personales: se registran
  completos, incluidas las observaciones.
- Se excluyen las fechas que cambian en cada guardado y
  `usuario_ultima_modificacion`, que repite al actor del evento.
- Las marcas de visualización de un documento cambian cada vez que alguien lo
  abre: registrarlas llenaría el log sin aportar un cambio real.
- Quedan afuera los catálogos `TipoDocumentoRendicionFinal` y
  `EstadoDocumentoRendicionFinal`, y la relación M2M `rendiciones_incluidas`
  de la rendición mensual (la lista única no soporta M2M).

## Lo que no queda en el visor

auditlog registra solo lo que pasa por `save()`. En
`src/backends/comedores/rendicioncuentasmensual/services.py` hay tres
actualizaciones en lote que no generan evento:

- al reabrir una revisión, los documentos validados vuelven a "presentado"
  en lote (sí queda el cambio de estado de la rendición);
- al cargar un documento, las solicitudes de faltante de esa categoría se
  desactivan en lote;
- el reseteo de las marcas de visualización (que de todos modos no se
  registran).

Además, el borrado lógico y la restauración, igual que en el resto de los
modelos de la lista.

## Verificación

- `pytest src/backends/comedores/tests/test_auditoria_fondos_comedores.py`:
  el cambio de monto y orden de pago, el cambio de estado de una rendición y
  de un documento, y la presentación física de la rendición final quedan con
  `[viejo, nuevo]`; abrir un documento no genera evento.
- `pytest src/backends/kernel/tests/test_audittrail_registry_unit.py`: los
  seis modelos están en el allowlist.
- Tests de pagos, rendiciones y admin de comedores: 338 pasan. Fallan 7
  `*_sin_n_mas_1` de `test_admin_operaciones_comedores.py` y
  `test_admin_operaciones_flujos.py`, que fallan igual sin este cambio.
