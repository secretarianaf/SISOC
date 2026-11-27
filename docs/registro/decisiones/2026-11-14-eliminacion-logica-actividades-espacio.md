# 2026-11-14 - Eliminación lógica de actividades del espacio sin tocar `activo`

## Estado
- propuesta (la propuso el agente durante la implementación; queda a revisión en el PR)

## Contexto
- Las actividades de Abordaje Comunitario (`pwa.ActividadEspacioPWA`) solo se
  podían inactivar (`activo=False`, desde la API de la PWA o el admin). Para
  cargas erróneas hacía falta eliminarlas sin perder información.
- Los inscriptos (`pwa.InscriptoActividadEspacioPWA`) tienen la unicidad
  `uniq_inscripto_actividad_nomina_estado_pwa` sobre (actividad, nómina, activo):
  una misma persona puede tener una inscripción activa y otra inactiva en la
  misma actividad.
- El patrón del repo (`centrodefamilia`, `VAT`, `ciudadanos`) acompaña el borrado
  lógico con `SOFT_DELETE_OPERATIONAL_UPDATES = {"activo": False}`.

## Decision
- Actividad e inscripto usan `core.soft_delete.SoftDeleteModelMixin` y quedan
  registrados en `SOFT_DELETE_MODEL_KEYS` (Papelera). Eliminar una actividad hace
  borrado lógico en cascada sobre sus inscriptos.
- **No** se define `SOFT_DELETE_OPERATIONAL_UPDATES`: eliminar no cambia `activo`.
  Pasar a inactiva una inscripción activa cuando ya existe una inactiva para la
  misma persona y actividad viola la unicidad y aborta la eliminación.
- Como `activo` no cambia, las consultas que cruzan desde la nómina hacia
  `inscripciones_actividad_pwa` (las que no pasan por el manager por defecto)
  filtran `deleted_at__isnull=True`: la pestaña "Actividades" de la nómina y el
  conteo `cantidad_actividades_pwa` de la API.
- Inactivar sigue siendo la baja operativa y no cambia.
- La baja operativa y el borrado con la actividad como raíz (web o directo)
  bloquean la actividad antes de consultar las inscripciones. La sincronización
  de nómina bloquea las actividades por
  PK antes de validar cuáles pueden recibir inscripciones. Ambas operaciones
  conservan los bloqueos hasta terminar la transacción: el borrado incluye una
  inscripción confirmada primero, o la inscripción se rechaza si el borrado
  confirmó primero. No se cambia el esquema ni el estado operativo.
- El formulario de inscripciones del admin toma los mismos bloqueos. Si la
  inscripción cambia de actividad, bloquea tanto el origen como el destino
  antes de guardar. Si alguno desapareció durante la edición, pide recargar.
- Para que el borrado en cascada desde el comedor no invierta el orden de
  bloqueos respecto a la auditoría de nómina, primero se bloquea el comedor.
  Luego se bloquean las actividades por PK y finalmente las inscripciones.
  Las mutaciones de actividad y nómina toman ese bloqueo antes de escribir.
  Solo se serializan operaciones sobre el mismo comedor.
- Si el comedor o la actividad dejan de estar disponibles durante un alta o
  edición, la API responde 400 y el formulario web muestra un error sin guardar
  parcialmente el grupo de horarios.
- El alta web de nómina PNUD, directa o por admisión, bloquea el comedor
  antes de escribir. El alta base, el perfil y las inscripciones se confirman
  juntas; si la sincronización falla, se revierte todo y se muestra el aviso.

## Consecuencias
- La restauración desde la Papelera devuelve actividad e inscriptos tal como
  estaban, incluido su estado activo/inactivo.
- Si se intenta restaurar solo una inscripción cuya actividad sigue eliminada,
  la Papelera indica que primero hay que restaurar la actividad. No cambia ni
  la actividad ni la inscripción rechazada. La restauración en cascada desde
  la actividad conserva el comportamiento anterior.
- La nómina (`comedores.Nomina`) no se modifica: el inscripto la referencia con
  `PROTECT` y la cascada no la alcanza.
- Al eliminar un comedor, sus actividades e inscriptos ahora quedan con borrado
  lógico y se restauran con él; antes la cascada los borraba físicamente.
- Costo: toda consulta nueva que cruce relaciones hacia inscriptos o actividades
  (en `filter`, `Count` o `Q`) tiene que excluir `deleted_at` a mano, porque el
  manager por defecto no aplica en los joins.
- Una actividad eliminada no bloquea cargar la correcta en el mismo horario; si
  después se la restaura, pueden quedar dos actividades superpuestas.

## Referencias
- [Cambio](../cambios/2026-T4/2026-11-14-actividades-espacio-alta-web-y-eliminacion.md)
- `src/backends/comedores/pwa/models.py`
- `src/backends/comedores/pwa/services/actividades_service.py`
