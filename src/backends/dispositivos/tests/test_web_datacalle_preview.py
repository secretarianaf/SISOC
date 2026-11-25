"""Local React preview entries of the DataCalle operativos (``datacalle.web_preview``)."""

import datetime
import types

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client, override_settings

from config.urls_all import urlpatterns as monolith_patterns
from core.models import Provincia
from datacalle.models import Relevamiento
from datacalle.web_preview import datacalle_preview_patterns
from users.models import ProfileTerritorialScope

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
NATIVE = "/datacalle/relevamientos/"

pytestmark = pytest.mark.django_db


def _client(username, *codenames, provincia=None):
    user = User.objects.create_user(username)
    if provincia is not None:
        user.profile.es_usuario_provincial = True
        user.profile.save()
        ProfileTerritorialScope.objects.create(
            profile=user.profile, provincia=provincia
        )
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="datacalle", codename__in=codenames
        )
    )
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="relevamiento")
def relevamiento_fixture():
    return Relevamiento.objects.create(
        denominacion="Preview",
        provincia=Provincia.objects.create(nombre="Córdoba"),
        fase=Relevamiento.Fase.ESPACIO_PUBLICO,
        area_operativa="Plaza",
        fecha_inicio=datetime.date(2026, 9, 15),
        fecha_fin=datetime.date(2026, 9, 16),
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
    module = types.ModuleType("datacalle_preview_test_urls")
    module.urlpatterns = datacalle_preview_patterns(build) + list(monolith_patterns)
    return module


def _outcome(client, urlconf, method, url):
    with override_settings(ROOT_URLCONF=urlconf):
        respuesta = getattr(client, method)(url)
    return respuesta.status_code, respuesta.get("Location")


def _pages(relevamiento):
    return [
        NATIVE,
        NATIVE + "crear/",
        f"{NATIVE}{relevamiento.pk}/",
        f"{NATIVE}{relevamiento.pk}/editar/",
        f"{NATIVE}{relevamiento.pk}/eliminar/",
    ]


def test_entries_serve_the_frozen_index_with_rewritten_assets(
    preview_urls, relevamiento
):
    client = _client(
        "todo",
        "view_relevamiento",
        "add_relevamiento",
        "change_relevamiento",
        "delete_relevamiento",
    )
    for url in _pages(relevamiento):
        with override_settings(ROOT_URLCONF=preview_urls):
            respuesta = client.get(url)
            head = client.head(url)

        assert respuesta.status_code == 200, url
        body = respuesta.content.decode()
        assert '/datacalle/react/assets/app-1.js"' in body
        assert "/v2/sisoc/assets/" not in body
        assert "no-store" in respuesta["Cache-Control"]
        assert "private" in respuesta["Cache-Control"]
        assert "Cookie" in respuesta["Vary"]
        assert "csrftoken" in respuesta.cookies
        assert head.content == b""


def test_native_guards_decide_exactly_as_the_native_pages(preview_urls, relevamiento):
    otra = Provincia.objects.create(nombre="Salta")
    anonimo = Client()
    sin_permiso = _client("sin_permiso")
    solo_ver = _client("solo_ver", "view_relevamiento")
    ajeno = _client(
        "ajeno",
        "view_relevamiento",
        "add_relevamiento",
        "change_relevamiento",
        "delete_relevamiento",
        provincia=otra,
    )
    casos = [
        (c, "get", url) for c in (anonimo, sin_permiso) for url in _pages(relevamiento)
    ]
    casos += [
        (solo_ver, "get", url)
        for url in _pages(relevamiento)[1:2] + _pages(relevamiento)[3:]
    ]
    casos += [
        (solo_ver, "get", NATIVE + "?page=9"),
        (ajeno, "get", f"{NATIVE}{relevamiento.pk}/"),
        (ajeno, "get", f"{NATIVE}{relevamiento.pk}/editar/"),
        (ajeno, "get", f"{NATIVE}{relevamiento.pk}/eliminar/"),
        (ajeno, "get", f"{NATIVE}00000000-0000-0000-0000-000000000000/"),
        (ajeno, "post", NATIVE),
        (ajeno, "post", f"{NATIVE}{relevamiento.pk}/"),
    ]
    for client, method, url in casos:
        native = _outcome(client, "config.urls_all", method, url)
        preview = _outcome(client, preview_urls, method, url)
        assert preview == native, (url, method)
        assert native[0] in (403, 404, 405), (url, native)
    assert _outcome(solo_ver, preview_urls, "get", NATIVE)[0] == 200
    assert (
        _outcome(solo_ver, preview_urls, "get", f"{NATIVE}{relevamiento.pk}/")[0] == 200
    )


def test_writes_on_native_urls_stay_native(preview_urls, relevamiento):
    client = _client(
        "todo", "view_relevamiento", "change_relevamiento", "delete_relevamiento"
    )

    with override_settings(ROOT_URLCONF=preview_urls):
        respuesta = client.post(f"{NATIVE}{relevamiento.pk}/eliminar/")

    assert respuesta.status_code == 302
    assert Relevamiento.objects.filter(pk=relevamiento.pk).count() == 0


def test_only_frozen_assets_are_served(client, preview_urls):
    with override_settings(ROOT_URLCONF=preview_urls):
        asset = client.get("/datacalle/react/assets/app-1.js")
        assert asset.status_code == 200
        assert asset.content == b"console.log(1);"
        for url in (
            "/datacalle/react/assets/app-1.js?x=1",
            "/datacalle/react/assets/notes.txt",
            "/datacalle/react/assets/otro.js",
        ):
            assert client.get(url).status_code == 404, url


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        datacalle_preview_patterns(tmp_path)


def test_production_urlconf_keeps_the_native_pages(relevamiento):
    client = _client("prod", "view_relevamiento")
    lista = client.get(NATIVE)
    detalle = client.get(f"{NATIVE}{relevamiento.pk}/")

    assert lista.status_code == detalle.status_code == 200
    assert "dc-filtros" in lista.content.decode()
    assert "/datacalle/react/" not in detalle.content.decode()
