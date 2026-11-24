"""Local React preview entry of the Actas tab (``inspecciones.web_preview``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings

from config.urls_all import urlpatterns as monolith_patterns
from inspecciones.web_preview import actas_preview_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)

pytestmark = pytest.mark.django_db


@pytest.fixture(name="build")
def build_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    (tmp_path / "assets" / "notes.txt").write_text("not served", encoding="utf-8")
    return tmp_path


@pytest.fixture(name="preview")
def preview_fixture(build):
    module = types.ModuleType("actas_preview_test_urls")
    module.urlpatterns = actas_preview_patterns(build) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_manager_gets_the_frozen_index_with_rewritten_assets(panel):
    respuesta = panel.get("/inspecciones/actas/", {"numero": "1"})

    assert respuesta.status_code == 200
    body = respuesta.content.decode()
    assert '/inspecciones/react/assets/app-1.js"' in body
    assert "/v2/sisoc/assets/" not in body
    assert respuesta["Content-Type"] == "text/html; charset=utf-8"
    assert "no-store" in respuesta["Cache-Control"]
    assert "private" in respuesta["Cache-Control"]
    assert "Cookie" in respuesta["Vary"]
    assert "csrftoken" in respuesta.cookies
    assert panel.head("/inspecciones/actas/").content == b""


@pytest.mark.usefixtures("preview")
def test_native_guards_still_decide_before_the_index(panel, inspector_a):
    client = Client()
    anonimo = client.get("/inspecciones/actas/")
    assert anonimo.status_code == 302
    assert anonimo["Location"].startswith("/login")

    for usuario in (inspector_a, get_user_model().objects.create_user("otro")):
        client.force_login(usuario)
        assert client.get("/inspecciones/actas/").status_code == 403

    assert panel.get("/inspecciones/actas/", {"page": "9"}).status_code == 404
    assert panel.post("/inspecciones/actas/").status_code == 405


@pytest.mark.usefixtures("preview")
def test_only_frozen_assets_are_served(client):
    asset = client.get("/inspecciones/react/assets/app-1.js")

    assert asset.status_code == 200
    assert asset.content == b"console.log(1);"
    assert asset["Cache-Control"] == "public, max-age=31536000, immutable"
    assert asset["X-Content-Type-Options"] == "nosniff"
    assert client.get("/inspecciones/react/assets/app-1.js?x=1").status_code == 404
    assert client.get("/inspecciones/react/assets/notes.txt").status_code == 404
    assert client.get("/inspecciones/react/assets/otro.js").status_code == 404
    assert client.post("/inspecciones/react/assets/app-1.js").status_code == 405


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        actas_preview_patterns(tmp_path)


def test_production_urlconf_keeps_the_native_page(panel):
    respuesta = panel.get("/inspecciones/actas/")

    assert respuesta.status_code == 200
    assert "inspecciones/actas.html" in [t.name for t in respuesta.templates]
