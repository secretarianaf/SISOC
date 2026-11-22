"""Puerta común de ``/api/web/core/``: métodos, admindocs y cabecera de puerta falsificada."""

import pytest
from django.contrib.auth.models import User
from django.test import Client

pytestmark = pytest.mark.django_db

LECTURAS = (
    "/api/web/core/novedades/",
    "/api/web/core/arquitectura/",
    "/api/web/core/programas/",
    "/api/web/core/programas/crear/",
)


def _cliente(username, **flags):
    user = User.objects.create_user(username=username, password="x", **flags)
    client = Client()
    client.force_login(user)
    return client


def test_admindocs_head_no_agrega_x_view():
    cliente = _cliente("core_staff", is_staff=True)
    for url in LECTURAS:
        respuesta = cliente.head(url)
        assert "X-View" not in respuesta
        assert respuesta.status_code == 200


def test_metodos_no_admitidos_son_405():
    cliente = _cliente("core_metodos")
    for url in ("/api/web/core/novedades/", "/api/web/core/arquitectura/"):
        assert cliente.post(url).status_code == 405
        assert cliente.delete(url).status_code == 405
    assert cliente.put("/api/web/core/programas/crear/").status_code == 405


def test_cabecera_de_puerta_falsificada_no_autentica():
    respuesta = Client().get(
        "/api/web/core/programas/", HTTP_X_SISOC_WEB_GATE="falsificada"
    )
    assert respuesta.status_code == 401


def test_papelera_head_no_agrega_x_view_y_sigue_403_para_staff():
    cliente = _cliente("core_staff_papelera", is_staff=True)
    respuesta = cliente.head("/api/web/core/papelera/")
    assert "X-View" not in respuesta
    assert respuesta.status_code == 403
