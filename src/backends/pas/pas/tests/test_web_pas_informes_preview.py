"""Local React preview entries of the PAS reports (``pas.web_preview_informes``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from config.urls_all import urlpatterns as monolith_patterns
from pas.models import PasInforme
from pas.web_preview_informes import informes_preview_patterns

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
    module = types.ModuleType("pas_informes_preview_test_urls")
    module.urlpatterns = informes_preview_patterns(tmp_path) + list(monolith_patterns)
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
def test_report_pages_get_the_frozen_index():
    informe = PasInforme.objects.create()
    client = _client("view_paspersona", "view_pasinforme")
    for url in ("/pas/informes", f"/pas/informes/{informe.pk}", "/pas/listar"):
        respuesta = client.get(url)
        assert respuesta.status_code == 200, url
        assert b"/pas/react/assets/app-1.js" in respuesta.content, url
        assert "csrftoken" in respuesta.cookies


@pytest.mark.usefixtures("preview")
def test_native_guards_decide_before_the_index():
    informe = PasInforme.objects.create()
    for client in (Client(), _client("view_paspersona"), _client("view_pasinforme")):
        for url in ("/pas/informes", f"/pas/informes/{informe.pk}"):
            assert client.get(url).status_code == 403, url
    lector = _client("view_paspersona", "view_pasinforme")
    assert lector.get("/pas/informes/999999").status_code == 404
    # The download stays native (it needs the export code, so 403 here).
    assert lector.get(f"/pas/informes/{informe.pk}/descargar").status_code == 403


@pytest.mark.usefixtures("preview")
def test_request_form_gets_the_frozen_index_with_its_own_guards():
    permitido = _client("view_paspersona", "add_pasinforme")
    respuesta = permitido.get("/pas/informes/generar")

    assert respuesta.status_code == 200
    assert b"/pas/react/assets/app-1.js" in respuesta.content
    assert "csrftoken" in respuesta.cookies
    for client in (Client(), _client("view_paspersona"), _client("view_pasinforme")):
        assert client.get("/pas/informes/generar").status_code == 403


@pytest.mark.usefixtures("preview")
def test_request_form_post_and_preview_stay_native():
    client = _client("view_paspersona", "add_pasinforme")

    assert client.post("/pas/informes/generar", {}).content.startswith(b"\xef\xbb\xbf")
    assert client.post("/pas/informes/previsualizar", {}).json()["ok"] is True
    assert PasInforme.objects.count() == 1
