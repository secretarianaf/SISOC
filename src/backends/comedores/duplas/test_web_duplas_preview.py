"""Local React preview entries of the Duplas screens (``duplas.web_preview``)."""

import types

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings

from config.urls_all import urlpatterns as monolith_patterns
from duplas.models import Dupla
from duplas.web_preview import duplas_preview_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)

pytestmark = pytest.mark.django_db


def _admin(username="admin_preview"):
    user = User.objects.create_user(username)
    permission, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Group),
        codename="role_admin",
        defaults={"name": "Admin"},
    )
    user.user_permissions.add(permission)
    return user


@pytest.fixture(name="dupla")
def dupla_fixture():
    abogado = User.objects.create_user("abogado_preview")
    return Dupla.objects.create(
        nombre="Equipo Preview", estado="Activo", abogado=abogado
    )


@pytest.fixture(name="admin_client")
def admin_client_fixture():
    client = Client()
    client.force_login(_admin())
    return client


@pytest.fixture(name="build")
def build_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    (tmp_path / "assets" / "notes.txt").write_text("not served", encoding="utf-8")
    return tmp_path


@pytest.fixture(name="preview_urls")
def preview_urls_fixture(build):
    module = types.ModuleType("duplas_preview_test_urls")
    module.urlpatterns = duplas_preview_patterns(build) + list(monolith_patterns)
    return module


def _outcome(client, urlconf, method, url, params=None):
    with override_settings(ROOT_URLCONF=urlconf):
        respuesta = getattr(client, method)(url, params or {})
    return respuesta.status_code, respuesta.get("Location")


def test_admin_gets_the_frozen_index_with_rewritten_assets(
    admin_client, preview_urls, dupla
):
    for url in ("/equipo-tecnico/", f"/equipo-tecnico/{dupla.pk}/"):
        with override_settings(ROOT_URLCONF=preview_urls):
            respuesta = admin_client.get(
                url, {"page": "1"} if url.endswith("o/") else {}
            )
            head = admin_client.head(url)

        assert respuesta.status_code == 200, url
        body = respuesta.content.decode()
        assert '/equipo-tecnico/react/assets/app-1.js"' in body
        assert "/v2/sisoc/assets/" not in body
        assert respuesta["Content-Type"] == "text/html; charset=utf-8"
        assert "no-store" in respuesta["Cache-Control"]
        assert "private" in respuesta["Cache-Control"]
        assert "Cookie" in respuesta["Vary"]
        assert "csrftoken" in respuesta.cookies
        assert head.content == b""


def test_native_guards_decide_exactly_as_the_native_pages(
    admin_client, preview_urls, dupla
):
    anonimo = Client()
    sin_rol = Client()
    sin_rol.force_login(User.objects.create_user("sin_rol_preview"))
    casos = [
        (anonimo, "get", "/equipo-tecnico/", None),
        (anonimo, "get", f"/equipo-tecnico/{dupla.pk}/", None),
        (sin_rol, "get", "/equipo-tecnico/", None),
        (sin_rol, "get", f"/equipo-tecnico/{dupla.pk}/", None),
        (admin_client, "get", "/equipo-tecnico/", {"page": "9"}),
        (admin_client, "get", "/equipo-tecnico/999999/", None),
    ]
    for client, method, url, params in casos:
        native = _outcome(client, "config.urls_all", method, url, params)
        preview = _outcome(client, preview_urls, method, url, params)
        assert preview == native, (url, params)
        assert native[0] in (302, 403, 404), (url, native)


def test_only_frozen_assets_are_served(client, preview_urls):
    with override_settings(ROOT_URLCONF=preview_urls):
        asset = client.get("/equipo-tecnico/react/assets/app-1.js")
        assert asset.status_code == 200
        assert asset.content == b"console.log(1);"
        assert asset["Cache-Control"] == "public, max-age=31536000, immutable"
        assert asset["X-Content-Type-Options"] == "nosniff"
        for url in (
            "/equipo-tecnico/react/assets/app-1.js?x=1",
            "/equipo-tecnico/react/assets/notes.txt",
            "/equipo-tecnico/react/assets/otro.js",
        ):
            assert client.get(url).status_code == 404, url
        assert client.post("/equipo-tecnico/react/assets/app-1.js").status_code == 405


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        duplas_preview_patterns(tmp_path)


def test_production_urlconf_keeps_the_native_pages(admin_client, dupla):
    lista = admin_client.get("/equipo-tecnico/")
    detalle = admin_client.get(f"/equipo-tecnico/{dupla.pk}/")

    assert "dupla_list.html" in [t.name for t in lista.templates]
    assert "dupla_detail.html" in [t.name for t in detalle.templates]
