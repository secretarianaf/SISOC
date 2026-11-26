"""React delete confirmation of a Dispositivo on its canonical URL (#2785, T5d).

``/dispositivos/<pk>/eliminar`` keeps the native guard (ANY
``delete_dispositivo``) and the native object rule (territorial scope 404).
Only the GET returns the frozen React ``index.html``; the confirmed POST still
reaches ``DispositivoDeleteView``. The screen reads its data from
``GET /api/web/dispositivos/<pk>/eliminar/`` under the same guard and scope.
"""

import types
import uuid
from contextlib import contextmanager
from importlib import import_module, reload

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.messages import get_messages
from django.test import Client, override_settings
from django.urls import clear_url_caches, set_urlconf

from config.backends import load_backends_registry
from config.urls_all import urlpatterns as monolith_patterns
from core.models import Municipio, Provincia
from dispositivos.models import Dispositivo
from dispositivos.web_preview import dispositivos_preview_patterns
from users.models import ProfileTerritorialScope

MARK = '<div id="root-dispositivo-eliminar"></div>'
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    f"<body>{MARK}</body></html>"
)
API = "/api/web/dispositivos/{}/eliminar/"

pytestmark = pytest.mark.django_db


def _client(*perms, provincia=None):
    user = User.objects.create_user(f"u{uuid.uuid4().hex[:8]}")
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    if provincia is not None:
        profile.es_usuario_provincial = True
    profile.save()
    if provincia is not None:
        ProfileTerritorialScope.objects.create(profile=profile, provincia=provincia)
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="dispositivos", codename__in=perms
        )
    )
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="geo")
def geo_fixture():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    return {
        "provincia": provincia,
        "municipio": Municipio.objects.create(nombre="La Plata", provincia=provincia),
        "otra": Provincia.objects.create(nombre="Cordoba"),
    }


@pytest.fixture(name="dispositivo")
def dispositivo_fixture(geo):
    return Dispositivo.objects.create(
        nombre_institucion="Refugio a eliminar",
        tipo_gestion="estatal",
        cuit_institucion="20123456789",
        provincia=geo["provincia"],
        municipio=geo["municipio"],
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
    return tmp_path


@pytest.fixture(name="preview_urls")
def preview_urls_fixture(build):
    module = types.ModuleType("dispositivos_eliminar_preview_test_urls")
    module.urlpatterns = dispositivos_preview_patterns(build) + list(monolith_patterns)
    return module


def _outcome(client, urlconf, method, url):
    with override_settings(ROOT_URLCONF=urlconf):
        respuesta = getattr(client, method)(url)
    return respuesta.status_code, respuesta.get("Location")


# --- Canonical entry -----------------------------------------------------------


def test_get_serves_the_frozen_index_to_an_authorized_user(preview_urls, dispositivo):
    client = _client("delete_dispositivo")
    url = f"/dispositivos/{dispositivo.pk}/eliminar"
    with override_settings(ROOT_URLCONF=preview_urls):
        respuesta = client.get(url)
        head = client.head(url)

    assert respuesta.status_code == 200
    body = respuesta.content.decode()
    assert MARK in body
    assert '/dispositivos/react/assets/app-1.js"' in body
    assert "Refugio a eliminar" not in body
    assert "no-store" in respuesta["Cache-Control"]
    assert "csrftoken" in respuesta.cookies
    assert head.status_code == 200
    assert head.content == b""


def test_denials_are_the_native_ones_and_carry_no_data(preview_urls, dispositivo, geo):
    url = f"/dispositivos/{dispositivo.pk}/eliminar"
    casos = [
        (Client(), url),
        (_client(), url),
        (_client("view_dispositivo", "change_dispositivo"), url),
        (_client("delete_dispositivo", provincia=geo["otra"]), url),
        (_client("delete_dispositivo"), "/dispositivos/999999/eliminar"),
    ]
    for client, target in casos:
        native = _outcome(client, "config.urls_all", "get", target)
        preview = _outcome(client, preview_urls, "get", target)
        assert preview == native, target
        assert native[0] in (302, 403, 404), (target, native)
        with override_settings(ROOT_URLCONF=preview_urls):
            body = client.get(target).content.decode()
        assert MARK not in body
        assert "Refugio a eliminar" not in body
    assert Dispositivo.objects.filter(pk=dispositivo.pk).exists()


def test_confirmed_post_still_deletes_through_the_native_view(
    preview_urls, dispositivo
):
    client = _client("delete_dispositivo")
    with override_settings(ROOT_URLCONF=preview_urls):
        respuesta = client.post(f"/dispositivos/{dispositivo.pk}/eliminar")

    assert respuesta.status_code == 302
    assert respuesta["Location"] == "/dispositivos/"
    assert not Dispositivo.objects.filter(pk=dispositivo.pk).exists()
    assert [str(m) for m in get_messages(respuesta.wsgi_request)] == [
        "Dispositivo eliminado correctamente."
    ]


def test_post_without_permission_deletes_nothing(preview_urls, dispositivo, geo):
    for client in (
        _client("view_dispositivo"),
        _client("delete_dispositivo", provincia=geo["otra"]),
    ):
        native = _outcome(
            client,
            "config.urls_all",
            "post",
            f"/dispositivos/{dispositivo.pk}/eliminar",
        )
        preview = _outcome(
            client, preview_urls, "post", f"/dispositivos/{dispositivo.pk}/eliminar"
        )
        assert preview == native
        assert native[0] in (403, 404)
    assert Dispositivo.objects.filter(pk=dispositivo.pk).exists()


# --- Screen data -----------------------------------------------------------------


def test_screen_data_projects_the_native_confirmation(dispositivo):
    client = _client("delete_dispositivo")
    respuesta = client.get(API.format(dispositivo.pk))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id": dispositivo.pk,
        "nombre_institucion": "Refugio a eliminar",
        "cancel_url": f"/dispositivos/{dispositivo.pk}/",
        "messages": [],
    }


def test_screen_data_keeps_the_native_guard_and_scope(dispositivo, geo):
    url = API.format(dispositivo.pk)
    for client, status in (
        (_client("view_dispositivo", "change_dispositivo"), 403),
        (_client("delete_dispositivo", provincia=geo["otra"]), 404),
    ):
        respuesta = client.get(url)
        assert respuesta.status_code == status
        assert "Refugio a eliminar" not in respuesta.content.decode()
    assert _client("delete_dispositivo").get(API.format(999999)).status_code == 404
    assert Client().get(url).status_code in (401, 403)


def test_screen_data_is_read_only(dispositivo):
    client = _client("delete_dispositivo")
    for metodo in ("post", "put", "patch", "delete"):
        respuesta = getattr(client, metodo)(API.format(dispositivo.pk))
        assert respuesta.status_code == 405, metodo
    assert Dispositivo.objects.filter(pk=dispositivo.pk).exists()


# --- Activation flag ------------------------------------------------------------

MODULES = [f"{v}_runtime.urls" for v in load_backends_registry()] + [
    "config.urls",
    "config.urls_all",
]


def _reload():
    for nombre in MODULES:
        reload(import_module(nombre))
    clear_url_caches()
    set_urlconf(None)


@contextmanager
def _flag(activas, build):
    with override_settings(
        REACT_VERTICALES_ACTIVAS=frozenset(activas),
        SISOC_REACT_BUILD_DIR=str(build),
        SISOC_REACT_PAS_BUILD_DIR=str(build),
        ROOT_URLCONF="config.urls_all",
    ):
        _reload()
        yield
    _reload()


def test_flag_on_serves_react_and_flag_off_keeps_the_native_page(build, dispositivo):
    url = f"/dispositivos/{dispositivo.pk}/eliminar"
    with _flag({"dispositivos"}, build):
        con_flag = _client("delete_dispositivo").get(url)
    with _flag((), build):
        sin_flag = _client("delete_dispositivo").get(url)

    assert con_flag.status_code == 200
    assert MARK in con_flag.content.decode()
    assert sin_flag.status_code == 200
    native = sin_flag.content.decode()
    assert MARK not in native
    assert "Confirmar eliminación" in native
    assert "Refugio a eliminar" in native


def test_flag_on_post_still_deletes_natively(build, dispositivo):
    with _flag({"dispositivos"}, build):
        respuesta = _client("delete_dispositivo").post(
            f"/dispositivos/{dispositivo.pk}/eliminar"
        )
    assert respuesta.status_code == 302
    assert respuesta["Location"] == "/dispositivos/"
    assert not Dispositivo.objects.filter(pk=dispositivo.pk).exists()


def test_admindocs_head_does_not_bypass_the_screen_data(client, dispositivo):
    staff = User.objects.create_user("staff_eliminar", is_staff=True)
    staff.profile.acceso_web = True
    staff.profile.must_change_password = False
    staff.profile.needs_profile_confirmation = False
    staff.profile.save()
    client.force_login(staff)

    respuesta = client.head(API.format(dispositivo.pk))
    assert respuesta.status_code == 403
    assert "X-View" not in respuesta
