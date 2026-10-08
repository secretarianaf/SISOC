# Artefactos de PR pusheados con la GitHub App

## Problema

`pr-docs.yml` commitea los artefactos del PR (`docs(ci): actualizar artefactos
automaticos del PR #N`) con el `GITHUB_TOKEN`. Los workflows que dispara ese
commit quedan en `action_required` hasta que alguien los aprueba. Como el
commit pasa a ser el head y el ruleset de `development` exige checks sobre el
head, el PR queda `BLOCKED` aunque todo haya pasado en el commit anterior
(pasó en #2546, #2655 y #2666).

## Cambio

- El job `generate_pr_artifacts` genera un token de la GitHub App de release
  (`RELEASE_AUTOMATION_APP_CLIENT_ID` / `RELEASE_AUTOMATION_APP_PRIVATE_KEY`,
  la misma que usan `deploy.yml` y `release-orchestrator.yml`) y hace checkout
  y push con él. El commit queda a nombre de
  `secretarianaf-sisoc-release[bot]`.
- El job no corre cuando el push lo hizo esa App, igual que con
  `github-actions[bot]`: si no, cada commit de artefactos dispararía otro.

Evidencia: el commit de esa App en #2624 (`dc9dffeb0`) disparó sus workflows
sin aprobación manual.

## Trade-off

La App tiene más permisos que el `GITHUB_TOKEN` del job. El token es temporal
y solo se usa en PRs de ramas del mismo repositorio (la condición del job ya
excluye forks).

## Validación pendiente

Comprobar en el primer PR después del merge que los workflows del commit de
artefactos corren solos y que `pr-docs` no se vuelve a disparar en cadena.
