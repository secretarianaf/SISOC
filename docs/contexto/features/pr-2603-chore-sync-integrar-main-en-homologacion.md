# Contexto de feature PR #2603 - chore(sync): integrar main en homologacion

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2603
- Base: `homologacion`
- Rama origen: `automation/promote-main-to-homologacion`
- Autor: `secretarianaf-sisoc-release[bot]`

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
- Archivos visuales relevantes: relevamientos/templates/acta_complementaria_detail.html, relevamientos/templates/primer_seguimiento_detail.html, relevamientos/templates/relevamiento_detail.html, relevamientos/templates/relevamiento_list.html, relevamientos/templates/seguimiento_pnud_detail.html, static/custom/js/user_mobile_access.js, tests/js/user_mobile_access.test.js, users/templates/user/user_form.html

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2603.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `AGENT_REPO_MAP.md`
- `CHANGELOG.md`
- `comedores/api_views_territorial.py`
- `comedores/api_views_territorial_actas.py`
- `comedores/tests.py`
- `comedores/views/relevamientos.py`
- `core/constants.py`
- `docs/contexto/features/pr-2596-fix-acompanamiento-qa-28-9-popup-por-programa-acta-complementaria-bloqueo-de-re-revision-y-validacion-del-acta-h1-h5-h12-h16.md`
- `docs/contexto/features/pr-2598-feat-pnud-textos-literales-del-documento-en-los-formularios-de-seguimiento-pnud.md`
- `docs/contexto/features/pr-2599-fix-qa-28-9-ajustes-de-la-revision-de-2596-performance-del-listado-duplicados-backfill-de-actas.md`
- `docs/contexto/features/pr-2600-pnud-estructura-literal-del-documento-en-el-detalle-del-backoffice-si-no-ranking-y-casillas-aplanados-sin-migracion.md`
- `docs/contexto/features/pr-2601-feat-usuarios-secciones-del-abm-habilitadas-por-permiso.md`
- `docs/contexto/features/pr-2602-fix-pnud-json-de-etiquetas-pnud-de-la-ronda-2-de-la-estructura-literal-complemento-de-2600.md`
- `docs/registro/decisiones/2026-09-29-usuarios-secciones-por-permiso.md`
- `docs/registro/prs/PR-2596.md`
- `docs/registro/prs/PR-2598.md`
- `docs/registro/prs/PR-2599.md`
- `docs/registro/prs/PR-2600.md`
- `docs/registro/prs/PR-2601.md`
- `docs/registro/prs/PR-2602.md`
- ... y 38 archivo(s) adicional(es) relacionados.
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
