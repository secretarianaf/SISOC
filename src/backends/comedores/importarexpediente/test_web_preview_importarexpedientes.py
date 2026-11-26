"""Local React preview entries of EX02 (``importarexpediente.web_preview_importarexpedientes``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings

from config.urls_all import urlpatterns as monolith_patterns
from importarexpediente.models import ArchivosImportados
from importarexpediente.web_preview_importarexpedientes import (
    importarexpedientes_preview_patterns,
)

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
BASE = "/importarexpedientes/"

pytestmark = pytest.mark.django_db


@pytest.fixture(name="build")
def build_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    return tmp_path


@pytest.fixture(name="preview")
def preview_fixture(build):
    module = types.ModuleType("importarexpedientes_preview_test_urls")
    module.urlpatterns = importarexpedientes_preview_patterns(build) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


def _login(nombre, *codenames):
    usuario = get_user_model().objects.create_user(nombre)
    for codename in codenames:
        usuario.user_permissions.add(Permission.objects.get(codename=codename))
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="lote")
def lote_fixture(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    usuario = get_user_model().objects.create_user("duenio_prev_lotes")
    return ArchivosImportados.objects.create(
        archivo=SimpleUploadedFile("p.csv", b"ID\n1\n"), usuario=usuario
    )


@pytest.mark.usefixtures("preview")
def test_every_page_gets_the_frozen_index(lote):
    client = _login(
        "lector_prev_lotes", "view_archivosimportados", "change_archivosimportados"
    )
    for url in (
        f"{BASE}listar",
        f"{BASE}{lote.pk}/",
        f"{BASE}upload",
        f"{BASE}{lote.pk}/fechas-acreditacion/",
    ):
        respuesta = client.get(url)
        assert respuesta.status_code == 200, url
        assert (
            '/importarexpedientes/react/assets/app-1.js"' in respuesta.content.decode()
        )
        assert "no-store" in respuesta["Cache-Control"]
        assert "csrftoken" in respuesta.cookies
    assert client.get("/importarexpedientes/react/assets/app-1.js").content == (
        b"console.log(1);"
    )


@pytest.mark.usefixtures("preview")
def test_native_guards_decide_first(lote):
    anonimo = Client()
    assert anonimo.get(f"{BASE}listar").status_code == 403
    assert anonimo.get(f"{BASE}{lote.pk}/").status_code == 403
    assert anonimo.get(f"{BASE}{lote.pk}/fechas-acreditacion/").status_code == 403
    assert anonimo.get(f"{BASE}upload").status_code == 302
    sin_codigos = _login("sin_codigos_prev_lotes")
    assert sin_codigos.get(f"{BASE}upload").status_code == 200
    for url in (
        f"{BASE}listar",
        f"{BASE}{lote.pk}/",
        f"{BASE}{lote.pk}/fechas-acreditacion/",
    ):
        assert sin_codigos.get(url).status_code == 403, url
    lector = _login("lector2_prev_lotes", "view_archivosimportados")
    assert lector.get(f"{BASE}listar", {"page": "9"}).status_code == 404
    assert lector.get(f"{BASE}999999/").status_code == 404
    assert lector.get(f"{BASE}{lote.pk}/", {"page": "9"}).status_code == 404


@pytest.mark.usefixtures("preview")
def test_posts_still_reach_the_native_views(lote):
    client = _login("sesion_prev_lotes")
    respuesta = client.post(f"{BASE}upload", {"delimiter": ";"})
    assert respuesta.status_code == 302
    assert respuesta["Location"] == "/importarexpedientes/upload"
    assert client.get(f"{BASE}{lote.pk}/importar_datos/").status_code == 405


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        importarexpedientes_preview_patterns(tmp_path)
