---
name: validar-cambio
description: >
  Comandos de tests, migraciones, formato, lint y docs. Usar cuando haya que correr pytest, black,
  pylint, djlint o makemigrations, o validar antes de un commit o PR.
---

# Validar cambio

Con el entorno local levantado (`docker compose up`). Son los mismos chequeos de
CI (`.github/workflows/lint.yml` y `.github/workflows/tests.yml`). Correr solo
los que aplican a lo tocado; lo que no se pudo correr se dice, no se da por pasado.

## Tests

```bash
docker compose exec django pytest src/backends/<dueño>/tests/test_<modulo>.py -v  # el módulo tocado
docker compose exec django pytest -n auto                                          # suite completa
docker compose exec django pytest -m smoke
docker compose exec django pytest -m mysql_compat                                  # MySQL real
```

## Migraciones

Si cambian modelos:

```bash
docker compose exec django python manage.py makemigrations --check --dry-run
```

## Formato y lint de los archivos tocados

```bash
docker compose exec django black --config pyproject.toml <archivos.py>
docker compose exec django pylint --rcfile=.pylintrc <archivos.py>
docker compose exec django djlint <templates.html> --check --configuration=.djlintrc
```

## Front v2 (`src/frontends/`)

```bash
cd src/frontends && npm run lint && npm run typecheck && npm run test
```

Si cambió una API que consume el front, regenerar su esquema (comandos en
`.github/workflows/frontend-v2.yml`, pasos de contrato OpenAPI) y commitearlo.

## Docs y configuración para agentes

```bash
python src/scripts/ci/check_docs_paths.py --existencia <docs.md>   # rutas citadas en los docs tocados
python src/scripts/ai/sync_agents.py                               # tras editar .agents/skills/ o .agents/guardrails.toml
```
