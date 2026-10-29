# Cambio: revisión de los archivos para agentes (#2645)

## Alcance

Spike de #2645: revisar `AGENTS.md`, `CLAUDE.md`, `.codex/`, `.claude/`,
`docs/ia/` y las skills del repo, que #2639 solo había reubicado. Las
decisiones de criterio las tomó el responsable del issue; la auditoría y la
redacción las hizo el agente.

Decisiones del responsable:

- La lógica de negocio va **preferentemente** en `services/`; managers/querysets
  para reglas de acceso a datos. Se retira el "nunca en views ni modelos" de `CLAUDE.md`.
- Views nuevas: class-based. Las function-based existentes se toleran.
- Tests obligatorios para funcionalidad nueva (regresión en bugfix cuando sea
  viable); antes `AGENTS.md` decía "cuando aporte cobertura real".
- Se elimina la regla de worktrees en `../worktrees/<slug>`; queda "partir
  siempre de `development` actualizado".
- `CLAUDE.md` pasa a ser un puntero a `AGENTS.md` más lo específico de Claude Code.
- `docs/ia/AGENT_REPO_MAP.md` se poda (sin bitácora de PRs) y se corrige.
- Se agregan tres skills y un control de existencia de rutas en CI.

## Qué cambió

- **Fuente única.** `AGENTS.md` concentra arranque, reglas de código, verticales
  y validación. `CLAUDE.md`, `.codex/rules.md`, `CONTEXT_HYGIENE.md`,
  `CONTRIBUTING_AI.md`, `TESTING.md`, `ARCHITECTURE.md`, `MODULAR_BOUNDARIES.md`
  y `STYLE_GUIDE.md` enlazan en vez de repetir. El bloque de verticales estaba
  copiado cuatro veces.
- **Correcciones.** `CLAUDE.md` ubicaba Comedores en `sisoc_core`; el mapa
  describía `sisoc_core` como cluster de Comedores, omitía `comedores` y `ocr`,
  ubicaba los tests PWA en `sisoc_core` y citaba un pylint distinto del de CI.
  `TESTING.md` presentaba SQLite como excepción (es el default) y listaba jobs de
  CI incompletos. Los comandos de `CLAUDE.md` no usaban las configuraciones de
  CI. `docs/registro/README.md` citaba `scripts/ci/` y otro repositorio.
- **Mapa.** Se reemplazan las líneas de estado de #2641 (aprobaciones, conteos
  de pruebas, autorizaciones) por una sección de navegación con las mismas rutas.
- **Memoria.** `docs/contexto/memoria/sisoc-base.md` se revalida; citaba reglas
  que ya no existen.
- **Skills.** `registro-cambios`, `verticales-checklist` y `migracion-app-label`
  en `.agents/skills/`, cada una con un `ejemplo.md` basado en un caso real
  (#2724, DataCalle en Dispositivos, Firmante). No agregan reglas: aplican
  `docs/registro/README.md` y `docs/desarrollo/verticales_independientes.md`.
  La guía de verticales decía que no hacía falta una skill; se actualiza ese
  párrafo.
- **CI.** `src/scripts/ci/check_docs_paths.py --existencia <docs.md>` falla si
  esos documentos citan una ruta desde la raíz o un enlace relativo que no
  existe. El job `docs_paths` (`.github/workflows/lint.yml`) lo corre sobre los
  Markdown del PR (vía `pr_lint_tools.py changed-files --kind markdown`) y
  `deploy_guard` lo exige.

## Límites

- El control de existencia no ve rutas relativas a una app (`services/x.py`),
  comandos con espacios ni texto fuera de backticks/enlaces. Solo bloquea los
  Markdown modificados: la deuda previa de otros docs no rompe PRs ajenos.
- No cambia código de producción ni comportamiento de la aplicación. No despliega.

## Verificación

- `python src/scripts/ci/check_docs_paths.py --existencia` sobre todos los
  Markdown versionados: 0 referencias obsoletas o rotas.
- Tests nuevos `src/backends/kernel/tests/test_check_docs_paths.py` y el caso
  `markdown` de `test_pr_lint_tools_unit.py`, junto con `test_sync_skills.py`:
  corridos localmente sin Django (`-p no:django --noconftest`); la suite completa
  en Docker queda para CI. La imagen de tests no trae `git`: ahí se saltean los
  dos tests que dependen de `git check-ignore` (probado con `PATH` sin git), y
  el job `docs_paths`, que corre en el runner con git, cubre ese caso.
- `python src/scripts/ai/sync_skills.py --check` y
  `python src/scripts/ai/context_memory.py preflight --target AGENTS.md`.

## Pendiente fuera de alcance

- `skills_sync` no figura entre los checks requeridos de `deploy_guard`.
- `requirements/dev.txt` fija `djlint==1.34.2` y `requirements/lint.txt`,
  `djlint==1.43.2`.
