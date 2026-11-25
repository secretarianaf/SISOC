"""Local React preview entries of the Dispositivos screens (``dispositivos.web_preview``)."""

import types

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client, override_settings

from config.urls_all import urlpatterns as monolith_patterns
from core.models import Municipio, Provincia
from dispositivos.models import Dispositivo
from dispositivos.web_preview import dispositivos_preview_patterns
from users.models import ProfileTerritorialScope

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)

pytestmark = pytest.mark.django_db


def _client(username, *perms, provincia=None):
    user = User.objects.create_user(username)
    if provincia is not None:
        user.profile.es_usuario_provincial = True
        user.profile.save()
        ProfileTerritorialScope.objects.create(
            profile=user.profile, provincia=provincia
        )
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="dispositivos", codename__in=perms
        )
    )
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="dispositivo")
def dispositivo_fixture():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)
    return Dispositivo.objects.create(
        nombre_institucion="Dispositivo Preview",
        tipo_gestion="estatal",
        cuit_institucion="20123456789",
        provincia=provincia,
        municipio=municipio,
        calle="Calle",
        altura="1",
        telefono_prefijo="221",
        telefono_numero="1",
        responsable_nombre_completo="Ana",
        responsable_dni="12345678",
        tipo_dispositivo="refugio",
        modalidad_funcionamiento="permanente",
        capacidad_total_plazas="0_15",
    )


@pytest.fixture(name="build")
def build_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    (tmp_path / "assets" / "notes.txt").write_text("not served", encoding="utf-8")
    return tmp_path


@pytest.fixture(name="preview_urls")
def preview_urls_fixture(build):
    module = types.ModuleType("dispositivos_preview_test_urls")
    module.urlpatterns = dispositivos_preview_patterns(build) + list(monolith_patterns)
    return module


def _outcome(client, urlconf, method, url, params=None):
    with override_settings(ROOT_URLCONF=urlconf):
        respuesta = getattr(client, method)(url, params or {})
    return respuesta.status_code, respuesta.get("Location")


def test_entries_serve_the_frozen_index_with_rewritten_assets(
    preview_urls, dispositivo
):
    client = _client("todo", "view_dispositivo", "ver_mapa_dispositivo")
    for url, params in (
        ("/dispositivos/", {"page": "1", "busqueda": "x"}),
        ("/dispositivos/mapa/", {"dispositivo": str(dispositivo.pk)}),
        (f"/dispositivos/{dispositivo.pk}/", {}),
    ):
        with override_settings(ROOT_URLCONF=preview_urls):
            respuesta = client.get(url, params)
            head = client.head(url)

        assert respuesta.status_code == 200, url
        body = respuesta.content.decode()
        assert '/dispositivos/react/assets/app-1.js"' in body
        assert "/v2/sisoc/assets/" not in body
        assert respuesta["Content-Type"] == "text/html; charset=utf-8"
        assert "no-store" in respuesta["Cache-Control"]
        assert "private" in respuesta["Cache-Control"]
        assert "Cookie" in respuesta["Vary"]
        assert "csrftoken" in respuesta.cookies
        assert head.content == b""


def test_native_guards_decide_exactly_as_the_native_pages(preview_urls, dispositivo):
    otra = Provincia.objects.create(nombre="Cordoba")
    anonimo = Client()
    sin_permiso = _client("sin_permiso")
    solo_ver = _client("solo_ver", "view_dispositivo")
    ajeno = _client("ajeno", "view_dispositivo", "ver_mapa_dispositivo", provincia=otra)
    casos = [
        (anonimo, "get", "/dispositivos/"),
        (anonimo, "get", "/dispositivos/mapa/"),
        (anonimo, "get", f"/dispositivos/{dispositivo.pk}/"),
        (sin_permiso, "get", "/dispositivos/"),
        (sin_permiso, "get", f"/dispositivos/{dispositivo.pk}/"),
        (solo_ver, "get", "/dispositivos/mapa/"),
        (solo_ver, "get", "/dispositivos/?page=9"),
        (ajeno, "get", f"/dispositivos/{dispositivo.pk}/"),
        (ajeno, "get", "/dispositivos/999999/"),
        (ajeno, "post", "/dispositivos/"),
        (ajeno, "post", "/dispositivos/mapa/"),
        (ajeno, "post", f"/dispositivos/{dispositivo.pk}/"),
    ]
    for client, method, url in casos:
        path, _, query = url.partition("?")
        params = dict([query.split("=")]) if query else None
        native = _outcome(client, "config.urls_all", method, path, params)
        preview = _outcome(client, preview_urls, method, path, params)
        assert preview == native, (url, method)
        assert native[0] in (403, 404, 405), (url, native)
    assert _outcome(solo_ver, preview_urls, "get", "/dispositivos/")[0] == 200


def test_only_frozen_assets_are_served(client, preview_urls):
    with override_settings(ROOT_URLCONF=preview_urls):
        asset = client.get("/dispositivos/react/assets/app-1.js")
        assert asset.status_code == 200
        assert asset.content == b"console.log(1);"
        assert asset["Cache-Control"] == "public, max-age=31536000, immutable"
        for url in (
            "/dispositivos/react/assets/app-1.js?x=1",
            "/dispositivos/react/assets/notes.txt",
            "/dispositivos/react/assets/otro.js",
        ):
            assert client.get(url).status_code == 404, url


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        dispositivos_preview_patterns(tmp_path)


def test_production_urlconf_keeps_the_native_pages(dispositivo):
    client = _client("prod", "view_dispositivo", "ver_mapa_dispositivo")
    lista = client.get("/dispositivos/")
    detalle = client.get(f"/dispositivos/{dispositivo.pk}/")
    mapa = client.get("/dispositivos/mapa/")

    assert lista.status_code == detalle.status_code == mapa.status_code == 200
    assert "table-comedor-moderno" in lista.content.decode()
    assert "accordion-horizontal" in detalle.content.decode()
    assert "dispositivos-map" in mapa.content.decode()
    assert "/dispositivos/react/" not in lista.content.decode()
