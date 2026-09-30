"""Paquete de configuración del SISOC core.

Único punto que agrega las raíces de código al ``sys.path`` en runtime.
Django, Gunicorn, Celery y pytest-django importan ``config`` antes que
cualquier app, así que los imports siguen siendo ``import core``,
``import users``, etc., aunque el código viva en ``kernel/``.

El tooling estático (pylint, import-linter) no ejecuta este archivo: declara
las mismas raíces en ``.pylintrc`` y en ``.github/workflows/architecture.yml``.
Ver ``docs/registro/decisiones/2026-09-30-monorepo-kernel-backends.md``.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KERNEL_DIR = REPO_ROOT / "kernel"

KERNEL_PATH = str(KERNEL_DIR)
if KERNEL_PATH not in sys.path:
    sys.path.insert(0, KERNEL_PATH)
