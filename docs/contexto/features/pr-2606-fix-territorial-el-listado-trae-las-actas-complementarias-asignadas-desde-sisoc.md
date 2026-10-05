# Contexto de feature PR #2606 - fix(territorial): el listado trae las actas complementarias asignadas desde SISOC

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2606
- Base: `main`
- Rama origen: `fix/actas-asignadas-listado-territorial`
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

- Empezar por `docs/registro/prs/PR-2606.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `comedores/api_views_territorial.py`
- `comedores/api_views_territorial_actas.py`
- `tests/test_popup_acta_complementaria.py`
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
