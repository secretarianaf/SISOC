# Contexto de feature PR #2607 - fix(territorial): exponer sin_cargar en las actas complementarias (para app 1.1.54)

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2607
- Base: `main`
- Rama origen: `fix/acta-sin-cargar-territorial`
- Autor: `Mkdir-arg`

## Contexto funcional

- No informado explícitamente; inferir desde el título del PR y el diff.

## Arquitectura tocada

- Hay cambios en capa API/DRF y conviene revisar contratos de request/response.

## Decisiones y supuestos detectados

- Tipo de cambio declarado: No informado
- Área principal declarada: No informada
- Impacto usuario declarado: No informado
- Riesgos / rollback: No informado

## Design system y UI

- Sin cambios visibles de UI o design system detectados en el diff.

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2607.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `CHANGELOG.md`
- `comedores/api_views_territorial.py`
- `comedores/api_views_territorial_actas.py`
- `docs/contexto/features/pr-2607-fix-territorial-exponer-sin-cargar-en-las-actas-complementarias-para-app-1-1-54.md`
- `docs/registro/prs/PR-2607.md`
- `docs/registro/releases/pending/2026-09-30-pr-2607.md`
- `tests/test_acta_complementaria_validacion.py`
- `tests/test_territorial_actas_sin_cargar.py`
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
