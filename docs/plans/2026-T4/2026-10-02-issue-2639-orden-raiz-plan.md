# Plan — #2639: ordenar los archivos sueltos de la raíz del repo

- **Issue:** #2639
- **Fecha:** 2026-10-02
- **Estado:** aprobado por el responsable técnico (juanikitro), pendiente de implementación
- **Base:** `development` @ `9f5af3332`

## Decisiones cerradas

Las definió el responsable técnico. Las marcadas como *recomendación del agente* surgieron de la propuesta del agente y fueron aceptadas.

| Tema | Decisión |
|-|-|
| Alcance | **Un solo PR** contra `development`, con un commit por fase. |
| Código | `src/backends/{config, kernel, sisoc_core, pas, cdi, cdf, celiaquia, dispositivos, vat, vpsl}` y `src/frontends/`. `manage.py` queda en la raíz. |
| `templates/`, `static/`, `tests/` | Se reparten por dueño: lo compartido va a `src/backends/kernel/`, y lo de cada vertical, a su app. |
| Datos y artefactos | Se borran `centros.xlsx`, `usuarios.xlsx`, `coverage.json` (el CI no lo usa), `appspec.yml` (nada lo referencia) y `.idea/`. **No** se reescribe el historial de git. **No** se agrega una regla de `*.xlsx` al `.gitignore`. |
| `.idea/` | Se borra y se descomenta `.idea/` en el `.gitignore`. `.vscode/` (compartido a propósito), `.codex/` y `.claude/` quedan como están. |
| `.env.qa`, `.env.homologacion`, `.env.prod` | Se borran. El deploy no los usa (lee el `.env` del servidor). Las diferencias por entorno se documentan en `docs/operacion/instalacion.md`. *Supuesto:* tienen placeholders. Si alguno tuviera una credencial real, hay que rotarla, y eso queda fuera de este PR. |
| Compose | `docker-compose.yml` queda en la raíz (así `docker compose up` sigue funcionando). Los 5 overrides van a `docker/compose/`. *Recomendación del agente.* |
| `requirements.txt` | Pasa a `requirements/all.txt`, sin cambiar qué se instala. |
| `.md` | Se borra lo que no aporte valor, se corrigen las partes obsoletas de los docs vigentes y los registros se ordenan **por trimestre** (`AAAA-TN/`), con el bot escribiendo directo así. `docs/registro/decisiones/` no se mueve. |
| Skills | La fuente vive en `.agents/skills/` (para Codex). La copia en `.claude/skills/` (para Claude Code) la genera `scripts/ai/sync_skills.py`, y un check de CI falla si difieren. *Recomendación del agente:* se descartaron las symlinks porque se rompen en Windows con `core.symlinks=false`. |
| Archivos para agentes | `CODEX.md` y `LLM.md` se fusionan en `AGENTS.md`. `frontend-ui-ux.agent.md` pasa a ser skill. `AGENT_REPO_MAP.md` va a `docs/ia/`. Se crea un spike para revisar el contenido. |
| Fuera de alcance | Sacar `ciudadanos`, `organizaciones` y `catalogo_intervenciones` del kernel y partir `sisoc_core` en verticales: se registró en #2641. Achicar la imagen de producción (hoy instala dev y test): va a #2641. |

## Estructura objetivo

```
.agents/skills/        skills del repo (fuente, Codex)
.claude/               settings y copia generada de las skills (Claude Code)
.codex/                configuración de Codex
.github/               CI/CD
.vscode/               configuración compartida de VS Code y debugger
docker/                Dockerfiles, entrypoint y docker/compose/ (overrides)
docs/                  documentación (ver docs/indice.md)
requirements/          dependencias Python
scripts/               scripts operativos, CI e IA
src/
  backends/
    config/            proyecto Django: settings, urls, wsgi, maquinaria de backends
    kernel/            código común: core, users, iam, audittrail, ... (+ templates/static/tests compartidos)
    sisoc_core/ pas/ cdi/ cdf/ celiaquia/ dispositivos/ vat/ vpsl/
  frontends/           fronts React (apps/<modulo>/)
manage.py  conftest.py  docker-compose.yml  README.md  AGENTS.md  CLAUDE.md  CHANGELOG.md
+ configuración de herramientas (.pylintrc, pytest.ini, pyproject.toml, .importlinter*, .gitleaks*, .djlintrc, .editorconfig, ...)
```

## Fases (un commit por fase)

### 0. Antes del PR

- Crear el issue spike "Revisar los archivos para agentes" (`AGENTS.md`, `CLAUDE.md`, `.codex/rules.md`, `docs/ia/`, skills): label `SPIKE`, asignado a juanikitro y en "En progreso" en el project SISOC #1.
- Sumar a #2641 el seguimiento "la imagen del core instala `requirements/dev.txt` y `test.txt`".

### 1. Limpieza

- Borrar `centros.xlsx`, `usuarios.xlsx`, `coverage.json`, `appspec.yml`, `.idea/`, `.env.qa`, `.env.homologacion` y `.env.prod`.
- `.gitignore`: descomentar `.idea/`.
- `scripts/update_fixtures_from_production.py`: cambiar el default `--env-file` a `.env`.
- Actualizar las menciones en `docs/operacion/instalacion.md`, `docs/infra/QA_INVENTORY.md` y el mapa de agentes.

### 2. Movimiento del código

Se hace con `git mv`, así `git log --follow` sigue funcionando.

- `config/`, `kernel/` y `backends/*` van a `src/backends/`, y `frontends/` va a `src/frontends/`.
- **`BASE_DIR`:** sigue siendo la raíz del repo, porque de él salen `media/`, `logs/` y `static_root/`, que montan los servidores. Se agrega una constante aparte para la ruta del código.
- **`sys.path`:** se actualiza en `manage.py`, `config/__init__.py`, `pytest.ini` (`pythonpath`, `testpaths`), `.pylintrc`, `.importlinter`, `.importlinter_celiaquia_config` y `architecture.yml`. Los imports no cambian (`import core`, `import config`, `import pas`), así que tampoco cambian los app labels, las migraciones ni los nombres de las tareas de Celery.
- **Plantillas:**
  - Las compartidas van a `src/backends/kernel/templates/`, y las de cada vertical, a `<app>/templates/`.
  - El directorio compartido **sigue en `TEMPLATES["DIRS"]`**, porque el override de `templates/admin/` depende de que `DIRS` tenga prioridad sobre `APP_DIRS`.
- **Estáticos:** los compartidos van a `src/backends/kernel/static/` (`STATICFILES_DIRS`). Los de un vertical, si los hay, van a `<app>/static/`.
- **Tests:**
  - Los transversales van a `src/backends/kernel/tests/`, y los de cada vertical, junto a su app.
  - El `conftest.py` global queda en la raíz.
- **Docker:**
  - Se actualizan los `COPY` de `docker/django/Dockerfile` y de los Dockerfiles de cada vertical. La imagen del core sigue sin incluir verticales (#2635).
  - También se actualizan `.dockerignore` y los build contexts y volúmenes de los compose.
- **Config de backends:** se actualizan las rutas en `config/backends.json`, `url_registry.json` y `backend_settings.py`.
- **CI:**
  - Se actualizan los paths y filtros de `tests.yml`, `lint.yml`, `architecture.yml`, `frontend-v2.yml` y `deploy.yml`.
  - En `scripts/operacion/deploy_targets.py`, **`src/backends/kernel/` y `src/backends/config/` siguen desplegando todo** y no se cuentan como verticales.
- **Scripts:** se actualizan `scripts/infra/*`, `scripts/arquitectura/generar_mapa.py`, `generar_mapa_arquitectura`, `scripts/ai/*` y `deploy_verified.sh`.
- **Herramientas:** se actualizan `.djlintrc`, `.prettierignore`, `pyproject.toml` y los `pathMappings` de `.vscode/launch.json`.
- **Front:** se ajustan `package-lock.json` y el workspace npm de `src/frontends`.

### 3. Compose y requirements

- Los cinco overrides `docker-compose.{celery,codex,deploy,frontends.dev,produccion}.yml` van a `docker/compose/`.
- Hay que revisar las rutas relativas (`env_file`, `build.context` y volúmenes) con `--project-directory` en la raíz.
- Se actualizan `deploy.yml`, `deploy_refresh.sh`, `preflight.sh`, `codex_common.ps1`, el `README` y los docs de operación.
- `requirements.txt` pasa a `requirements/all.txt`, y se actualizan `Dockerfile`, `codex_common.ps1` y `docs/seguridad/security_baseline.md`.

### 4. Documentación

- **Movimientos:**
  - `postman/` va a `docs/api/postman/`, y se actualiza `SIN_DEPLOY_PREFIJOS` en `deploy_targets.py` y los docs de VAT y PWA.
  - `benchmarks/baselines/` va al lado de `src/backends/kernel/core/benchmarks/`, y se actualizan el test y el JSON.
  - `analisisexpedientes.md` va a `docs/analisis/`.
  - `AGENT_REPO_MAP.md` va a `docs/ia/AGENT_REPO_MAP.md`, y se actualiza la regla de `AGENTS.md`.
  - `var/arquitectura/` no está en git: solo se documenta como salida generada.
- **Auditoría de los `.md`** (~1.700):
  - **Se borra:** lo duplicado (por ejemplo, ver si `docs/contexto/features/` repite `docs/registro/prs/`), lo reemplazado por otro doc, y lo que describe rutas o código que ya no existen sin valor histórico.
  - **Se corrigen** las partes obsoletas de los docs vigentes, incluidas las rutas viejas tras el movimiento.
  - La descripción del PR lista lo borrado, para revisarlo.
- **Por trimestre (`AAAA-TN/`):**
  - Se ordenan `docs/registro/cambios/`, `docs/registro/prs/`, `docs/contexto/features/` y `docs/plans/`. Los `README.md` e índices quedan en la raíz de cada carpeta.
  - Se ajustan `scripts/ci/pr_doc_automation.py`, la regla de `docs/registro/README.md`, `AGENTS.md`, `docs/indice.md` y los demás índices.

### 5. Skills

- Crear `.agents/skills/tema-verde-institucional/SKILL.md` (adjunto del primer comentario de #2639) y `.agents/skills/frontend-ui-ux/SKILL.md`, convertido a partir de `frontend-ui-ux.agent.md`.
- Crear `scripts/ai/sync_skills.py`: copia `.agents/skills/` a `.claude/skills/`, sin dependencias, y tiene un modo `--check`.
- Agregar el check al CI (en `lint.yml` o en el workflow que corresponda) y a `scripts/ai/preflight.sh`.
- Escribir `docs/ia/SKILLS.md`, que explica cómo agregar o editar una skill.

### 6. Cierre

- `README.md`: agregar el mapa de carpetas de primer nivel, con el propósito de cada una.
- Escribir el ADR nuevo `docs/registro/decisiones/2026-10-02-estructura-src-backends.md`, que reemplaza la parte de estructura de `2026-09-30-monorepo-kernel-backends.md`. Registra:
  - `src/` y el kernel dentro de backends, con pros, contras y la alternativa descartada.
  - Cómo se comparten las skills.
  - Que no se reescribe el historial.
  - El borrado de los `.env` por entorno.
- Agregar la entrada en `docs/registro/cambios/2026-T4/`.

## Validación

- **Rápida, en la sesión:**
  - `lint-imports`, `pylint` sobre lo tocado, `djlint templates --check` (con la ruta nueva), `python manage.py check`, `makemigrations --check --dry-run` y `collectstatic --noinput`.
  - `docker compose config` para cada combinación de compose, el build de las imágenes del core y de un vertical, y `sync_skills.py --check`.
  - `git grep` de las rutas viejas (`kernel/`, `backends/`, `config/` y `frontends/` sin `src/`, los compose de la raíz y `requirements.txt`): tiene que dar cero fuera de los registros históricos.
- **Con OK, porque es lenta o externa:** `pytest -n auto` completo, el CI del PR y un deploy a QA, revisando la salud de los 7 backends, Celery de PAS, los workers y el front v2.

## Criterios de aceptación y evidencia

| Criterio | Evidencia |
|-|-|
| No quedan datos personales en el árbol, y la decisión sobre el historial está registrada | Fase 1 y ADR |
| La raíz tiene solo configuración de herramientas, puntos de entrada y carpetas con propósito | `git ls-tree origin/<rama>` y mapa del README |
| Cada movimiento actualiza sus referencias, y la suite, el CI y el deploy a QA pasan | `git grep`, `pytest`, CI y deploy a QA |
| La decisión sobre `src/` queda registrada | ADR de la fase 6 |
| `README.md` tiene el mapa de primer nivel | Fase 6 |

## Riesgos

- **Rutas de runtime en los servidores** (`media`, `logs`, `.env`, volúmenes). Se mitiga manteniendo `BASE_DIR` en la raíz y validando en QA.
- **Mezcla con la modularización en el pase a HML/PRD.** Se recomienda promover primero la modularización a HML/PRD y después este PR.
- **Conflictos con PRs y ramas abiertas** (hoy hay 1 PR abierto). Se mitiga con un solo PR y un merge rápido.
- **Links rotos** en issues o PRs viejos que apuntan a docs movidos. Es aceptable, y `decisiones/` no se mueve.
- **Sentry y code mappings:** cambian las rutas en los stack traces. Hay que revisarlo después del deploy.
- **Deploy selectivo:** si `deploy_targets.py` toma `src/backends/kernel/` como un vertical, un cambio en el kernel no despliega todo. Se cubre con tests de `deploy_targets`.
