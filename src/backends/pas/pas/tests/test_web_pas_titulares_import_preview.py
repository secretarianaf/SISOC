"""Local React preview entry of the PAS titulares import (``pas.web_preview_titulares_import``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings

from config.urls_all import urlpatterns as monolith_patterns
from pas.models import PasPersona
from pas.web_preview_titulares_import import titulares_import_preview_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)

pytestmark = pytest.mark.django_db


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("pas_titulares_import_preview_test_urls")
    module.urlpatterns = titulares_import_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


def _client(*codenames):
    user = get_user_model().objects.create_user("_".join(codenames) or "nadie")
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="pas", codename__in=codenames
        )
    )
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.usefixtures("preview")
def test_import_page_gets_the_frozen_index_after_the_native_rule():
    respuesta = _client("add_paspersona").get("/pas/titulares/importar")

    assert respuesta.status_code == 200
    assert b"/pas/react/assets/app-1.js" in respuesta.content
    assert "csrftoken" in respuesta.cookies
    for client in (Client(), _client("view_paspersona")):
        assert client.get("/pas/titulares/importar").status_code == 403


@pytest.mark.usefixtures("preview")
def test_native_post_stays_native_and_the_get_creates_nothing():
    client = _client("add_paspersona")
    client.get("/pas/titulares/importar")
    assert not PasPersona.objects.exists()

    archivo = SimpleUploadedFile("t.csv", b"Apellidos;Nombres\nX;Y\n")
    respuesta = client.post("/pas/titulares/importar", {"archivo": archivo})
    assert respuesta.status_code == 200
    assert b"Faltan columnas obligatorias" in respuesta.content
    assert b"app-1.js" not in respuesta.content
