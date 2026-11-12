#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import logging
import os
import sys

# El código vive en src/backends/ (config, kernel y verticales). config agrega
# el kernel y cada vertical al sys.path antes de cargar el settings, que puede
# vivir en un backend (p. ej. dispositivos_runtime.settings).
BACKENDS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "src", "backends"
)
if BACKENDS_DIR not in sys.path:
    sys.path.insert(0, BACKENDS_DIR)

import config  # noqa: E402,F401  pylint: disable=unused-import,wrong-import-position


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("django")


def check_migration_context():
    """Rechaza el grafo parcial antes de inicializar Django o acceder a la DB."""
    commands = {
        "createsuperuser",
        "makemigrations",
        "migrate",
        "showmigrations",
        "sqlmigrate",
        "squashmigrations",
        "optimizemigration",
    }
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        return
    if any(arg in {"-h", "--help"} for arg in sys.argv[2:]):
        return
    selected = os.environ["DJANGO_SETTINGS_MODULE"]
    for index, arg in enumerate(sys.argv[2:], 2):
        if arg.startswith("--settings="):
            selected = arg.split("=", 1)[1]
        elif arg == "--settings" and index + 1 < len(sys.argv):
            selected = sys.argv[index + 1]
    from config.backends import load_backends_registry

    complete = all(
        os.path.isdir(os.path.join(BACKENDS_DIR, name))
        for name in load_backends_registry()
    )
    if selected != "config.settings_all" or not complete:
        print(
            "Este comando requiere el migrador completo, no el grafo parcial de "
            "este servicio. Desde el host del deploy ejecute:\n"
            "python3 src/scripts/operacion/manage_deploy.py "
            + " ".join(sys.argv[1:2])
            + " [argumentos Django]\nNo se aplicaron migraciones ni se crearon usuarios.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    # manage.py consulta DEBUG antes de que Django procese --settings.
    os.environ["DJANGO_SETTINGS_MODULE"] = selected


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    check_migration_context()

    # To debug in Docker
    from django.conf import settings

    if settings.DEBUG:
        if os.environ.get("RUN_MAIN") or os.environ.get("WERKZEUG_RUN_MAIN"):
            import debugpy

            debugpy.listen(("0.0.0.0", 3000))
            logger.info("Debugger listo")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
