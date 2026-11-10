"""Local React preview entries of CDI screens (``centrodeinfancia.web_preview``)."""

import types

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings

from centrodeinfancia.web_preview import cdi_preview_patterns
from config.urls_all import urlpatterns as monolith_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
REPORTES = "/centrodeinfancia/reportes/"

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
    module = types.ModuleType("cdi_preview_test_urls")
    module.urlpatterns = cdi_preview_patterns(build) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


def _cliente(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="reportes")
def reportes_fixture():
    user = User.objects.create_user("preview-reportes")
    permiso, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Group),
        codename="role_reportes_cdi",
        defaults={"name": "Reportes CDI"},
    )
    user.user_permissions.add(permiso)
    return _cliente(user)


@pytest.mark.usefixtures("preview")
def test_reports_entry_returns_the_frozen_index_with_rewritten_assets(reportes):
    respuesta = reportes.get(REPORTES, {"provincia": "1"})

    assert respuesta.status_code == 200
    body = respuesta.content.decode()
    assert '/centrodeinfancia/react/assets/app-1.js"' in body
    assert "/v2/sisoc/assets/" not in body
    assert respuesta["Content-Type"] == "text/html; charset=utf-8"
    assert "no-store" in respuesta["Cache-Control"]
    assert "private" in respuesta["Cache-Control"]
    assert "Cookie" in respuesta["Vary"]
    assert "csrftoken" in respuesta.cookies
    assert reportes.head(REPORTES).content == b""


@pytest.mark.usefixtures("preview")
def test_reports_entry_keeps_the_native_guards():
    native = Client().get(REPORTES)
    with override_settings(ROOT_URLCONF="config.urls_all"):
        expected = Client().get(REPORTES)
    assert native.status_code == expected.status_code
    assert native.get("Location") == expected.get("Location")

    sin_permiso = _cliente(User.objects.create_user("preview-sin-reportes"))
    assert sin_permiso.get(REPORTES).status_code == 403


@pytest.mark.usefixtures("preview")
def test_only_frozen_assets_are_served(client):
    asset = client.get("/centrodeinfancia/react/assets/app-1.js")

    assert asset.status_code == 200
    assert asset.content == b"console.log(1);"
    assert asset["Cache-Control"] == "public, max-age=31536000, immutable"
    assert asset["X-Content-Type-Options"] == "nosniff"
    assert client.get("/centrodeinfancia/react/assets/app-1.js?x=1").status_code == 404
    assert client.get("/centrodeinfancia/react/assets/notes.txt").status_code == 404
    assert client.get("/centrodeinfancia/react/assets/otro.js").status_code == 404
    assert client.post("/centrodeinfancia/react/assets/app-1.js").status_code == 405


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        cdi_preview_patterns(tmp_path)


def test_production_urlconf_keeps_the_native_page(reportes):
    respuesta = reportes.get(REPORTES)

    assert respuesta.status_code == 200
    assert "centrodeinfancia/reportes.html" in [t.name for t in respuesta.templates]
