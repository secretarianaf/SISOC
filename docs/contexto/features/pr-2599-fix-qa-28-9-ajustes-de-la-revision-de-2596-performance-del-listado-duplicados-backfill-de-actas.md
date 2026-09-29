# Contexto de feature PR #2599 - fix(qa-28/9): ajustes de la revisión de #2596 (performance del listado, duplicados, backfill de actas)

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2599
- Base: `main`
- Rama origen: `fix/qa-2026-09-28-sisoc-ajustes`
- Autor: `Mkdir-arg`

## Contexto funcional

- No informado explícitamente; inferir desde el título del PR y el diff.

## Arquitectura tocada

- Hay cambios en capa API/DRF y conviene revisar contratos de request/response.
- Existen cambios de persistencia o migraciones que requieren revisión de datos.

## Decisiones y supuestos detectados

- Tipo de cambio declarado: No informado
- Área principal declarada: No informada
- Impacto usuario declarado: No informado
- Riesgos / rollback: No informado

## Design system y UI

- Sin cambios visibles de UI o design system detectados en el diff.

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2599.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `CHANGELOG.md`
- `comedores/api_views_territorial.py`
- `docs/contexto/features/pr-2599-fix-qa-28-9-ajustes-de-la-revision-de-2596-performance-del-listado-duplicados-backfill-de-actas.md`
- `docs/registro/prs/PR-2599.md`
- `docs/registro/releases/pending/2026-09-30-pr-2599.md`
- `relevamientos/alta_backoffice.py`
- `relevamientos/migrations/0021_actas_app_pendiente_validacion.py`
- `relevamientos/models.py`
- `tests/test_qa_0928_ajustes_revision.py`
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
