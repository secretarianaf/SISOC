"""Local React preview entries of the CDI worker screens (``centrodeinfancia.web_preview_trabajadores``)."""

import types

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings

from centrodeinfancia.models import AccesoCDI, CentroDeInfancia, Trabajador
from centrodeinfancia.web_preview import cdi_preview_patterns
from centrodeinfancia.web_preview_trabajadores import cdi_trabajadores_preview_patterns
from core.constants import UserGroups
from config.urls_all import urlpatterns as monolith_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)

pytestmark = pytest.mark.django_db


@pytest.fixture(name="build")
def build_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    return tmp_path


@pytest.fixture(name="preview")
def preview_fixture(build):
    module = types.ModuleType("cdi_trabajadores_preview_test_urls")
    module.urlpatterns = (
        cdi_trabajadores_preview_patterns(build)
        + cdi_preview_patterns(build)
        + list(monolith_patterns)
    )
    with override_settings(ROOT_URLCONF=module):
        yield


def _cliente(user):
    client = Client()
    client.force_login(user)
    return client


# Por defecto SIMEPI Equipo Nacional: está en la regla de la Fuerza de Trabajo
# (#2943) con alcance nacional.
def _usuario(username, *codenames, grupos=(UserGroups.SIMEPI_EQUIPO_NACIONAL,)):
    user = User.objects.create_user(username)
    for nombre in grupos:
        user.groups.add(Group.objects.get_or_create(name=nombre)[0])
    for codename in codenames:
        permiso = Permission.objects.filter(
            content_type__app_label="centrodeinfancia", codename=codename
        ).first() or Permission.objects.create(
            content_type=ContentType.objects.get_for_model(Group),
            codename=codename,
            name=codename,
        )
        user.user_permissions.add(permiso)
    return user


@pytest.fixture(name="datos")
def datos_fixture():
    centro = CentroDeInfancia.objects.create(nombre="CDI Preview")
    otro = CentroDeInfancia.objects.create(nombre="CDI Ajeno")
    trabajador = Trabajador.objects.create(centro=centro, nombre="Ana", apellido="Paz")
    ajeno = Trabajador.objects.create(centro=otro, nombre="Eva", apellido="Sol")
    return centro, trabajador, otro, ajeno


def _url(centro, trabajador):
    return f"/centrodeinfancia/{centro.pk}/trabajadores/{trabajador.pk}/"


@pytest.mark.usefixtures("preview")
def test_detail_entry_returns_the_frozen_index_for_the_scoped_worker(datos):
    centro, trabajador, _, _ = datos
    client = _cliente(_usuario("prev-trab-ver", "view_trabajador"))

    respuesta = client.get(_url(centro, trabajador))

    assert respuesta.status_code == 200
    assert '/centrodeinfancia/react/assets/app-1.js"' in respuesta.content.decode()
    assert "no-store" in respuesta["Cache-Control"]
    assert "Cookie" in respuesta["Vary"]
    assert "csrftoken" in respuesta.cookies
    assert client.head(_url(centro, trabajador)).content == b""


@pytest.mark.usefixtures("preview")
def test_detail_entry_keeps_the_native_guards(datos):
    centro, trabajador, otro, ajeno = datos
    url = _url(centro, trabajador)
    anonimo = Client().get(url)
    with override_settings(ROOT_URLCONF="config.urls_all"):
        esperado = Client().get(url)
    assert anonimo.status_code == esperado.status_code
    assert anonimo.get("Location") == esperado.get("Location")

    sin_permiso = _cliente(_usuario("prev-trab-sin", grupos=()))
    assert sin_permiso.get(url).status_code == 403
    referente = _usuario(
        "prev-trab-referente",
        "view_trabajador",
        grupos=[UserGroups.CDI_REFERENTE_CENTRO],
    )
    AccesoCDI.objects.create(user=referente, centro=centro)
    cliente = _cliente(referente)
    assert cliente.get(url).status_code == 200
    assert cliente.get(_url(otro, ajeno)).status_code == 404
    assert cliente.get(_url(centro, ajeno)).status_code == 404


def test_production_urlconf_keeps_the_native_page(datos):
    centro, trabajador, _, _ = datos
    client = _cliente(_usuario("prev-trab-nativo", "view_trabajador"))

    respuesta = client.get(_url(centro, trabajador))

    assert respuesta.status_code == 200
    assert "centrodeinfancia/trabajador_detail.html" in [
        t.name for t in respuesta.templates
    ]


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        cdi_trabajadores_preview_patterns(tmp_path)


@pytest.mark.usefixtures("preview")
def test_form_entries_return_the_index_and_keep_the_native_guards(datos):
    centro, trabajador, _, ajeno = datos
    cliente = _cliente(
        _usuario("prev-trab-form", "add_trabajador", "change_trabajador")
    )
    crear = f"/centrodeinfancia/{centro.pk}/trabajadores/crear/"
    editar = f"{_url(centro, trabajador)}editar/"

    assert cliente.get(crear).status_code == 200
    assert (
        "/centrodeinfancia/react/assets/app-1.js"
        in cliente.get(editar).content.decode()
    )
    assert cliente.get(f"{_url(centro, ajeno)}editar/").status_code == 404
    with override_settings(ROOT_URLCONF="config.urls_all"):
        esperado = Client().get(crear)
    assert Client().get(crear).status_code == esperado.status_code
    assert (
        _cliente(_usuario("prev-trab-form-sin", grupos=())).get(crear).status_code
        == 403
    )
    assert not Trabajador.objects.exclude(pk__in=[trabajador.pk, ajeno.pk]).exists()
