"""Local React preview entry of the PAS crossings (``pas.web_preview_cruces``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from config.urls_all import urlpatterns as monolith_patterns
from pas.models import PasCircuitoMensual
from pas.web_preview_cruces import cruces_preview_patterns

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
    module = types.ModuleType("pas_cruces_preview_test_urls")
    module.urlpatterns = cruces_preview_patterns(tmp_path) + list(monolith_patterns)
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
def test_crossings_page_gets_the_frozen_index_after_the_native_rule():
    respuesta = _client("view_paspersona").get("/pas/cruces")

    assert respuesta.status_code == 200
    assert b"/pas/react/assets/app-1.js" in respuesta.content
    assert "csrftoken" in respuesta.cookies
    for client in (Client(), _client("change_paspersona")):
        assert client.get("/pas/cruces").status_code == 403


@pytest.mark.usefixtures("preview")
def test_native_post_routes_stay_native_and_the_get_creates_nothing():
    client = _client("view_paspersona", "change_paspersona")
    client.get("/pas/cruces")
    assert not PasCircuitoMensual.objects.exists()

    sin_permiso = _client("view_paspersona")
    assert sin_permiso.post("/pas/cruces/exportar-sintys").status_code == 403
