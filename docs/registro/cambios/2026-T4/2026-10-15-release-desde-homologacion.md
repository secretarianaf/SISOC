# Promoción semanal a `main` desde `homologacion`

## Problema

El pre-deploy semanal pasó a promover `homologacion -> main`, pero
`release-orchestrator.yml` y `release_orchestrator.js` seguían aceptando solo
el PR final `development -> main` y el PR temporal hacia `development`. El
pre-deploy del 2026-10-15 terminó en `SETUP_BLOCKED` por eso.

## Cambio

- `release_orchestrator.js`: una constante `RELEASE_SOURCE_BRANCH =
  "homologacion"` reemplaza los literales `development`. El PR final debe ser
  `homologacion -> main`, el temporal debe apuntar a `homologacion` y la
  comparación previa al tag verifica que `homologacion` contenga el `main`
  actual.
- `release-orchestrator.yml`: el disparo `pull_request: closed` y el checkout
  del script apuntan a `homologacion`.
- Test de regresión: un PR final `development -> main` o un temporal hacia
  `development` ya no se reconocen.
- Se mantiene el prefijo `codex/predeploy-dev-main-AAAAMMDD` de la rama
  temporal para no cambiar el contrato de la tarea programada.

## Rulesets (configuración, fuera del repo)

- `Proteccion` (`development`, `homologacion`, `main`): vuelve a exigir
  `deploy_guard` junto a `architecture_imports`, `gitleaks` y
  `sync_pr_artifacts`; sin rama al día; cero aprobaciones.
- `Promocion automatica a main`: activa, exige además `release_baseline` de la
  GitHub App `secretarianaf SISOC Release` y rama al día.

## Trade-off

Con `release_baseline` obligatorio, ningún PR directo de una rama de feature
puede integrarse en `main` (en el último mes fueron 29 de 33). Todo cambio
llega a producción por `development -> homologacion -> main`. Rollback:
desactivar la ruleset `Promocion automatica a main` y revertir este PR.

## Transición

`schedule` y `workflow_run` leen el YAML de `development` y el script de
`homologacion`. Hasta que este cambio llegue a `homologacion`, el orquestador
corre el script viejo, que no encuentra PRs `development -> main` y no hace
nada.
