# Plantillas de preparar-deploy

## Detección de operaciones

`<rango>` es `origin/main..origin/homologacion` o `origin/homologacion..origin/development`.
Si una señal aparece, va como operación con el comando exacto y quién la corre.

| Señal | Cómo buscarla | Operación |
|-|-|-|
| Migraciones nuevas | `git diff --name-only --diff-filter=A <rango> -- ':(glob)src/**/migrations/*.py'` | Revisar cada una. `RunPython`/`RunSQL`, `RemoveField`, `DeleteModel`, `AlterField` en tablas grandes o reversa `noop`: **pre** backup verificado de la base y duración estimada; **post** `python manage.py showmigrations` sin pendientes |
| Migraciones ya publicadas que cambian o se borran | `git diff --name-only --diff-filter=MD <rango> -- ':(glob)src/**/migrations/*.py'` | Parar y preguntar: rompe bases ya migradas |
| Variables de entorno nuevas | diff de `.env*example*` y de `os.getenv`/`os.environ` en `settings` | **Pre**: cargarlas en el `.env` de PRD (y HML) |
| Comandos de gestión | nuevos en `management/commands/`, o un PR o registro que pide correr uno | **Pre** o **post** con el comando exacto |
| Dependencias o imagen | `requirements*.txt`, `Dockerfile*`, `docker-compose*.yml`, `package*.json` | El deploy reconstruye la imagen; anotar el riesgo |
| Infra fuera del contenedor | `nginx`, cron, workers, `deploy_verified.sh` | Operación manual de infra |
| CI o automatización | `.github/workflows/`, `src/scripts/github/` | Los `schedule`/`workflow_run` leen de `development` y el orquestador de `homologacion`: el cambio tiene que estar en las dos |
| Registros | `docs/registro/` agregados en el rango con "Consideraciones operativas", deploy o rollback | Copiar la operación |
| Bodies de PR | buscar `deploy`, `manage.py`, `correr`, `ejecutar`, `backup`, `antes de`, `después de` | Copiar la operación |
| Satélites y PWAs | cambios de API o contrato que consume otro repo | Deploy coordinado en ese repo |

Si no aparece nada: "Sin operaciones pre/post. Revisado: migraciones, variables de
entorno, comandos, dependencias, infra, CI, registros y bodies de PR."

## PR `homologacion -> main`

```bash
gh pr create --draft --base main --head homologacion \
  --title "chore(release): promover homologacion a main AAAA-MM-DD" --body-file <scratch>/main.md
```

Los cuatro markers van primero y exactos: el orquestador los lee con regex.

```markdown
<!-- release-automation: scheduled -->
<!-- release-date: AAAA-MM-DD -->
<!-- release-head: <SHA de 40 caracteres de origin/homologacion> -->
<!-- release-preparation: pending -->

> **No mergear a mano.** El día del deploy se arma con
> `gh workflow run release-orchestrator.yml -f release_pr=<este PR>`.

## Resumen

Release AAAA-MM-DD. Snapshot `<sha homologacion>` sobre `main` `<sha main>`: N PRs.

## Qué entra a producción

### <Módulo>
- #N <título>: <qué cambia para quien usa el sistema> (en HML desde AAAA-MM-DD).

## En HML hace menos de 7 días
- #N ... o "Ninguno".

## Operaciones

**Antes del merge**
- [ ] ...

**Después del deploy**
- [ ] ...

## Riesgos y rollback
- Tag de rollback `AAAA.MM.DD-stable` sobre el `main` actual `<sha>`; lo crea el orquestador.
- Migraciones irreversibles o de datos: ...

## Saneamiento previo
- #N chore(sync): ...
```

## PR `development -> homologacion`

```bash
gh pr create --base homologacion --head development \
  --title "chore(release): promover development a homologacion AAAA-MM-DD" --body-file <scratch>/hml.md
```

```markdown
> **No mergear antes de que salga el release a PRD**: mover `homologacion` cambia
> el snapshot del PR final #<n> y lo bloquea.

## Resumen
Lo que entra a HML para probar durante la semana: N PRs.

## Qué entra a homologación
### <Módulo>
- #N <título>: <qué cambia> (qué probar en HML).

## Operaciones
**Antes del merge** / **Después del deploy en HML**
- [ ] ...
```

## Pasos del día del deploy

1. No mergear nada a `homologacion` hasta que salga el release. Si cambió, volver a
   correr la skill para actualizar `release-head`.
2. Correr las operaciones **antes del merge** del PR final.
3. `gh workflow run release-orchestrator.yml -f release_pr=<n>`: el PR pasa a ready,
   se crea el tag `AAAA.MM.DD-stable` y se habilita el auto-merge.
4. Aprobar el job `production` del Environment y esperar el deploy y la promoción
   descendente `main -> homologacion -> development`.
5. Operaciones **después del deploy** de PRD.
6. Mergear `development -> homologacion` (si quedó atrás, actualizarlo) y correr sus
   operaciones en HML.
