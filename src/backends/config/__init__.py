"""Paquete de configuración del SISOC core.

Único punto que agrega las raíces de código al ``sys.path`` en runtime:
``src/backends/kernel/`` y cada ``src/backends/<vertical>/`` presente en disco.
``src/backends/`` (donde vive este paquete) lo agrega quien arranca el proceso:
``manage.py``, ``PYTHONPATH`` en las imágenes y ``pythonpath`` de pytest.
Django, Gunicorn, Celery y pytest-django importan ``config`` antes que
cualquier app, así que los imports siguen siendo ``import core``,
``import dispositivos``, etc.

La imagen de cada servicio copia solo lo suyo: la del core no trae los
verticales y la de un backend trae solo su carpeta, así que un import de otro
vertical falla en runtime.

El tooling estático (pylint, import-linter) no ejecuta este archivo: declara
las mismas raíces en ``.pylintrc`` y en ``.github/workflows/architecture.yml``.
Ver ``docs/registro/decisiones/2026-10-02-estructura-src-backends.md``.
"""

import sys
from pathlib import Path

BACKENDS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKENDS_DIR.parent.parent
KERNEL_DIR = BACKENDS_DIR / "kernel"
# Carpetas de src/backends/ que no son verticales.
NO_VERTICALES = {"config", "kernel"}

CODE_ROOTS = [KERNEL_DIR] + sorted(
    p
    for p in BACKENDS_DIR.iterdir()
    if p.is_dir() and p.name not in NO_VERTICALES and not p.name.startswith((".", "_"))
)

for code_root in reversed(CODE_ROOTS):
    if str(code_root) not in sys.path:
        sys.path.insert(0, str(code_root))
