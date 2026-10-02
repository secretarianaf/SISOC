# Contexto de feature PR #2637 - feat(deploy): un cambio solo en backends/sisoc_core recrea solo el core

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2637
- Base: `development`
- Rama origen: `feat/2309-deploy-selectivo-core`
- Autor: `juanikitro`

## Contexto funcional

- No informado explícitamente; inferir desde el título del PR y el diff.

## Arquitectura tocada

- No se detectó un patrón arquitectónico dominante más allá del diff observado.

## Decisiones y supuestos detectados

- Tipo de cambio declarado: No informado
- Área principal declarada: No informada
- Impacto usuario declarado: No informado
- Riesgos / rollback: No informado

## Design system y UI

- Sin cambios visibles de UI o design system detectados en el diff.

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2637.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `docs/operacion/backends_por_servicio.md`
- `docs/registro/cambios/2026-10-02-deploy-selectivo-core.md`
- `docs/registro/decisiones/2026-09-30-monorepo-kernel-backends.md`
- `scripts/operacion/deploy_refresh.sh`
- `scripts/operacion/deploy_targets.py`
- `tests/test_deploy_refresh_script.py`
- `tests/test_deploy_targets.py`
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
