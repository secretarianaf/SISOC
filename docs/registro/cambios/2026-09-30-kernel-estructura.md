# Kernel en `kernel/` (Ola 0 de desplegables independientes)

Primer paso del ADR `docs/registro/decisiones/2026-09-30-monorepo-kernel-backends.md`
(épicas #1931 y #2251).

## Qué cambió

- Se movieron `core`, `users`, `iam`, `ciudadanos` y `audittrail` a `kernel/`
  con `git mv`, sin cambios de contenido.
- Los imports, los app labels, las migraciones y las tareas de Celery siguen
  iguales (`import core`, `users.0051`, etc.). `config/__init__.py` agrega
  `kernel/` al `sys.path`. Django, Gunicorn, Celery y pytest-django importan
  `config` antes que cualquier app.
- El tooling estático declara la misma raíz: `.pylintrc` (`init-hook`),
  `pytest.ini` (`pythonpath`) y `.github/workflows/architecture.yml`
  (`PYTHONPATH` para import-linter).
- Pylint: se desactiva `C0411` (wrong-import-order), porque el isort interno
  de pylint no lee la configuración del proyecto y clasifica los paquetes de
  `kernel/` como third party. El job de CI agrega `kernel/*/*.py`: sin
  globstar, `**/*.py` solo cubre un nivel de carpetas.
- Se ajustaron las rutas que dependían de la ubicación física: el fixture
  territorial, el comando `export_relaciones_territoriales_fixture`,
  `debug_queries`, el generador del mapa de arquitectura y los tests que leen
  archivos del kernel.

## Sin cambios

- Comportamiento funcional, URLs, permisos, datos y migraciones.
- Deploy y compose. Los contenedores siguen montando el checkout; eso cambia
  en la Ola 1.

## Riesgos

- Los PRs abiertos que tocan estas apps deben actualizarse desde
  `development`. Git detecta los renombres y en general los resuelve solo.
- Un script que importe `core`, `users`, etc. **sin** importar antes `config`
  necesita `PYTHONPATH=kernel`. `scripts/debug_cruce.py` ya importaba antes de
  configurar Django y sigue igual.
