# AGENTS.md

Reglas para agentes de IA en SISOC (Codex, Claude Code). Solo contiene lo que un agente haria mal sin ayuda: los limites los aplican los guardrails (`.agents/guardrails.toml`), la calidad la exige la CI y los flujos viven en skills (`.agents/skills/`), que se cargan por su descripcion.

## Antes de empezar

- Rama nueva desde `origin/development` actualizado (`git fetch origin`). No revertir cambios ajenos.
- Para ubicar codigo, usar CodeGraph primero; si no esta disponible, grep. No leer docs enteros por defecto: `docs/indice.md` es el indice y `docs/ia/AGENT_REPO_MAP.md` da orientacion estable.
- Al tocar `src/backends/` o `src/frontends/`, aplicar tambien el `AGENTS.md` de esa carpeta y los de carpetas mas profundas que correspondan.

## Codigo

- Seguir un caso parecido que ya exista y nombrarlo en el PR ("se hizo como `X`").
- Si se agregan dependencias, modelos, settings o permisos, decirlo en el PR con el motivo.
- Commits en espanol: `<type>(<scope>): <subject>`.
- Cada test afirma el resultado esperado; ejecutar lineas sin verificar nada no cuenta como test.
- Registrar en `docs/registro/` los cambios funcionales visibles, de arquitectura o de permisos.
