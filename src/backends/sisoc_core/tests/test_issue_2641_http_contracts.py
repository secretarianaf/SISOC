"""Contratos sobre HTTP real entre procesos; no prueba imágenes ni deploy."""

import os
import selectors
import subprocess
import sys
from pathlib import Path

import pytest
from django.contrib.auth.models import Permission, User
from django.db import connection
from django.test import Client, RequestFactory
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from comedores.models import Comedor
from dashboard.comedores_metrics import METRIC_KEYS, actualizar_metricas_comedores
from dashboard.models import Dashboard
from pwa.models import AccesoComedorPWA

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def owner_process(tmp_path, monkeypatch):
    """Sólo loopback del contenedor aislado; misma DB sintética, otro proceso."""
    if os.name != "posix":
        pytest.skip(
            "Este probe de procesos se ejecuta en el contenedor Linux de pruebas."
        )
    script = """
import config, django
django.setup()
from django.core.wsgi import get_wsgi_application
from django.urls import resolve
from wsgiref.simple_server import make_server
resolve('/interno/espacios/login/')
resolve('/interno/usuarios/operacion/')
server = make_server('127.0.0.1', 0, get_wsgi_application())
print('READY http://127.0.0.1:' + str(server.server_port), flush=True)
server.serve_forever()
"""
    env = {
        **os.environ,
        "DATABASE_NAME": connection.settings_dict["NAME"],
        "DJANGO_SETTINGS_MODULE": "config.settings_all",
        "WAIT_FOR_DB": "false",
    }
    log_path = tmp_path / "owner-http.log"
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
            origin = line.removeprefix("READY ")
            process.contract_log = log_path
            from core import internal_services

            original_owner = internal_services.backend_de_app
            # Destino del contrato inyectado en el test. El registro, imágenes y
            # topología reales pertenecen a C3 y no se dan por probados aquí.
            monkeypatch.setattr(
                internal_services,
                "backend_de_app",
                lambda app: (
                    {"origin": origin}
                    if app in {"pwa", "comedores"}
                    else original_owner(app)
                ),
            )
            yield process
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=15)
            process.stdout.close()


def test_login_contexto_metricas_y_caida_de_dueno_sobre_http(owner_process):
    password = "ContratoSeguro123!"
    user = User.objects.create_user(username="contrato_http", password=password)
    user.profile.acceso_web = False
    user.profile.save(update_fields=["acceso_web"])
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="dashboard", codename="view_dashboard"
        )
    )
    comedor = Comedor.objects.create(nombre="Espacio HTTP")
    AccesoComedorPWA.objects.create(user=user, comedor=comedor, rol="representante")
    client = APIClient()
    login = client.post(
        "/api/users/login/", {"username": user.username, "password": password}
    )
    assert login.status_code == 200, owner_process.contract_log.read_text()
    token = login.data["token"]
    assert Token.objects.filter(key=token, user=user).exists()
    user.profile.must_change_password = True
    user.profile.needs_profile_confirmation = True
    user.profile.save(
        update_fields=["must_change_password", "needs_profile_confirmation"]
    )
    # Cookie web previa + Token: conserva el tratamiento de la API pública,
    # incluso sin acceso web y con confirmaciones pendientes.
    client.force_login(user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    context = client.get("/api/users/me/")
    assert context.status_code == 200
    assert context.data["espacios_comunitarios_disponible"] is True
    assert context.data["pwa"]["comedores_representados"] == [comedor.pk]
    request = RequestFactory().get("/dashboard/", HTTP_AUTHORIZATION=f"Token {token}")
    request.user = user
    assert actualizar_metricas_comedores(request)
    previous = dict(
        Dashboard.objects.filter(llave__in=METRIC_KEYS).values_list("llave", "cantidad")
    )
    assert previous["cantidad_comedores_activos"] == Comedor.objects.count()
    owner_process.terminate()
    owner_process.wait(timeout=15)
    assert not actualizar_metricas_comedores(request)
    assert (
        dict(
            Dashboard.objects.filter(llave__in=METRIC_KEYS).values_list(
                "llave", "cantidad"
            )
        )
        == previous
    )
    context = client.get("/api/users/me/")
    assert context.status_code == 200
    assert context.data["espacios_comunitarios_disponible"] is False
    assert "dashboard.view_dashboard" in context.data["permissions"]
    independent = User.objects.create_user(
        username="datacalle_sin_dueno", password=password
    )
    independent.profile.es_relevador_calle = True
    independent.profile.datacalle_rol = "entrevistador"
    independent.profile.save()
    independent_login = APIClient().post(
        "/api/users/login/",
        {
            "username": independent.username,
            "password": password,
        },
    )
    assert independent_login.status_code == 200
    assert client.post("/api/users/logout/", {}).status_code == 200
    assert not Token.objects.filter(key=token).exists()


def test_operacion_compuesta_http_valida_sesion_csrf_y_guarda_completa(owner_process):
    admin = User.objects.create_superuser(
        username="admin_http", password="ContratoSeguro123!"
    )
    comedor = Comedor.objects.create(nombre="Espacio operación HTTP")
    client = Client(enforce_csrf_checks=True)
    client.force_login(admin)
    page = client.get("/usuarios/crear/")
    assert page.status_code == 200
    # Completar/cerrar la respuesta de streaming antes de iniciar el POST.
    b"".join(page.streaming_content)
    page.close()
    csrf = client.cookies["csrftoken"].value
    response = client.post(
        "/usuarios/crear/",
        {
            "username": "creado_por_dueno_http",
            "tipo_usuario": "interno",
            "es_representante_pwa": "on",
            "tipo_asociacion_pwa": "espacio",
            "comedores_pwa": [comedor.pk],
            "csrfmiddlewaretoken": csrf,
        },
    )
    assert response.status_code == 302
    response.close()
    user = User.objects.get(username="creado_por_dueno_http")
    assert user.profile.must_change_password
    assert AccesoComedorPWA.objects.filter(
        user=user, comedor=comedor, activo=True
    ).exists()
    assert not user.profile.acceso_web
    rejected = client.post(
        "/usuarios/crear/",
        {
            "username": "csrf_invalido_http",
            "es_representante_pwa": "on",
            "csrfmiddlewaretoken": "invalido",
        },
    )
    assert rejected.status_code == 403
    assert not User.objects.filter(username="csrf_invalido_http").exists()
