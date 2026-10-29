# Cambio: acceso de SISOC a los runners de organizacion

## Alcance

Investigar y restablecer la asignacion de jobs de SISOC a los runners de
organizacion de QA, Homologacion y Produccion; seguir el deploy pendiente de QA
y actualizar los inventarios y el procedimiento de migracion de runners.
No se autorizaron despliegues ni promociones de HML o Produccion.

## Causa y evidencia

El 2026-10-27, `gh api repos/secretarianaf/SISOC/actions/runners` devolvio
`total_count: 0`. Por SSH, sin sudo, los tres servicios anteriores de repositorio
`actions.runner.dsocial118-SISOC.sisoc-<entorno>` estaban `inactive (dead)`.
Los tres servicios de organizacion estaban activos, con `Runner.Listener`
vivo, y GitHub los mostraba online con los labels correctos.

La hipotesis inicial de falta de seleccion de SISOC no coincidio con la API:
el grupo `Default` (ID 1) ya tenia `visibility: selected` e incluia SISOC.
El bloqueo comprobado era otro: SISOC era publico y el grupo tenia
`allows_public_repositories: false`. Los cuatro repos satelite seleccionados
eran privados, lo que explica que pudieran usar los mismos runners.
Las politicas de Actions de SISOC y de la organizacion permitian todos los
actions; el grupo no restringia workflows (`restricted_to_workflows: false`,
`selected_workflows: []`).

## Estado de GitHub y atribucion del cambio

Se solicito y obtuvo autorizacion para cambiar exclusivamente
`allows_public_repositories` a `true`. Sin embargo, en la lectura previa al
PATCH el valor **ya era true**: el agente no ejecuto el PATCH ni modifico la
seleccion de repositorios. No se verifico el actor ni la hora exacta del cambio.

| Propiedad | Primera lectura | Lectura posterior a la autorizacion |
| --- | --- | --- |
| Grupo | `Default`, ID 1 | sin cambio |
| `visibility` | `selected` | `selected` |
| `allows_public_repositories` | `false` | `true` |
| `restricted_to_workflows` | `false` | `false` |
| Repositorios | DataCalle, Espacios-Comunitarios, Gestionar, Inspecciones, SISOC | los mismos cinco |

La habilitacion permite a SISOC usar runners compartidos por los tres entornos.
No se debe ejecutar codigo de PR/forks en estos runners. No se agregaron
restricciones por workflow, se cambiaron labels ni se reinstalaron,
reiniciaron o desregistraron servicios.

## Comportamiento y documentacion

Los inventarios `docs/infra/QA_INVENTORY.md`,
`docs/infra/HML_INVENTORY.md` y `docs/infra/PROD_INVENTORY.md` distinguen el
runner de organizacion vigente del servicio de repositorio detenido.
`docs/infra/HML_OPERATIONS.md` consulta el servicio vigente.
`docs/operacion/deploy_automatizado.md` exige comprobar el acceso de SISOC,
el permiso para repos publicos cuando corresponda y un deploy de SISOC tomado
por el runner organizacional antes de retirar el anterior.
No basta con que este online o acepte jobs satelite.

## Verificacion

- Cuenta activa `juanikitro`, scope `admin:org` confirmado tras autorizacion
  interactiva del usuario. No se copiaron tokens ni archivos de credenciales.
- Run original [40529406949](https://github.com/secretarianaf/SISOC/actions/runs/40529406949):
  `deploy-qa` tomo `sisoc-qa-org` a las 15:56:12 UTC y termino `failure` a las
  15:56:20 UTC (8 segundos). Su SHA `6cf6527b989f68cb4982ec35229a3950913faa69`
  ya no era el head de `development`; el log muestra el fetch de
  `ffba74b9c` y salida 1 antes del merge/deploy, coherente con la guarda de
  revision obsoleta del workflow. No se relanzo esa revision.
- Run posterior [40535874390](https://github.com/secretarianaf/SISOC/actions/runs/40535874390):
  generado por push a `development`, SHA
  `ffba74b9c09f3b10ce5ac4191d46a0765d6b36bf`; tomo `sisoc-qa-org` a las
  15:56:24 UTC y termino `success` a las 16:04:21 UTC: **7 min 57 s de job**.
  Tras un corte de conectividad del cliente Windows (SSH timeout, error API,
  curl `000`), el usuario restablecio la red y se consulto el resultado final.
  SSH `git rev-parse HEAD` en el checkout QA devolvio el mismo SHA del run;
  el log registra `QA health check: OK` a las 16:03:36 y 16:04:16 UTC.
- Baseline HTTP anterior al deploy: estatico de Unfold `404`; titulo
  `Identificarse | Administración de sitio Django`;
  cabecera `Content-Security-Policy-Report-Only` sin `unsafe-eval` en
  `script-src`; footer `v21.10.26`.
- Verificacion HTTP posterior al deploy, sin autenticacion:

  | Criterio | Salida observada | Resultado |
  | --- | --- | --- |
  | `GET /static/unfold/css/styles.css` | `200` | cumple |
  | Titulo de `/admin/login/` | `[QA] Identificarse \| SISOC admin` (HTTP 200) | cumple |
  | CSP de `/admin/login/` | `Content-Security-Policy-Report-Only`, `script-src` incluye `'unsafe-eval'` | cumple; sigue en modo report-only |
  | Footer de `/` | `v21.10.26` (HTTP 200) | no cumple el cambio de etiqueta solicitado |

  El footer no identifica el commit desplegado. En
  `src/backends/kernel/core/context_processors.py`, `footer_version` toma
  `get_current_version` y cachea la etiqueta 300 segundos. En
  `src/backends/kernel/core/views.py`, esa funcion obtiene la primera version
  de `CHANGELOG.md` (local o fallback GitHub). El changelog del SHA desplegado
  comienza con `Version SISOC 21.10.2026` (con tilde en el archivo).
  La etiqueta observada es coherente con esa fuente y no invalida el SHA ni
  los otros chequeos. No se inspecciono cual fuente uso el proceso en runtime.
  No se modificaron la semantica del footer, el changelog ni releases para
  forzar otra fecha: ese criterio queda explicitamente pendiente.
- HML y PRD: API confirma `sisoc-homologacion-org` y `sisoc-produccion-org`
  online, con `[self-hosted, sisoc-homologacion]` y
  `[self-hosted, sisoc-produccion]`, respectivamente, en el mismo grupo.
  SSH confirma servicios activos y procesos en
  `/home/sisoc-deploy/actions-runner-org-homologacion` y
  `/home/sisoc-deploy/actions-runner-org-produccion`.
- `production` conserva la regla `required_reviewers`; no se aprobo.
- `git diff --check`: sin errores. Comprobacion documental ejecutada sobre los
  seis Markdown tocados con
  `python src/scripts/ci/check_docs_paths.py --existencia`: 85 documentos
  vigentes, 0 referencias obsoletas o rotas. No se ejecutaron tests/build de
  aplicacion porque el diff es exclusivamente documental.
- PR documental [#2809](https://github.com/secretarianaf/SISOC/pull/2809), en
  borrador hacia `development`, sin merge. El resultado de CI se informa en
  el PR; no equivale a aceptacion humana ni a validacion de deploy HML/PRD.

## Riesgos y limites

El proximo deploy autorizado de `homologacion`/`main` es la primera prueba real
de SISOC con los runners de organizacion en esos entornos. Estar online no
demuestra permisos Docker, migraciones, collectstatic ni salud de la aplicacion.
No se ejecutaron deploys HML/PRD, comandos Docker, cambios de DB, sudo ni
inspecciones de `.env` desde esta sesion. El inicio automatico de los servicios
no se reverifico. El resto de los inventarios conserva sus fechas originales.

Ante regresion de acceso, revisar grupo, seleccion, permiso de publicos y
labels. Revocar el permiso de publicos vuelve a bloquear SISOC; no revierte un
deploy ya ejecutado. Un rollback de aplicacion requiere su procedimiento y
autorizacion propios. No restaurar runners de repositorio sin confirmacion.

Skill utilizada: `registro-cambios`, para separar evidencia operativa, cambios
documentales, deploy y validaciones pendientes conforme al registro del repo.
