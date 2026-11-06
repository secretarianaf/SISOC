# Cambio: operaciones de soporte en el admin de Celiaquía para pedidos recurrentes

Relacionado: `docs/registro/cambios/2026-T4/2026-10-26-2789-admin-unfold.md`
(mecanismo `core.admin_operaciones`).

## Problema

Soporte pedía a desarrollo correcciones manuales sobre legajos de Celiaquía
(`ExpedienteCiudadano`) que no tenían camino en la pantalla:

- devolver a PENDIENTE un legajo aprobado por error: #2758 y #2861;
- eliminar legajos duplicados cargados con CUIL/DNI incorrecto: #2483 y #2488.

El objetivo es que un superusuario lo resuelva desde el admin, con auditoría y
los mismos efectos que el flujo normal, sin SQL ni intervención de desarrollo.

## Operaciones nuevas en `ExpedienteCiudadanoAdmin`

### Volver a pendiente (corregir evaluación)

- **Service:** `RevisionService.volver_a_pendiente(legajo, usuario, motivo)`.
- **Desde:** APROBADO, RECHAZADO o SUBSANADO. Desde PENDIENTE responde
  "El legajo ya está en PENDIENTE."; desde SUBSANAR se rechaza (ver límites).
- **Permiso:** administradores y coordinadores de Celiaquía, igual que
  `CorregirEvaluacionView`.
- **Efectos, en una transacción:**
  - relee el legajo con `select_for_update` y valida su estado sobre esa
    lectura: una doble ejecución (doble clic o dos operadores) falla con
    "El legajo ya está en PENDIENTE." en vez de liberar cupo dos veces;
  - si el legajo ocupaba cupo (DENTRO) o estaba en lista de espera (FUERA),
    `CupoService.liberar_slot` lo deja NO_EVAL; con DENTRO descuenta
    `ProvinciaCupo.usados` y registra `HistorialCupo` y `CupoMovimiento` BAJA;
  - `revision_tecnico` pasa a PENDIENTE;
  - `HistorialValidacionTecnica` con estado anterior, nuevo, usuario y motivo;
  - `LogEntry` de auditlog con el motivo y `revision_tecnico` antes y después.
- **Guardas:** motivo obligatorio; si la provincia no tiene cupo configurado,
  falla sin cambiar nada; si el legajo ya figura en una nómina de pago
  (`PagoNomina`), no se toca.
- **UI:** confirmación destructiva, por registro (no en lote).
- La regla general de `validar_transicion` no cambia: un legajo aprobado o
  rechazado sigue sin poder aprobarse, rechazarse ni subsanarse de nuevo hasta
  que soporte lo devuelva a PENDIENTE.

### Eliminar legajo (baja lógica)

- **Service:** `RevisionService.verificar_permiso(..., "ELIMINAR")` y
  `RevisionService.eliminar`, lo mismo que el botón Eliminar del expediente.
- **Efectos:** baja lógica en cascada con `deleted_by`, liberación de cupo si
  estaba DENTRO y `LogEntry` con el motivo. Se restaura desde la papelera.
- **Guardas:** motivo obligatorio, confirmación destructiva; en lote hasta 100.

## Pedidos analizados y no implementados

- **Cambiar el estado de un expediente a EN_ESPERA** (#1807: ASIGNADO o
  CONFIRMACION_DE_ENVIO a EN_ESPERA). Un solo pedido, y desde ASIGNADO hace
  falta decidir qué pasa con el técnico asignado y con los legajos ya
  revisados: la revisión técnica no mira el estado del expediente.
- **Eliminar un expediente de pago y sus derivados** (#2631). El propio issue
  pide revisar la lógica de pagos antes de borrar.
- **Volver a pendiente desde SUBSANAR.** Queda abierta la `Subsanacion`
  pendiente y bloquea la edición de documentos (`permissions.py`). Falta decidir
  si se cierra, se descarta o se conserva.

## Límites

- Si el legajo se vuelve a aprobar después del cruce SINTYS, la aprobación no
  reserva cupo (pasa lo mismo con `CorregirEvaluacionView`). Ese cupo hay que
  reservarlo con el flujo de cruce o de cupo que corresponda.
- La baja desde el admin no muestra el aviso de menores sin responsable que
  muestra la pantalla; la descripción de la operación pide revisar el expediente
  antes.

## Verificación

- `src/backends/celiaquia/celiaquia/tests/test_admin_operaciones_celiaquia.py`:
  vuelta a pendiente desde cada estado, cupo y movimientos, historial, auditlog,
  errores (PENDIENTE, SUBSANAR, nómina de pago, cupo no configurado), flujo por
  URL con y sin motivo, nueva aprobación después de volver; baja lógica con
  cupo, `deleted_by`, auditoría y permiso.
- Suite de `src/backends/celiaquia` y `kernel/tests/test_admin_operaciones.py`.
