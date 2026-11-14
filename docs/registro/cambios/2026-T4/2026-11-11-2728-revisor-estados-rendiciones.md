# Usuario revisor de estados de rendiciones (#2728, punto 1)

## Qué cambia

Se agrega el permiso `rendicioncuentasmensual.change_review_stage_state`
(«Puede modificar el estado de rendiciones en revisión»). Quien lo tiene ve, en
la tarjeta «Acciones del proceso» del detalle de una rendición, un selector
para enviarla a Pendiente, En curso o Subsanado de Revisión Territorial o de
Revisión para Carga, siempre que la rendición esté en una de esas dos etapas.

- No se ofrece «Pendiente de correcciones»: implica una interacción con la PWA.
- Auditoría y Regularización no cambian, ni en lógica ni en permisos.
- Después del cambio la rendición se gestiona como cualquier otra en ese
  estado, con el permiso de la etapa destino.

## Decisiones

- La regla vive en `RendicionProcesoService.cambiar_estado_revision`
  (`src/backends/comedores/rendicioncuentasmensual/services.py`); la vista solo
  autoriza y delega. Sigue el patrón de permisos por etapa de
  `docs/registro/cambios/2026-T3/2026-08-21-permisos-etapas-rendiciones.md`.
- El cambio no modifica documentos ni solicitudes de faltantes.
- Volver a Revisión Territorial borra `fecha_validacion_territorial` y reinicia
  las confirmaciones de lectura; avanzar a Revisión para Carga registra esa
  fecha si faltaba.
- Enviar a Territorial en curso o subsanado respeta el cupo de una rendición
  por proyecto (#2642). Para reutilizar esa regla se separó
  `_bloquear_revision_territorial` en bloqueo y detección de conflicto, sin
  cambiar su comportamiento.
- El permiso no se asigna a ningún grupo y no concede acceso al listado ni al
  detalle por sí solo: se combina con un permiso de acceso existente.
- Cada cambio manual queda en el log de aplicación con rendición, usuario y
  estados; no se agregó un historial persistente.

## Despliegue

Requiere revisión técnica: incluye la migración
`rendicioncuentasmensual.0030_issue_2728_permiso_revisor_estados`, que solo
declara el permiso (sin cambios de esquema). Ejecutar `python manage.py migrate`
con el migrador y asignar el permiso desde Usuarios > Grupos.

## Pendiente

El punto 2 del issue (previsualización del documento compilado) se trata en un
PR aparte.
