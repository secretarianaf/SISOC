# Contexto de feature PR #2597 - feat(encuestas): aprobación y segmentación por usuarios y grupos (#2563)

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2597
- Base: `development`
- Rama origen: `Fixex-28-09`
- Autor: `PabloCao1`

## Contexto funcional

- puntos 5 y 6 del issue #2563, aprobación de publicación y segmentación de encuestas.

## Arquitectura tocada

- Hay cambios en vistas web y puede existir impacto en permisos o renderizado.
- Se modifican templates, con posible impacto visual o de composición UI.
- Existen cambios de persistencia o migraciones que requieren revisión de datos.

## Decisiones y supuestos detectados

- Tipo de cambio declarado: feature
- Área principal declarada: encuestas
- Impacto usuario declarado: el gestor solicita publicación; el administrador resuelve; se facilita la selección y corrección de destinatarios.
- Riesgos / rollback: aplicar migraciones y sincronizar grupos; grupos dinámicos e IDs propios de cada ambiente. Antes de revertir esquema, respaldar motivos de rechazo y segmentaciones nuevas.

## Design system y UI

- El PR toca piezas de UI y conviene revisar consistencia visual con el patrón existente.
- Archivos visuales relevantes: encuestas/templates/encuestas/encuesta_form.html, encuestas/templates/encuestas/encuesta_list.html, encuestas/templates/encuestas/encuesta_revision.html, encuestas/templates/encuestas/encuesta_segmentacion.html, encuestas/templates/encuestas/partials/estado.html, encuestas/templates/encuestas/partials/motivo_rechazo.html, static/custom/css/encuestaForm.css, static/custom/css/encuestaGestion.css

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2597.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `AGENT_REPO_MAP.md`
- `docs/implementaciones/encuestas.md`
- `docs/registro/cambios/2026-09-28-encuestas-aprobacion-2563.md`
- `docs/registro/cambios/2026-09-28-encuestas-segmentacion-2563.md`
- `docs/registro/cambios/2026-09-28-encuestas-segmentacion-apariencia.md`
- `docs/registro/cambios/2026-09-28-encuestas-segmentacion-grupos.md`
- `encuestas/admin.py`
- `encuestas/filters.py`
- `encuestas/forms.py`
- `encuestas/migrations/0004_encuesta_aprobacion.py`
- `encuestas/migrations/0005_motivo_rechazo.py`
- `encuestas/migrations/0006_segmentacion_usuarios.py`
- `encuestas/migrations/0007_segmentacion_grupos.py`
- `encuestas/models.py`
- `encuestas/services.py`
- `encuestas/templates/encuestas/encuesta_form.html`
- `encuestas/templates/encuestas/encuesta_list.html`
- `encuestas/templates/encuestas/encuesta_revision.html`
- `encuestas/templates/encuestas/encuesta_segmentacion.html`
- `encuestas/templates/encuestas/partials/estado.html`
- ... y 23 archivo(s) adicional(es) relacionados.
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
