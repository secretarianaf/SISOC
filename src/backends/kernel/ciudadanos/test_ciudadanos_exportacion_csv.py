"""Exportación CSV del listado de ciudadanos (C05.04): la descarga nativa se conserva tal cual."""

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.urls import reverse

from ciudadanos.models import Ciudadano

pytestmark = pytest.mark.django_db

HEADER = "Apellido;Nombre;Documento;Sexo;Provincia;Municipio;Localidad"


def _cliente(username, *, ver=True, exportar=True):
    user = User.objects.create_user(username=username, password="x")
    if ver:
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="ciudadanos", codename="view_ciudadano"
            )
        )
    if exportar:
        permiso, _ = Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Group),
            codename="role_exportar_a_csv",
            defaults={"name": "role_exportar_a_csv"},
        )
        user.user_permissions.add(permiso)
    client = Client()
    client.force_login(user)
    return client


def _filas(respuesta):
    cuerpo = b"".join(respuesta.streaming_content).decode("utf-8-sig")
    return cuerpo.strip().splitlines()


@pytest.fixture(name="ciudadanos")
def ciudadanos_fixture():
    Ciudadano.objects.create(nombre="Zoe", apellido="Zeta", documento=30111222)
    Ciudadano.objects.create(nombre="Ana", apellido="Alfa", documento=30111223)
    Ciudadano.objects.create(nombre="Beto", apellido="Alfa", documento=30111224)


def test_exporta_el_listado_ordenado_como_csv(ciudadanos):
    antes = Ciudadano.objects.count()
    respuesta = _cliente("exp_ok").get(reverse("ciudadanos_exportar"))
    assert respuesta.status_code == 200
    assert respuesta["Content-Type"].startswith("text/csv")
    assert respuesta["Content-Disposition"].startswith(
        'attachment; filename="exportacion_ciudadanos_'
    )
    filas = _filas(respuesta)
    assert filas[0] == HEADER
    assert filas[1:] == [
        "Alfa;Ana;30111223;;;;",
        "Alfa;Beto;30111224;;;;",
        "Zeta;Zoe;30111222;;;;",
    ]
    # Mirar la exportación no escribe nada.
    assert Ciudadano.objects.count() == antes


def test_aplica_el_filtro_y_el_orden_del_listado(ciudadanos):
    cliente = _cliente("exp_filtro")
    filtrado = _filas(cliente.get(reverse("ciudadanos_exportar"), {"q": "Zeta"}))
    assert filtrado[1:] == ["Zeta;Zoe;30111222;;;;"]
    descendente = _filas(
        cliente.get(
            reverse("ciudadanos_exportar"), {"sort": "apellido", "direction": "desc"}
        )
    )
    assert descendente[1].startswith("Zeta;")


def test_rechazos_no_entregan_el_archivo(ciudadanos):
    url = reverse("ciudadanos_exportar")
    anonimo = Client().get(url)
    assert anonimo.status_code == 302
    assert "login" in anonimo["Location"]
    assert _cliente("exp_sin_ver", ver=False, exportar=True).get(url).status_code == 403
    # Con ver pero sin el permiso de exportar a CSV tampoco hay descarga.
    assert _cliente("exp_sin_csv", ver=True, exportar=False).get(url).status_code == 403
