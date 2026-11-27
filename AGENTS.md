# AGENTS.md

Reglas para agentes de IA en SISOC (Codex, Claude Code). Solo contiene lo que un agente haria mal sin ayuda: los limites los aplican los guardrails (`.agents/guardrails.toml`), la calidad la exige la CI y los flujos viven en skills (`.agents/skills/`), que se cargan por su descripcion.

## Antes de empezar

- Rama nueva desde `origin/development` actualizado (`git fetch origin`). No revertir cambios ajenos.
- Para ubicar codigo, usar CodeGraph primero; si no esta disponible, grep. No leer docs enteros por defecto: `docs/indice.md` es el indice y `docs/ia/AGENT_REPO_MAP.md` da orientacion estable.

## Verticales independientes

Guia: `docs/desarrollo/verticales_independientes.md`.

- El kernel no importa core ni verticales; un servicio no importa a otro, tampoco su `api.py`.
- Registrar prefijos en `src/backends/config/backends.json` y regenerar `src/backends/config/url_registry.json`.
- Resolver archivos por app o `__file__`, nunca por `BASE_DIR` + nombre de app.
- Comandos del grafo completo y `collectstatic` corren en el migrador, no en la web de deploy.

## Codigo

- La logica de negocio vive en `services/` de la app; views y templates no concentran reglas de dominio.
- Views nuevas: class-based. Las function-based existentes no se migran salvo pedido.
- Seguir un caso parecido que ya exista y nombrarlo en el PR ("se hizo como `X`").
- Si se agregan dependencias, modelos, settings o permisos, decirlo en el PR con el motivo.
- Commits en espanol: `<type>(<scope>): <subject>`.
- Cada test afirma el resultado esperado; ejecutar lineas sin verificar nada no cuenta como test.
- Registrar en `docs/registro/` los cambios funcionales visibles, de arquitectura o de permisos.

## Comandos

Con el entorno local levantado (`docker compose up`). Son los mismos chequeos de CI.

```bash
docker compose exec django pytest -n auto
docker compose exec django pytest src/backends/<dueño>/tests/test_<modulo>.py -v
docker compose exec django python manage.py makemigrations --check --dry-run
docker compose exec django black --config pyproject.toml <archivos.py>
docker compose exec django pylint --rcfile=.pylintrc <archivos.py>
docker compose exec django djlint <templates.html> --check --configuration=.djlintrc
python src/scripts/ci/check_docs_paths.py --existencia <docs.md>
python src/scripts/ai/sync_agents.py   # tras editar .agents/skills/ o .agents/guardrails.toml
```
