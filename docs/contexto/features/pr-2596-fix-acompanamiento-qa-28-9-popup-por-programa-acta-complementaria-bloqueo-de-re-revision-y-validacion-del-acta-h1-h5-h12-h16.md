# Contexto de feature PR #2596 - fix(acompañamiento): QA 28/9 — popup por programa, acta complementaria, bloqueo de re-revisión y validación del acta (H1, H5, H12, H16)

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2596
- Base: `main`
- Rama origen: `fix/qa-2026-09-28-sisoc`
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
- Archivos visuales relevantes: relevamientos/templates/acta_complementaria_detail.html, relevamientos/templates/primer_seguimiento_detail.html, relevamientos/templates/relevamiento_detail.html, relevamientos/templates/relevamiento_list.html, relevamientos/templates/seguimiento_pnud_detail.html

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2596.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `CHANGELOG.md`
- `comedores/api_views_territorial.py`
- `comedores/api_views_territorial_actas.py`
- `comedores/tests.py`
- `comedores/views/relevamientos.py`
- `docs/contexto/features/pr-2596-fix-acompanamiento-qa-28-9-popup-por-programa-acta-complementaria-bloqueo-de-re-revision-y-validacion-del-acta-h1-h5-h12-h16.md`
- `docs/registro/prs/PR-2596.md`
- `docs/registro/releases/pending/2026-09-30-pr-2596.md`
- `relevamientos/alta_backoffice.py`
- `relevamientos/migrations/0020_acta_complementaria_validacion.py`
- `relevamientos/models.py`
- `relevamientos/templates/acta_complementaria_detail.html`
- `relevamientos/templates/primer_seguimiento_detail.html`
- `relevamientos/templates/relevamiento_detail.html`
- `relevamientos/templates/relevamiento_list.html`
- `relevamientos/templates/seguimiento_pnud_detail.html`
- `relevamientos/urls/web_urls.py`
- `relevamientos/views/backoffice_views.py`
- `relevamientos/views/seguimiento_helpers.py`
- `relevamientos/views/web_views.py`
- ... y 5 archivo(s) adicional(es) relacionados.
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
