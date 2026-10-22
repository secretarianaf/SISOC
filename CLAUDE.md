# CLAUDE.md

Guía para Claude Code en este repositorio.

**Leer `AGENTS.md` antes de cualquier tarea.** Es la fuente de verdad para agentes: arranque mínimo, reglas de código, verticales independientes, documentación y validación. Este archivo solo agrega lo específico de Claude Code; si algo de acá contradice `AGENTS.md`, vale `AGENTS.md`.

## Específico de Claude Code

- Partir de `development` actualizado. `.claude/settings.json` fija `worktree.baseRef: fresh` para los worktrees que crea Claude Code; igual confirmar la base antes de abrir el PR.
- Skills: `.claude/skills/` es una copia generada de `.agents/skills/`. Editar la fuente y correr `python src/scripts/ai/sync_skills.py` (ver `docs/ia/SKILLS.md`).
- `.claude/settings.json` permite `docker compose *` sin confirmación; `.claude/settings.local.json` es personal y está ignorado por Git.

## Comandos

En un entorno local aislado (`docker compose up`). Son los mismos chequeos que corre CI (`.github/workflows/lint.yml` y `tests.yml`).

```bash
# Tests: todos en paralelo, un archivo, smoke o MySQL real
docker compose exec django pytest -n auto
docker compose exec django pytest src/backends/<dueño>/tests/test_<modulo>.py -v
docker compose exec django pytest -m smoke
docker compose exec django pytest -m mysql_compat

# Migraciones sin cambios pendientes
docker compose exec django python manage.py makemigrations --check --dry-run

# Formato y lint de los archivos tocados
docker compose exec django black --config pyproject.toml <archivos.py>
docker compose exec django pylint --rcfile=.pylintrc <archivos.py>
docker compose exec django djlint <templates.html> --check --configuration=.djlintrc

# Rutas citadas en los docs tocados
python src/scripts/ci/check_docs_paths.py --existencia <docs.md>
```
