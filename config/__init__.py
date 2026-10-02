"""Paquete de configuración del SISOC core.

Único punto que agrega las raíces de código al ``sys.path`` en runtime:
``kernel/`` y cada ``backends/<vertical>/`` presente en disco. Django, Gunicorn,
Celery y pytest-django importan ``config`` antes que cualquier app, así que los
imports siguen siendo ``import core``, ``import dispositivos``, etc.

La imagen de cada servicio copia solo lo suyo: la del core no trae
``backends/`` y la de un backend trae solo su carpeta, así que un import de
otro vertical falla en runtime.

El tooling estático (pylint, import-linter) no ejecuta este archivo: declara
las mismas raíces en ``.pylintrc`` y en ``.github/workflows/architecture.yml``.
Ver ``docs/registro/decisiones/2026-09-30-monorepo-kernel-backends.md``.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KERNEL_DIR = REPO_ROOT / "kernel"
BACKENDS_DIR = REPO_ROOT / "backends"

CODE_ROOTS = [KERNEL_DIR]
if BACKENDS_DIR.is_dir():
    CODE_ROOTS += sorted(p for p in BACKENDS_DIR.iterdir() if p.is_dir())

for code_root in reversed(CODE_ROOTS):
    if str(code_root) not in sys.path:
        sys.path.insert(0, str(code_root))
