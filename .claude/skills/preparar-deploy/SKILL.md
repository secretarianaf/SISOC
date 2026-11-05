---
name: preparar-deploy
description: "Preparar release SISOC sin mergear sus PRs finales; promover y desplegar automáticamente satélites durante el pre-deploy. Usar /preparar-deploy."
---

# Preparar deploy

Fuente: `docs/operacion/deploy_automatizado.md` (promoción descendente y promoción
`homologacion -> main` y preparación coordinada de satélites),
`docs/operacion/deploy_pwas.md` y `src/scripts/github/release_orchestrator.js`.
Si algo difiere, vale el código.

Ciclo de SISOC: primero `homologacion -> main` (PRD) y después
`development -> homologacion` (HML), donde lo nuevo queda una semana en prueba.
Los PRs finales de SISOC quedan sin mergear. **Durante el pre-deploy**, promover y
desplegar automáticamente los satélites autorizados y compatibles con el backend
ya desplegado; no esperar al futuro release de SISOC ni adelantarlo por esta skill.

## Reglas

- Nunca mergear, armar ni habilitar auto-merge en los dos PRs finales de SISOC. Nunca push
  directo, force push, rebase ni reset sobre `development`, `homologacion` o `main`.
- Los PRs de sincronización de SISOC se mergean siempre con merge commit (`--merge`), nunca
  squash ni rebase: sin ancestro común, el próximo sync vuelve a chocar.
- Un PR de saneamiento solo sincroniza ramas o arregla lo que rompe CI. Si el arreglo
  cambia comportamiento o mete código funcional nuevo en `homologacion`, parar y preguntar.
- Si algo que va a entrar a PRD parece no querido (por ejemplo, `homologacion` trae
  cambios que no pasaron por la semana en HML), parar y preguntar. Avisarlo al pasar
  no alcanza (ver `ejemplo.md`).
- Trabajar en un worktree propio creado desde `origin/<rama>`, nunca en el checkout de
  otra sesión. Scratch (bodies de PR) fuera del repo, en `mktemp -d`.
- Lo que el clasificador bloquea (aprobar runs en `action_required`, borrar ramas
  remotas, tocar rulesets) se le pasa al usuario como comando para correr con `!`.

## 1. Relevar el estado

Incluir SISOC y **todas** las entradas de `src/scripts/operacion/pwas.json`,
con su estado habilitado/deshabilitado. Aplicar la matriz y decisiones de
"Expediente coordinado" en `plantillas.md`; no limitarse a los contratos que
cambiaron en SISOC. Consultar otros repositorios solo con autorización vigente.
Una lectura desconocida no equivale a "sin cambios".

Para SISOC, `git fetch origin` y mostrar una tabla antes de tocar nada:

- `git rev-list --left-right --count origin/main...origin/homologacion`: `homologacion`
  debe contener `main` (izquierda en 0); si no, el orquestador no promueve.
- Lo mismo con `origin/homologacion...origin/development`.
- PRs abiertos con base `main` u `homologacion`, y ramas `automation/promote-*`
  (`git ls-remote origin 'refs/heads/automation/*'`).
- CI de la punta de cada rama: `gh run list --commit <sha> --json name,conclusion`.

## 2. Sanear (crear y mergear)

Usar autorización vigente para la operación, destino y cuenta/sesión. La solicitud
de ejecutar satélites durante el pre-deploy autoriza el plan acotado una vez resuelto
ese alcance; no pedir aprobación redundante por cada acción. Preguntar solo si falta
un dato de autorización. Esto no autoriza SSH, credenciales nuevas ni saltar gates.
Los comandos de esta sección describen el saneamiento de SISOC; verificar el flujo
propio de cada satélite antes del paso 4.

Un PR por problema, en este orden:

1. Promoción descendente colgada (rama `automation/promote-*` vieja o run con 409):
   cerrar su PR y pedir al usuario que borre la rama, o cubrirla con el paso 2 o 3.
2. `homologacion` atrás de `main`: rama `sync/main-a-homologacion-AAAAMMDD` desde
   `origin/homologacion`, `git merge --no-ff origin/main`, PR a `homologacion`.
3. `development` atrás de `homologacion`: rama `sync/homologacion-a-development-AAAAMMDD`
   desde `origin/development`, `git merge --no-ff origin/homologacion`, PR a `development`.
4. CI rojo en la punta de una rama: fix chico con test desde esa rama, PR a esa rama,
   y bajarlo a la otra con el sync correspondiente.

Conflictos: conservar las dos intenciones. Si una rama trae archivos en una ruta que
la otra ya movió (por ejemplo, de la raíz a `src/backends/<dueño>/`), llevarlos a la
ruta nueva y no resucitar la vieja.
Correr los chequeos de `CLAUDE.md` sobre lo tocado.

Mergear con `gh pr merge <n> --merge --auto` y seguir con `gh pr checks <n> --watch`
en primer plano. Cerrar el paso cuando `main` ⊆ `homologacion` ⊆ `development` y
`git merge-tree --write-tree origin/homologacion origin/development` no da conflictos.

## 3. Armar el contenido

Para `origin/main..origin/homologacion` y `origin/homologacion..origin/development`:

- PRs incluidos: `git log --first-parent --merges --format='%H %cs %s' <rango>` y
  `gh pr view <N> --json title,author,body,labels`. Los commits directos sin PR, aparte.
- En `homologacion -> main`, marcar lo que entró a `homologacion` hace menos de 7 días.
- Operaciones pre y post merge: recorrer "Detección de operaciones" de `plantillas.md`.
- Agrupar por módulo y explicar cada ítem en una línea, para quien no lee código.

## 4. Promover y desplegar satélites durante el pre-deploy

Aplicar "Ejecución de satélites durante el pre-deploy" de `plantillas.md` a todas
las entradas habilitadas del inventario. Verificar el backend **actualmente
desplegado**, no su rama `main`, antes de mergear cualquier frontend. Promover
`development -> main` cuando ese sea el flujo real verificado; no imponerlo a
repositorios con otra política. Omitir sin cambios verificado y deshabilitados;
lo desconocido bloquea, no se transforma en éxito.

Reutilizar o crear el PR autorizado, comprobar CI y head fijado, mergear sin bypass
y seguir su deploy en primer plano. Un fallo detiene dependientes y deja resultado
parcial; no repetir dispatch ni inventar rollback. Conservar los gates humanos.

## 5. Crear los PRs finales de SISOC (sin mergear)

Bodies y títulos en `plantillas.md`. La fecha del release es el día planeado del
deploy (preguntar si no se sabe): define el tag `AAAA.MM.DD-stable`, que no puede
existir apuntando a otro SHA.

1. `homologacion -> main` en **draft**, con los markers del orquestador,
   `release-preparation: pending` y `release-head` = SHA actual de `origin/homologacion`.
   Así el orquestador lo reconoce pero no lo arma ni le habilita auto-merge.
2. `development -> homologacion`, sin auto-merge.

Enlazar los PRs satélite ya mergeados, sus SHA y resultados de deploy del paso 4,
o sus bloqueos. No aplicarles el estado draft de los PRs finales de SISOC.
No declarar listo el conjunto con un componente pendiente o desconocido.

Si ya hay un PR abierto para el mismo par, actualizar su body en lugar de duplicarlo.
Verificar: `gh pr view <n> --json isDraft,autoMergeRequest` da draft y sin auto-merge.

## Salida

Tabla de estado antes y después, PRs de saneamiento mergeados, links a los dos PRs de
deploy, operaciones pre/post, riesgos y los pasos del día del deploy de `plantillas.md`.
Adjuntar el expediente de todos los componentes: SHA, promociones, compatibilidad,
orden, validación, recuperación y bloqueos; separar satélites desplegados durante
el pre-deploy de los PRs SISOC pendientes. No hay atomicidad entre repositorios.
Lo que no se pudo verificar se dice; no se da por pasado.
