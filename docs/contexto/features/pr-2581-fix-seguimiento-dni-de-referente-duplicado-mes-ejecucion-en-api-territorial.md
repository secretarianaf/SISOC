# Contexto de feature PR #2581 - fix(seguimiento): DNI de referente duplicado + mes_ejecucion en API territorial

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2581
- Base: `main`
- Rama origen: `fix/referente-dni-duplicado`
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

- Empezar por `docs/registro/prs/PR-2581.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `CHANGELOG.md`
- `comedores/api_views_territorial.py`
- `docs/contexto/features/pr-2581-fix-seguimiento-dni-de-referente-duplicado-mes-ejecucion-en-api-territorial.md`
- `docs/registro/prs/PR-2581.md`
- `docs/registro/releases/pending/2026-09-30-pr-2581.md`
- `relevamientos/serializer.py`
- `tests/test_primer_seguimiento_relevamientos.py`
- `tests/test_territorial_api.py`
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
