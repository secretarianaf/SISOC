# Contexto de feature PR #2611 - Celiaquia tk 2592

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2611
- Base: `development`
- Rama origen: `CeliaquiaTk_2592`
- Autor: `MariaNavarro90`

## Contexto funcional

- Celiaquía — revisión técnica de legajos por Nación (Subsanar / Rechazar) y comunicación de observaciones a Provincia.

## Arquitectura tocada

- El PR toca lógica en `services/`, por lo que impacta reglas de negocio u orquestación.
- Se modifican templates, con posible impacto visual o de composición UI.

## Decisiones y supuestos detectados

- Tipo de cambio declarado: Mejora funcional (evolutivo) + fix visual.
- Área principal declarada: celiaquia (comentarios técnicos, subsanación, detalle de expediente).
- Impacto usuario declarado: Nación ve un multiselect en los modales Subsanar y Rechazar. Provincia ve en "Observación" solo los motivos vigentes de cada instancia.
- Riesgos / rollback: Sin migración; rollback revirtiendo los commits. Las subsanaciones y rechazos creados con el cambio conservan sus datos si se revierte.

## Design system y UI

- El PR toca piezas de UI y conviene revisar consistencia visual con el patrón existente.
- Archivos visuales relevantes: celiaquia/templates/celiaquia/expediente_detail.html, static/custom/js/expediente_detail.js

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2611.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `celiaquia/services/comentarios_tecnicos_service/impl.py`
- `celiaquia/templates/celiaquia/expediente_detail.html`
- `celiaquia/tests/test_comentarios_tecnicos_flujo.py`
- `celiaquia/tests/test_comentarios_tecnicos_service.py`
- `celiaquia/tests/test_subsanacion_documentacion_complementaria.py`
- `celiaquia/views/comentarios.py`
- `celiaquia/views/expediente.py`
- `docs/registro/cambios/2026-09-30-2592-motivos-por-instancia-subsanacion-rechazo.md`
- `static/custom/js/expediente_detail.js`
- `tests/test_celiaquia_expediente_view_helpers_unit.py`
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
