"""Registro de backends por vertical (``config/backends.json``).

Solo stdlib: lo leen los settings, el proxy del core y los scripts de deploy
(`scripts/operacion/deploy_targets.py`), que corren en el host sin Django.

Cada entrada describe un backend en ``backends/<nombre>/``:

- ``apps``: apps Django propias del backend, que el core no instala.
- ``url_prefixes``: prefijos de URL (sin ``/`` inicial) que el core reenvía.
- ``urlconf``: URLconf del backend, que también usa ``config/urls_all.py``.
- ``origin_env`` / ``default_origin``: dónde escucha el backend en la red de
  Compose.
- ``service`` / ``migrate_service``: servicios de Compose de web y migración.
- ``extra_services``: otros servicios con el mismo código (Celery de PAS);
  el deploy selectivo los recrea junto con el backend.
- ``favorite_sections``: secciones de filtros favoritos del backend; el core
  le reenvía esos pedidos.
- ``ciudadano_contributions``: secciones de Ciudadano 360 que el core le pide
  ya renderizadas (ciudadanos.detail_contributions).
"""

import json
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parent / "backends.json"


def load_backends_registry(path=REGISTRY_PATH):
    with open(path, encoding="utf-8") as registry:
        return json.load(registry)
