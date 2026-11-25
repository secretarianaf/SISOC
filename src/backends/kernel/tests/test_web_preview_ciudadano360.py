"""Local React preview entry of Ciudadano 360 (``ciudadanos.web_preview``)."""

import types

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client, override_settings

from ciudadanos.models import Ciudadano
from ciudadanos.web_preview import ciudadanos_preview_patterns
from config.urls_all import urlpatterns as monolith_patterns

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
    module = types.ModuleType("ciudadanos_preview_test_urls")
    module.urlpatterns = ciudadanos_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


def _client(perms=("view_ciudadano",)):
    user = User.objects.create_user(f"prev_c360_{len(perms)}")
    for codename in perms:
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="ciudadanos", codename=codename
            )
        )
    client = Client()
    client.force_login(user)
    return client


def test_native_guards_then_frozen_index(preview):
    ciudadano = Ciudadano.objects.create(nombre="Ana", apellido="Prev", documento=3111)
    url = f"/ciudadanos/ver/{ciudadano.pk}"
    assert Client().get(url).status_code == 302
    assert _client(perms=()).get(url).status_code == 403
    client = _client()
    response = client.get(url)
    assert response.status_code == 200
    assert b"/ciudadanos/react/assets/app-1.js" in response.content
    assert "no-store" in response["Cache-Control"]
    assert client.get("/ciudadanos/ver/999999").status_code == 404
    assert client.get("/ciudadanos/react/assets/app-1.js").status_code == 200
    assert client.get("/ciudadanos/react/assets/x.js").status_code == 404
