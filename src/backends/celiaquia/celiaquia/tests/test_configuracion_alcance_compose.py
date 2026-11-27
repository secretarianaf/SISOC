"""El origen del núcleo se declara sin leer configuración privada."""

from pathlib import Path

import yaml


def test_compose_deploy_declara_origen_del_nucleo_con_override():
    raiz = Path(__file__).resolve().parents[5]
    compose = yaml.safe_load(
        (raiz / "docker/compose/docker-compose.deploy.yml").read_text(encoding="utf-8")
    )
    entorno = compose["services"]["backend_celiaquia"]["environment"]
    assert entorno["SISOC_CORE_ORIGIN"] == "${SISOC_CORE_ORIGIN:-http://django:8000}"
