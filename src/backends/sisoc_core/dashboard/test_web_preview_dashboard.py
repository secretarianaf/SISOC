"""Local React preview entries of the dashboards (``dashboard.web_preview_dashboard``)."""

import types

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client, override_settings

from config.urls_all import urlpatterns as monolith_patterns
from dashboard.models import Tablero
from dashboard.web_preview_dashboard import dashboard_preview_patterns

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
    module = types.ModuleType("dashboard_preview_test_urls")
    module.urlpatterns = dashboard_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


def _client(username, *permisos):
    user = User.objects.create_user(username)
    for codigo in permisos:
        app, codename = codigo.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    client = Client()
    client.force_login(user)
    return client


def test_dashboard_keeps_the_native_login_then_frozen_index(preview):
    assert Client().get("/dashboard/centro-de-familia").status_code == 302
    response = _client("prev_dash").get("/dashboard/centro-de-familia")
    assert response.status_code == 200
    assert "/ciudadanos/react/assets/app-1.js" in response.content.decode()
    assert "no-store" in response["Cache-Control"]


def test_board_keeps_native_guards_redirect_and_404(preview):
    Tablero.objects.create(
        nombre="Prev", slug="prev", permisos=["dashboard.view_dashboard"]
    )
    Tablero.objects.create(
        nombre="Propio",
        slug="propio",
        ruta_interna="/celiaquia/tablero/",
        permisos=["dashboard.view_dashboard"],
    )
    assert Client().get("/dashboard/prev/").status_code == 302
    assert _client("prev_sin").get("/dashboard/prev/").status_code == 403
    viewer = _client("prev_ve", "dashboard.view_dashboard")
    response = viewer.get("/dashboard/prev/")
    assert response.status_code == 200
    assert "/ciudadanos/react/assets/app-1.js" in response.content.decode()
    assert viewer.get("/dashboard/nada/").status_code == 404
    redirected = viewer.get("/dashboard/propio/")
    assert redirected.status_code == 302
    assert redirected["Location"] == "/celiaquia/tablero/"
