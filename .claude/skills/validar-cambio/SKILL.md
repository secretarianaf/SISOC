---
name: validar-cambio
description: >
  Comandos de SISOC para validar un cambio en el entorno local: tests, migraciones, formato, lint,
  rutas de docs y sincronización de skills y guardrails. Usar cuando haya que correr tests, black,
  pylint, djlint o makemigrations, o verificar un cambio antes de un commit o un PR.
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

## Docs y configuración para agentes

```bash
python src/scripts/ci/check_docs_paths.py --existencia <docs.md>   # rutas citadas en los docs tocados
python src/scripts/ai/sync_agents.py                               # tras editar .agents/skills/ o .agents/guardrails.toml
```
