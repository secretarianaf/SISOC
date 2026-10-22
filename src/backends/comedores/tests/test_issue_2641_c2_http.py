"""HTTP hacia el runtime dueño C3; sin acreditar por sí solo imágenes separadas."""

import json
import os
import selectors
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
import requests
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from admisiones.models.admisiones import Admision
from ciudadanos import detail_contributions
from ciudadanos.models import Ciudadano
from comedores.models import Comedor, Nomina, ColaboradorEspacio
from core import backend_proxy
from core.models import FiltroFavorito
from core.services.favorite_filters import registry
from pwa.models import NominaEspacioPWA

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def propietario_http(tmp_path, http_probe_database):
    script = """
import importlib, json, os, sys, time
started = time.monotonic()
import config, django
database = json.loads(os.environ['SISOC_HTTP_PROBE_DATABASE'])
runtime_settings = importlib.import_module(os.environ['DJANGO_SETTINGS_MODULE'])
runtime_settings.DATABASES = {'default': database}
django.setup()
from django.db import connection
assert connection.settings_dict['ENGINE'] == database['ENGINE']
assert connection.settings_dict['NAME'] == database['NAME']
print(f'OWNER_SETUP_SECONDS={time.monotonic() - started:.3f}', file=sys.stderr, flush=True)
from django.urls import resolve
from django.core.wsgi import get_wsgi_application
from wsgiref.simple_server import make_server
resolve('/ciudadanos/1/contribucion/comedores/')
server = make_server('127.0.0.1', 0, get_wsgi_application())
print(f'OWNER_READY_SECONDS={time.monotonic() - started:.3f}', file=sys.stderr, flush=True)
print('READY http://127.0.0.1:' + str(server.server_port), flush=True)
server.serve_forever()
"""
    env = {
        **os.environ,
        "SISOC_HTTP_PROBE_DATABASE": http_probe_database,
        "DJANGO_SETTINGS_MODULE": "comedores_runtime.settings",
        "WAIT_FOR_DB": "false",
    }
    log_path = tmp_path / "c2-owner.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, "-u", "-c", script],
            cwd=Path(__file__).resolve().parents[4],
            env=env,
            stdout=subprocess.PIPE,
            stderr=log,
            text=True,
        )
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                assert selector.select(timeout=30), log_path.read_text()
                line = process.stdout.readline().strip()
            assert line.startswith("READY "), line + log_path.read_text()
            print(log_path.read_text())
            yield process, line.removeprefix("READY ")
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=15)
            process.stdout.close()


def test_ciudadano_y_favoritos_http_sesion_csrf_propiedad_y_caida(
    propietario_http, monkeypatch
):
    process, origin = propietario_http
    user = User.objects.create_superuser(username="c2_http")
    ciudadano = Ciudadano.objects.create(nombre="Persona C2", apellido="HTTP")
    comedor = Comedor.objects.create(nombre="Comedor remoto C2")
    admision = Admision.objects.create(comedor=comedor)
    nomina = Nomina.objects.create(ciudadano=ciudadano, admision=admision)
    NominaEspacioPWA.objects.create(nomina=nomina, situacion_calle=True)
    ColaboradorEspacio.objects.create(
        comedor=comedor, ciudadano=ciudadano, fecha_alta=date.today()
    )
    backend = {"origin": origin}
    monkeypatch.setattr(detail_contributions, "_CONTRIBUCIONES", {})
    monkeypatch.setattr(detail_contributions, "backend_de_app", lambda _app: backend)
    monkeypatch.setattr(backend_proxy, "backend_de_app", lambda _app: backend)
    monkeypatch.setattr(registry, "_CONFIGURACIONES_POR_SECCION", {})
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    url = reverse("ciudadanos_ver", args=[ciudadano.pk])
    response = client.get(url)
    assert response.status_code == 200
    assert b"Comedor remoto C2" in response.content
    assert b"Colaboraciones en comedores" in response.content
    assert "Situación de calle</span>" in response.content.decode()
    favorite_url = reverse("filtros_favoritos")
    page = client.get(favorite_url, {"seccion": "comedores"})
    assert page.status_code == 200
    b"".join(page.streaming_content)
    page.close()
    payload = {"seccion": "comedores", "nombre": "Remoto", "filtros": {"items": []}}
    refused = client.post(
        favorite_url, json.dumps(payload), content_type="application/json"
    )
    assert refused.status_code == 403
    refused.close()
    response = client.post(
        favorite_url,
        json.dumps(payload),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
    )
    assert response.status_code == 201
    data = json.loads(b"".join(response.streaming_content))
    response.close()
    favorite = FiltroFavorito.objects.get(pk=data["id"])
    assert favorite.usuario_id == user.pk
    # Autenticación y permiso se comprueban de nuevo en el dueño.
    denied_user = User.objects.create_user(username="c2_denegado")
    other = Client()
    other.force_login(denied_user)
    headers = {
        "Host": "testserver",
        "Cookie": f"sessionid={other.cookies['sessionid'].value}",
    }
    denied = requests.get(
        f"{origin}/ciudadanos/{ciudadano.pk}/contribucion/comedores/",
        headers=headers,
        timeout=5,
    )
    assert denied.status_code == 403
    detail = reverse("detalle_filtro_favorito", args=[favorite.pk])
    assert other.get(detail).status_code == 404
    process.terminate()
    process.wait(timeout=15)
    response = client.get(url)
    assert response.status_code == 200
    assert b"Persona C2" in response.content
    assert b"Comedor remoto C2" not in response.content
    response = client.delete(detail, HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
    assert response.status_code == 503
    assert FiltroFavorito.objects.filter(pk=favorite.pk).exists()
