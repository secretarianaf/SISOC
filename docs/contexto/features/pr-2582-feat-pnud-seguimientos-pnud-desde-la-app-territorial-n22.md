# Contexto de feature PR #2582 - feat(pnud): seguimientos PNUD desde la app territorial (N22)

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2582
- Base: `main`
- Rama origen: `feat/pnud-seguimientos-n22`
- Autor: `Mkdir-arg`

## Contexto funcional

- No informado explícitamente; inferir desde el título del PR y el diff.

## Arquitectura tocada

- Hay cambios en capa API/DRF y conviene revisar contratos de request/response.
- Hay cambios en vistas web y puede existir impacto en permisos o renderizado.
- Se modifican templates, con posible impacto visual o de composición UI.
- Existen cambios de persistencia o migraciones que requieren revisión de datos.

## Decisiones y supuestos detectados

- Tipo de cambio declarado: No informado
- Área principal declarada: No informada
- Impacto usuario declarado: No informado
- Riesgos / rollback: No informado

## Design system y UI

- El PR toca piezas de UI y conviene revisar consistencia visual con el patrón existente.
- Archivos visuales relevantes: comedores/templates/comedor/comedor_detail.html, relevamientos/templates/acta_complementaria_detail.html, relevamientos/templates/acta_complementaria_form.html, relevamientos/templates/primer_seguimiento_detail.html, relevamientos/templates/relevamiento_confirm_delete.html, relevamientos/templates/relevamiento_detail.html, relevamientos/templates/relevamiento_list.html, relevamientos/templates/seguimiento_form.html

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2582.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `comedores/api_views_territorial.py`
- `comedores/api_views_territorial_pnud.py`
- `comedores/templates/comedor/comedor_detail.html`
- `relevamientos/admin.py`
- `relevamientos/data/pnud_formularios.json`
- `relevamientos/migrations/0018_seguimiento_pnud_n22.py`
- `relevamientos/models.py`
- `relevamientos/pnud_formularios.py`
- `relevamientos/templates/acta_complementaria_detail.html`
- `relevamientos/templates/acta_complementaria_form.html`
- `relevamientos/templates/primer_seguimiento_detail.html`
- `relevamientos/templates/relevamiento_confirm_delete.html`
- `relevamientos/templates/relevamiento_detail.html`
- `relevamientos/templates/relevamiento_list.html`
- `relevamientos/templates/seguimiento_form.html`
- `relevamientos/templates/seguimiento_pnud_detail.html`
- `relevamientos/urls/web_urls.py`
- `relevamientos/views/backoffice_views.py`
- `relevamientos/views/web_views.py`
- `tests/test_relevamientos_web_views_unit.py`
- ... y 1 archivo(s) adicional(es) relacionados.
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
