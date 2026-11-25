"""Local React preview entries of the CDF centre screens (``centrodefamilia.web_preview``)."""

import types

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings

from centrodefamilia.models import AccesoCDF, Centro
from centrodefamilia.web_preview import cdf_preview_patterns
from config.urls_all import urlpatterns as monolith_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)

pytestmark = pytest.mark.django_db


def _user(username, *roles, view=True):
    user = User.objects.create_user(username)
    if view:
        user.user_permissions.add(
            Permission.objects.get(
                content_type=ContentType.objects.get_for_model(Centro),
                codename="view_centro",
            )
        )
    for role in roles:
        permission, _ = Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Group),
            codename=role,
            defaults={"name": role},
        )
        user.user_permissions.add(permission)
    return user


def _client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="centro")
def centro_fixture():
    return Centro.objects.create(
        nombre="Centro Preview",
        tipo="faro",
        codigo="PREV-1",
        domicilio_actividad="Domicilio",
        telefono="1",
        celular="2",
        correo="c@example.com",
        nombre_referente="R",
        apellido_referente="E",
        telefono_referente="3",
        correo_referente="r@example.com",
    )


@pytest.fixture(name="sse_client")
def sse_client_fixture():
    return _client(_user("sse_preview", "role_cdf_sse"))


@pytest.fixture(name="build")
def build_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    (tmp_path / "assets" / "notes.txt").write_text("not served", encoding="utf-8")
    return tmp_path


@pytest.fixture(name="preview_urls")
def preview_urls_fixture(build):
    module = types.ModuleType("cdf_preview_test_urls")
    module.urlpatterns = cdf_preview_patterns(build) + list(monolith_patterns)
    return module


def _outcome(client, urlconf, method, url, params=None):
    with override_settings(ROOT_URLCONF=urlconf):
        respuesta = getattr(client, method)(url, params or {})
    return respuesta.status_code, respuesta.get("Location")


def test_entries_serve_the_frozen_index_with_rewritten_assets(
    sse_client, preview_urls, centro
):
    for url, params in (
        ("/centrodefamilia/centros/", {"page": "9"}),
        (f"/centrodefamilia/centros/{centro.pk}/", {"page_act": "x"}),
        ("/centrodefamilia/centros/nuevo/", {"faro": str(centro.pk)}),
        (f"/centrodefamilia/centros/{centro.pk}/editar/", {}),
        (f"/centrodefamilia/centros/{centro.pk}/eliminar/", {}),
    ):
        with override_settings(ROOT_URLCONF=preview_urls):
            respuesta = sse_client.get(url, params)
            head = sse_client.head(url)

        assert respuesta.status_code == 200, url
        body = respuesta.content.decode()
        assert '/centrodefamilia/react/assets/app-1.js"' in body
        assert "/v2/sisoc/assets/" not in body
        assert respuesta["Content-Type"] == "text/html; charset=utf-8"
        assert "no-store" in respuesta["Cache-Control"]
        assert "private" in respuesta["Cache-Control"]
        assert "Cookie" in respuesta["Vary"]
        assert "csrftoken" in respuesta.cookies
        assert head.content == b""


def test_native_guards_decide_exactly_as_the_native_pages(preview_urls, centro):
    otro = Centro.objects.create(
        nombre="Otro",
        tipo="faro",
        codigo="PREV-2",
        domicilio_actividad="D",
        telefono="1",
        celular="2",
        correo="o@example.com",
        nombre_referente="R",
        apellido_referente="E",
        telefono_referente="3",
        correo_referente="r@example.com",
    )
    referente = _user("ref_preview")
    AccesoCDF.objects.create(user=referente, centro=centro, activo=True)
    anonimo = Client()
    sin_permiso = _client(_user("sin_permiso_preview", view=False))
    solo_permiso = _client(_user("solo_permiso_preview"))
    ref = _client(referente)
    casos = [
        (anonimo, "get", "/centrodefamilia/centros/"),
        (anonimo, "get", f"/centrodefamilia/centros/{centro.pk}/"),
        (sin_permiso, "get", "/centrodefamilia/centros/"),
        (sin_permiso, "get", f"/centrodefamilia/centros/{centro.pk}/"),
        (solo_permiso, "get", f"/centrodefamilia/centros/{centro.pk}/"),
        (ref, "get", f"/centrodefamilia/centros/{otro.pk}/"),
        (ref, "get", "/centrodefamilia/centros/999999/"),
        (ref, "post", "/centrodefamilia/centros/"),
        (ref, "post", f"/centrodefamilia/centros/{centro.pk}/"),
        (anonimo, "get", "/centrodefamilia/centros/nuevo/"),
        (sin_permiso, "get", "/centrodefamilia/centros/nuevo/"),
        (ref, "get", f"/centrodefamilia/centros/{centro.pk}/editar/"),
        (ref, "get", f"/centrodefamilia/centros/{centro.pk}/eliminar/"),
        (ref, "post", f"/centrodefamilia/centros/{centro.pk}/eliminar/"),
        (solo_permiso, "get", "/centrodefamilia/centros/999999/editar/"),
        (sin_permiso, "post", f"/centrodefamilia/centros/{centro.pk}/eliminar/"),
    ]
    for client, method, url in casos:
        native = _outcome(client, "config.urls_all", method, url)
        preview = _outcome(client, preview_urls, method, url)
        assert preview == native, (url, method)
        assert native[0] in (403, 404, 405), (url, native)
    assert (
        _outcome(ref, preview_urls, "get", f"/centrodefamilia/centros/{centro.pk}/")[0]
        == 200
    )


def test_only_frozen_assets_are_served(client, preview_urls):
    with override_settings(ROOT_URLCONF=preview_urls):
        asset = client.get("/centrodefamilia/react/assets/app-1.js")
        assert asset.status_code == 200
        assert asset.content == b"console.log(1);"
        assert asset["Cache-Control"] == "public, max-age=31536000, immutable"
        assert asset["X-Content-Type-Options"] == "nosniff"
        for url in (
            "/centrodefamilia/react/assets/app-1.js?x=1",
            "/centrodefamilia/react/assets/notes.txt",
            "/centrodefamilia/react/assets/otro.js",
        ):
            assert client.get(url).status_code == 404, url
        assert client.post("/centrodefamilia/react/assets/app-1.js").status_code == 405


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        cdf_preview_patterns(tmp_path)


def test_production_urlconf_keeps_the_native_pages(sse_client, centro):
    lista = sse_client.get("/centrodefamilia/centros/")
    detalle = sse_client.get(f"/centrodefamilia/centros/{centro.pk}/")

    assert lista.status_code == detalle.status_code == 200
    assert "centros-table-body" in lista.content.decode()
    assert "cdf-hero" in detalle.content.decode()
    assert "/centrodefamilia/react/" not in lista.content.decode()
