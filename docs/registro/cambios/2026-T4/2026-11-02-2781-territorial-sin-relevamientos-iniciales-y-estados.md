# Cambio: territoriales sin relevamientos iniciales y estados unificados (#2781)

**Requiere revisión técnica**: toca permisos de la API territorial.

## Alcance

Puntos 2 y 3 del issue #2781 (el lado de SISOC; el botón de la app va en otro PR).

1. Los territoriales ya no pueden crear relevamientos iniciales.
   `POST /api/territorial/comedores/{id}/relevamientos/` responde 403 con
   "Los relevamientos iniciales se asignan desde SISOC; no se pueden crear
   desde la app." (`crear_relevamiento` en
   `src/backends/comedores/comedores/api_views_territorial.py`).
2. SISOC web y la app comparten cuatro estados: Pendiente, En curso, Pendiente
   Revisión y Finalizado.

## Comportamiento

- Alta de relevamiento: 403 siempre, salvo un reintento cuyo `client_uuid` ya
  pertenece a un relevamiento de ese mismo comedor: devuelve ese registro (200).
  Es una decisión del agente para que la cola offline de apps viejas se vacíe
  sin quedar trabada; no crea nada. Fuera de zona sigue siendo 404.
- No cambian: listado, completar/sincronizar relevamientos asignados desde
  SISOC, seguimientos (posterior, virtual, acta de excepción), PNUD, actas ni el
  alta desde el backoffice web.
- Estado unificado, calculado sin tocar datos guardados ni migrar
  (`RelevamientoService.estado_unificado` en
  `src/backends/comedores/relevamientos/service.py`). Manda `estado_validacion`:
  `Validado` = Finalizado; `Pendiente validación coordinador` = Pendiente
  Revisión; `A subsanar` = En curso. Sin validación:
  - Relevamiento: vacío, `Pendiente`, `Visita pendiente` = Pendiente;
    `Finalizado` y `Finalizado/Excepciones` = Finalizado; `Pendiente de
    validación`/`revisión` (históricos) = Pendiente Revisión; cualquier otro
    valor no vacío = En curso.
  - Seguimiento (todos los tipos): vacío o `Asignado` = Pendiente; `En Proceso`
    = En curso; `Completo` = Finalizado.
  - Seguimiento PNUD y acta complementaria (sin `estado`): sin contenido =
    Pendiente; con contenido y origen app = Pendiente Revisión (criterio de la
    migración 0021); con contenido y origen SISOC = En curso.
- Web: badges en el listado del comedor, detalle de relevamiento (y su ciclo de
  seguimiento), seguimiento, PNUD y acta, con el filtro de template
  `estado_unificado` (`relevamientos/templatetags/estado_unificado.py`). El
  estado de validación del coordinador queda en el tooltip del badge y los
  controles de revisión no cambian. No había filtro por estado en esas listas.
- API territorial: clave nueva y aditiva `estado_unificado` en
  `relevamientos.ultimo/items`, `seguimientos.items`, actas, PNUD y las
  respuestas de alta. Las claves existentes no cambian.

## Verificación

Ver la descripción del PR para los comandos y conteos de la corrida local. La
guía canónica `docs/flujos/relevamiento_sync.md` se actualizó. No hay
migraciones ni cambios de datos guardados.
