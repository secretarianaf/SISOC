"""Local React preview entries of the Dispositivos create and edit screens."""

import types

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client, override_settings

from config.urls_all import urlpatterns as monolith_patterns
from core.models import Municipio, Provincia
from dispositivos.models import Dispositivo
from dispositivos.web_preview import dispositivos_preview_patterns
from dispositivos.web_preview_dispositivo_form import (
    dispositivo_form_preview_patterns,
)
from users.models import ProfileTerritorialScope

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)

pytestmark = pytest.mark.django_db


def _client(username, *perms, provincia=None):
    user = User.objects.create_user(username)
    if provincia is not None:
        user.profile.es_usuario_provincial = True
        user.profile.save()
        ProfileTerritorialScope.objects.create(
            profile=user.profile, provincia=provincia
        )
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="dispositivos", codename__in=perms
        )
    )
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="dispositivo")
def dispositivo_fixture():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)
    return Dispositivo.objects.create(
        nombre_institucion="Dispositivo Form Preview",
        tipo_gestion="estatal",
        cuit_institucion="20123456789",
        provincia=provincia,
        municipio=municipio,
        calle="Calle",
        altura="1",
        telefono_prefijo="221",
        telefono_numero="1",
        responsable_nombre_completo="Ana",
        responsable_dni="12345678",
        tipo_dispositivo="refugio",
        modalidad_funcionamiento="permanente",
        capacidad_total_plazas="0_15",
    )


@pytest.fixture(name="preview_urls")
def preview_urls_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    module = types.ModuleType("dispositivos_form_preview_test_urls")
    module.urlpatterns = (
        dispositivo_form_preview_patterns(tmp_path)
        + dispositivos_preview_patterns(tmp_path)
        + list(monolith_patterns)
    )
    return module


def _outcome(client, urlconf, method, url):
    with override_settings(ROOT_URLCONF=urlconf):
        respuesta = getattr(client, method)(url)
    return respuesta.status_code, respuesta.get("Location")


def test_entries_serve_the_frozen_index(preview_urls, dispositivo):
    client = _client("todo", "add_dispositivo", "change_dispositivo")
    for url in ("/dispositivos/crear", f"/dispositivos/{dispositivo.pk}/editar"):
        with override_settings(ROOT_URLCONF=preview_urls):
            respuesta = client.get(url)

        assert respuesta.status_code == 200, url
        assert '/dispositivos/react/assets/app-1.js"' in respuesta.content.decode()
        assert "no-store" in respuesta["Cache-Control"]
        assert "csrftoken" in respuesta.cookies


def test_native_guards_decide_exactly_as_the_native_pages(preview_urls, dispositivo):
    otra = Provincia.objects.create(nombre="Cordoba")
    anonimo = Client()
    sin_permiso = _client("sin_permiso")
    solo_alta = _client("solo_alta", "add_dispositivo")
    ajeno = _client("ajeno", "change_dispositivo", provincia=otra)
    casos = [
        (anonimo, "get", "/dispositivos/crear"),
        (sin_permiso, "get", "/dispositivos/crear"),
        (solo_alta, "get", f"/dispositivos/{dispositivo.pk}/editar"),
        (ajeno, "get", f"/dispositivos/{dispositivo.pk}/editar"),
        (ajeno, "get", "/dispositivos/999999/editar"),
        (ajeno, "post", f"/dispositivos/{dispositivo.pk}/editar"),
    ]
    for client, method, url in casos:
        native = _outcome(client, "config.urls_all", method, url)
        preview = _outcome(client, preview_urls, method, url)
        assert preview == native, (url, method)
        assert native[0] in (302, 403, 404), (url, native)
