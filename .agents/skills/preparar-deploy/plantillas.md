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
| Satélites y PWAs | inventario completo de `src/scripts/operacion/pwas.json`, diferencias de cada repo y contratos compartidos | Expediente coordinado obligatorio, incluso sin cambios del backend |

Si no aparece nada: "Sin operaciones pre/post. Revisado: migraciones, variables de
entorno, comandos, dependencias, infra, CI, registros y bodies de PR."

## Expediente coordinado

Aplicar la guía de preparación coordinada en `docs/operacion/deploy_automatizado.md`.
Leer el inventario versionado en `src/scripts/operacion/pwas.json` en cada ejecución;
no congelar una lista de repositorios en la skill. Incluir entradas deshabilitadas
con su motivo, sin activarlas. Para cada repositorio autorizado, leer su workflow
vigente: no asumir las mismas ramas, aprobaciones o inputs que SISOC.

Usar esta tabla tanto para PRD como para el tramo HML posterior, con enlaces a la
evidencia y hora de consulta. Duplicar filas por entorno cuando corresponda.

| Componente / repo / habilitado | Entorno / ramas origen → destino | SHA origen / destino | PRs y cambios pendientes | CI del SHA | Deploy registrado: SHA / run / resultado | Prueba en vivo / cliente | Decisión / bloqueo |
|-|-|-|-|-|-|-|-|
| SISOC | ... | ... | ... | ... | ... | ... | ... |
| Cada entrada del inventario | ... | ... | ... | ... | ... | ... | ... |

Decisiones permitidas:

- **Promoción pendiente**: describir todo el rango, no solo el PR que motivó la
  release; ejecutar el flujo satélite siguiente si está autorizado y es compatible.
- **Desplegado verificado**: enlazar PR mergeado, SHA efectivo, run terminal y
  comprobaciones realizadas; no confundirlo con los PRs SISOC pendientes.
- **Sin cambios verificado**: documentar comparación y revisión destino; si falta
  evidencia del despliegue, anotar ese bloqueo por separado. No abrir PR vacío ni
  forzar un redeploy sin necesidad justificada.
- **Desconocido / bloqueado**: falta autorización, acceso, CI, contrato o evidencia;
  no omitir el componente ni declarar listo el conjunto.
- **Deshabilitado**: conservar la decisión del inventario y su motivo; no activarlo.

Registrar además:

1. **Dependencias y compatibilidad**: contrato/API, versión del instrumento y
   combinación backend/frontend; citar código, tests o PRs. Para ejecutar ahora,
   corroborar el backend actualmente desplegado y su compatibilidad con el frontend
   candidato, incluida la fase transitoria. Un PR en `main` no demuestra deploy.
   Si necesita un backend futuro o es desconocida, bloquear ese componente antes
   del merge y pedir la decisión/release necesaria, sin adelantar SISOC.
2. **Plan fijado**: SHA completos, entorno, orden y condición para avanzar por
   componente. Si una punta cambia, revalidar el rango y actualizar el expediente
   antes de autorizar acciones; no cambiar silenciosamente el snapshot.
3. **Ejecución satélite durante el pre-deploy**: PR, comando exacto de merge y
   mecanismo de deploy del workflow vigente, autorización y gates; registrar luego
   el resultado real. La ejecución del release SISOC sigue propuesta, no ejecutada.
   Nunca inventar un comando común a todos ni omitir una autorización faltante.
4. **Verificación posterior**: run y SHA efectivamente desplegado, salud y prueba
   funcional acotada por componente/entorno, con límites explícitos. CI verde,
   deploy exitoso y HTTP 200 son evidencias distintas de la prueba funcional.
5. **Fallo parcial y recuperación**: qué ya cambió, qué sigue anterior, dependientes
   que deben detenerse, artefacto previo compatible y responsable autorizado para
   recuperar. No continuar como éxito ni revertir migraciones/datos automáticamente.
6. **Cliente PWA**: separar bundle servido, versión instalada y service worker/caché.
   No borrar almacenamiento, registros offline ni cachés para ocultar diferencias.

Incluir una sección "Expediente coordinado de SISOC y satélites" en cada body de PR
siguiente: matriz, dependencias, orden, promociones/dispatches propuestos y ejecutados,
aprobaciones, recuperación y bloqueos. Enlazar los PRs de los otros componentes
cuando existan. La preparación deja los PRs finales SISOC sin mergear y registra
los merges/despliegues satélite ejecutados durante ella. Reutilizar autorización
válida para cada destino/operación/cuenta o sesión; pedir solo el alcance faltante.

## Ejecución de satélites durante el pre-deploy

No ejecutar estos pasos al editar la skill: corresponden a una invocación que
solicita promover y desplegar satélites, con destinos, operaciones y sesión/cuenta
resueltos. Mantener los gates del repositorio, CI y Environment: nunca `--admin`,
bypass, aprobación automática de un gate humano, nueva credencial ni SSH implícito.

1. Para cada satélite habilitado, verificar política de ramas, checks, estrategia
   de merge y disparador/inputs del workflow actual. Identificar también sus
   promociones/deploys descendentes automáticos e incluir esos destinos y efectos
   en el alcance autorizado antes del merge o dispatch. Usar `development -> main`
   cuando coincida con ese flujo; no inventar ramas ni saltar la validación HML que
   ese repositorio requiera. Fijar head/base SHA, entorno y versión del backend
   desplegado, compatibilidad y rango completo. Sin autorización o compatibilidad
   comprobada, bloquear antes de crear/mergear el PR.
2. Reutilizar o crear el PR autorizado. Seguir CI en primer plano con
   `gh pr checks <n> --repo <repo> --watch --fail-fast`. Volver a leer head/base antes
   del merge: un cambio requiere revalidación, no promoción silenciosa de novedades.
   Si admite merge commit, `gh pr merge <n> --repo <repo> --merge --match-head-commit <head-sha>` fija el head; esa opción no fija atómicamente la
   base. Respetar la estrategia o cola requerida si difiere, sin bypass. Confirmar
   estado mergeado y SHA de merge efectivo; un PR en cola no es un merge terminado.
3. Localizar el run del workflow y entorno exactos para el SHA mergeado. Si el merge
   ya dispara deploy, seguirlo: **no despachar otro**. Si producción exige dispatch,
   usar una sola vez el comando e inputs verificados en ese repo, comprobar que la
   referencia sigue en el SHA esperado y capturar su run. Si no puede identificarse
   el resultado o la referencia avanza, parar sin retry ciego ni dispatch duplicado.
4. Esperar en primer plano con `gh run watch <run-id> --repo <repo> --exit-status`.
   Ante un gate humano, informar qué aprobación falta y conservar el run pendiente;
   no declararlo completo ni saltarlo. Registrar conclusión terminal del job de
   deploy aplicable, entorno y SHA efectivamente desplegado: un run exitoso con ese
   job omitido no sirve. Contrastar con el objetivo fijado; salud/HTTP 200 o merge
   exitoso no reemplazan prueba funcional. Realizar el smoke autorizado y declarar
   límites de prueba en vivo/cliente.
5. Fallo, cancelación, timeout, SHA distinto o evidencia incompleta: detener acciones
   dependientes, informar qué ya cambió y marcar parcial/bloqueado. No iniciar
   recuperación remota fuera de su autorización ni revertir datos/storage. Completar
   solo con prueba por componente; `sin cambios verificado` y deshabilitado se
   omiten con evidencia/motivo, no originan PR vacío ni redeploy automático.

Los comandos de consulta/merge/watch anteriores son formas de CLI, no sustituyen
los dispatches específicos ni las protecciones del workflow vigente. La ejecución
es coordinada y secuencial según dependencias, no una transacción atómica.

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

1. Revisar el expediente: los satélites ya se ejecutaron durante el pre-deploy
   contra el backend compatible entonces desplegado. Revalidar su estado y los
   bloqueos; no redesplegarlos automáticamente ni despacharlos por el éxito SISOC.
   Si cambió un SHA o la compatibilidad, actualizar el plan antes de ejecutar.
   No mergear nada a `homologacion` hasta que salga el release. Si cambió, volver a
   correr la skill para actualizar `release-head`.
2. Correr las operaciones **antes del merge** del PR final.
3. `gh workflow run release-orchestrator.yml -f release_pr=<n>`: el PR pasa a ready,
   se crea el tag `AAAA.MM.DD-stable` y se habilita el auto-merge.
4. Aprobar el job `production` del Environment y esperar el deploy y la promoción
   descendente `main -> homologacion -> development`.
5. Operaciones **después del deploy** de PRD. Verificar el resultado conjunto del
   expediente, con evidencia por componente y las aprobaciones propias. Un fallo
   o componente pendiente deja la release parcial/bloqueada, no completa; detener
   el tramo HML dependiente. Los pasos 3 y 4 no despliegan por sí mismos todos los
   satélites ni autorizan acciones pendientes. Un pendiente satélite bloqueado
   por backend futuro requiere el plan/decisión explícita correspondiente; no se
   convierte por defecto en un deploy pospuesto o automático después de SISOC.
6. Mergear `development -> homologacion` (si quedó atrás, actualizarlo) y correr sus
   operaciones en HML.
