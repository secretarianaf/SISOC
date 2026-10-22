# Release notes preliminares

Este directorio agrupa artefactos generados automáticamente para el flujo de release.

## Estructura

- `pending/`: notas preliminares por PR hacia `main`

## Relación con `CHANGELOG.md`

Los archivos de `pending/` son la fuente inmediata para reconstruir el bloque superior de `CHANGELOG.md` durante PRs a `main`.

## Limitación vigente desde 2026-10-15

`src/scripts/ci/pr_doc_automation.py` y `.github/workflows/pr-docs.yml` generan
y exigen la nota de `pending/` y el `CHANGELOG.md` sólo cuando la base del PR
es `main`. Desde el PR #2719 a `main` sólo llega el PR semanal
`homologacion -> main` (ver
`docs/registro/cambios/2026-T4/2026-10-15-release-desde-homologacion.md`): los
PRs de feature van a `development` y ya no generan nota propia, así que el
bloque de cada release resume un único PR. El detalle por PR sigue en
`docs/registro/prs/`. Pendiente de decisión: generar la nota también para PRs a
`development` o armar el bloque del release desde los `prs/` que incluye.

## Limpieza

No hay limpieza automática: el script sólo reemplaza la nota anterior del mismo
PR, por lo que `pending/` acumula notas de releases ya publicadas.
