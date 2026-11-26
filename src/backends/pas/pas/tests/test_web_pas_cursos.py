"""Módulo Cursos PAS: pantalla reservada en v1 (``/pas/cursos``) y API web v2."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db

API = "/api/web/pas/cursos/"


def _client(username, *codenames):
    user = get_user_model().objects.create_user(username)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    for codename in codenames:
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="pas", codename=codename)
        )
    client = Client()
    client.force_login(user)
    return client


def test_v1_muestra_la_pantalla_reservada_con_el_fondo_pas():
    viewer = _client("cursos_ve", "view_paspersona")

    respuesta = viewer.get(reverse("pas_cursos"))

    assert respuesta.status_code == 200
    contenido = respuesta.content.decode()
    assert '<main class="pas-workspace"' in contenido
    assert "Cursos PAS" in contenido
    assert "custom/css/pas.css" in contenido


def test_v1_requiere_ver_el_padron():
    sin_permiso = _client("cursos_sin")

    respuesta = sin_permiso.get(reverse("pas_cursos"))

    assert respuesta.status_code in (302, 403)


def test_api_devuelve_el_encabezado_del_modulo():
    viewer = _client("cursos_api", "view_paspersona")

    respuesta = viewer.get(API)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"titulo": "Cursos PAS", "subtitulo": "Administración"}


def test_api_respeta_la_regla_nativa_y_la_sesion():
    assert Client().get(API).status_code == 401
    assert _client("cursos_api_sin").get(API).status_code == 403
