# Cambio: guardrails, skills por descripción y AGENTS.md mínimo (#2645)

## Alcance

Segunda ronda de #2645. Objetivo: que los límites para agentes los aplique la
herramienta y no una regla escrita, que Claude Code y Codex queden iguales y
sincronizados, y gastar menos tokens por sesión. Las decisiones las tomó el
responsable del issue en una sesión de alineación; la redacción la hizo el agente.

## Decisiones

- **Guardrails desde una fuente única.** `.agents/guardrails.toml` genera
  `.claude/settings.json` y `.codex/rules/sisoc.rules`. Lo que Codex no puede
  aplicar (comodines, archivos, `worktree.baseRef`) queda marcado como solo Claude.
- **Solo se versiona lo que es contrato de equipo y no depende de la máquina.**
  Se borran `.codex/rules.md` (Codex no lo carga) y
  `.codex/environments/environment.toml`. El permiso `docker compose *` pasa a
  la configuración local de cada persona.
- **Skills por descripción.** `AGENTS.md` ya no lista skills. Cada `description`
  dice `Usar cuando ...` y tiene 250 caracteres como máximo: las
  descripciones se cargan en cada sesión.
- **`AGENTS.md` desde cero.** Una línea se queda solo si sin ella el agente se
  equivocaría, si nada más la hace cumplir (guardrail, CI, skill) y si no se
  deduce del código. Pasó de unos 7,8 KB a unos 1,7 KB. Los comandos de validación pasan a la skill
  `validar-cambio`, que se carga solo cuando hace falta.
- **`CLAUDE.md` = `@AGENTS.md`.** Claude Code no lee `AGENTS.md` solo; con el
  import, las dos herramientas cargan el mismo texto.
- **CodeGraph primero para ubicar código.** `docs/ia/AGENT_REPO_MAP.md` se
  recorta de 1300 a unas 200 líneas de orientación estable y deja de
  actualizarse en cada PR. `.codegraph/` se ignora en Git.
- **`gh pr merge` pide confirmación en vez de bloquearse.** La skill
  `preparar-deploy` mergea PRs de sincronización y de satélites; un `deny` del
  proyecto no admite excepciones locales, así que un humano aprueba cada merge.
- **El check de CI avisa y no bloquea.** `agents_sync` reemplaza a `skills_sync`
  y no está en `deploy_guard`. Se quita el test de pytest que exigía la copia de
  skills al día, porque pytest sí bloquea.

- **Reglas por zona.** Las reglas de verticales y Django pasan a
  `src/backends/AGENTS.md`, y las del front v2 a `src/frontends/AGENTS.md`. Cada
  carpeta con `AGENTS.md` tiene un `CLAUDE.md` con `@AGENTS.md`, porque Claude Code
  solo lee `CLAUDE.md` (antes `src/frontends/apps/inet/AGENTS.md` era invisible
  para Claude). Codex incluye la raíz y la ruta hasta su directorio de trabajo;
  para subcarpetas, su prompt le indica buscar el `AGENTS.md` que aplique, por eso
  la raíz lo recuerda en una línea.
- **Se retira la memoria de contexto.** `context_memory.py`, `codex_context.ps1`,
  `preflight.sh` y `docs/contexto/memoria/` ya no los citaba ninguna instrucción
  para agentes; CodeGraph y las skills cubren ese uso. También se borran los
  `codex_*.ps1` y su guía: nadie los usaba y `docker compose` cubre lo mismo.
- **Copilot apunta a `AGENTS.md`.** `.github/copilot-instructions.md` era un
  resumen a mano sin check; queda en una línea.

## Qué cambió

- `AGENTS.md`, `CLAUDE.md`, `.agents/guardrails.toml`, `.claude/settings.json`,
  `.codex/rules/sisoc.rules` y `docs/ia/GUARDRAILS.md` (nuevo).
- `src/scripts/ai/sync_agents.py` reemplaza a `sync_skills.py`: copia skills,
  genera guardrails y valida el frontmatter. Tests en
  `src/backends/kernel/tests/test_sync_agents.py`.
- Descripciones de las 9 skills; las skills ya no citan secciones de `AGENTS.md`
  que dejaron de existir.
- Referencias actualizadas en `docs/ia/SKILLS.md`, `docs/ia/TESTING.md`,
  `docs/indice.md`, `docs/operacion/codex_desktop.md`,
  `docs/contexto/memoria/sisoc-base.md`, `src/scripts/ai/preflight.sh` y
  `.github/workflows/lint.yml`.

## Verificación

- Tests del generador y `sync_agents.py --check` en verde.
- Reglas de Codex probadas con `codex execpolicy check`: bloquea push forzado, push
  a `main`, `gh workflow run`, `ssh` y `manage.py flush`; pide confirmación para
  `gh pr merge`, `git reset --hard` y `npm install <paquete>`; deja pasar
  `git push` de una rama propia, `gh pr view` y `git commit`.

## Límites

- Las reglas comparan prefijos: protegen contra errores, no contra intentos
  deliberados (`bash -c`).
- Codex carga las reglas del proyecto solo si es de confianza, y sus reglas son
  experimentales.
- Como el check no bloquea, un desvío entre fuente y generados puede llegar a
  `development`; el aviso queda visible en el PR.
- Del mapa se quitó contexto por feature (variables de entorno, workers, deploy).
  Sigue en el historial de Git; moverlo a otras guías queda para otra tarea.
