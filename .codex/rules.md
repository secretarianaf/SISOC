# Codex rules

Fuente de verdad: `AGENTS.md`. Este archivo solo agrega lo especifico de Codex.

- Partir siempre de `development` actualizado; `src/scripts/ai/codex_task.ps1 <slug>` crea branch y worktree desde `origin/development`.
- Validar con `src/scripts/ai/codex_run.ps1 validate` cuando aplique; sumar checks puntuales si el cambio lo requiere.
- Las acciones del entorno estan en `.codex/environments/environment.toml`.
