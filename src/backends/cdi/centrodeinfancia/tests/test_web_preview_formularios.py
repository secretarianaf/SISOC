"""Local React preview entries of the CDI form screens (``centrodeinfancia.web_preview_formularios_institucionales``)."""

import types

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings

from centrodeinfancia.models import (
    AccesoCDI,
    CentroDeInfancia,
    FormularioCDI,
    FormularioCDIRoomDistribution,
)
from centrodeinfancia.web_preview import cdi_preview_patterns
from centrodeinfancia.web_preview_formularios_institucionales import (
    cdi_formularios_preview_patterns,
)
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
    module = types.ModuleType("cdi_formularios_preview_test_urls")
    module.urlpatterns = (
        cdi_formularios_preview_patterns(build)
        + cdi_preview_patterns(build)
        + list(monolith_patterns)
    )
    with override_settings(ROOT_URLCONF=module):
        yield


def _usuario(username, *codenames):
    user = User.objects.create_user(username)
    for codename in codenames:
        permiso = Permission.objects.filter(
            content_type__app_label="centrodeinfancia", codename=codename
        ).first() or Permission.objects.create(
            content_type=ContentType.objects.get_for_model(Group),
            codename=codename,
            name=codename,
        )
        user.user_permissions.add(permiso)
    client = Client()
    client.force_login(user)
    return user, client


@pytest.fixture(name="datos")
def datos_fixture():
    centro = CentroDeInfancia.objects.create(nombre="CDI Preview")
    otro = CentroDeInfancia.objects.create(nombre="CDI Ajeno")
    return (
        centro,
        FormularioCDI.objects.create(centro=centro),
        otro,
        FormularioCDI.objects.create(centro=otro),
    )


@pytest.mark.usefixtures("preview")
def test_entries_return_the_frozen_index_and_keep_the_native_guards(datos):
    centro, formulario, otro, ajeno = datos
    lista = f"/centrodeinfancia/{centro.pk}/formularios/"
    detalle = f"{lista}{formulario.pk}/"
    user, client = _usuario("prev-form", "view_formulariocdi")

    for url in (lista, detalle):
        respuesta = client.get(url)
        assert respuesta.status_code == 200
        assert '/centrodeinfancia/react/assets/app-1.js"' in respuesta.content.decode()
        assert "no-store" in respuesta["Cache-Control"]
        assert "csrftoken" in respuesta.cookies
    assert client.head(lista).content == b""
    AccesoCDI.objects.create(user=user, centro=centro)
    assert client.get(f"/centrodeinfancia/{otro.pk}/formularios/").status_code == 404
    assert client.get(f"{lista}{ajeno.pk}/").status_code == 404
    assert client.get(f"{lista}?page=9").status_code == 404
    with override_settings(ROOT_URLCONF="config.urls_all"):
        esperado = Client().get(lista)
    assert Client().get(lista).status_code == esperado.status_code
    assert _usuario("prev-form-sin")[1].get(lista).status_code == 403


@pytest.mark.usefixtures("preview")
def test_form_entries_return_the_index_without_building_the_formsets(datos):
    centro, formulario, otro, ajeno = datos
    user, client = _usuario(
        "prev-form-edit", "add_formulariocdi", "change_formulariocdi"
    )
    crear = f"/centrodeinfancia/{centro.pk}/formularios/crear/"
    editar = f"/centrodeinfancia/{centro.pk}/formularios/{formulario.pk}/editar/"

    assert client.get(crear).status_code == 200
    respuesta = client.get(editar)
    assert respuesta.status_code == 200
    assert "/centrodeinfancia/react/assets/app-1.js" in respuesta.content.decode()
    # The native edit GET creates the fixed rows; the index entry must not.
    assert not FormularioCDIRoomDistribution.objects.exists()
    AccesoCDI.objects.create(user=user, centro=centro)
    assert (
        client.get(f"/centrodeinfancia/{otro.pk}/formularios/crear/").status_code == 404
    )
    assert (
        client.get(
            f"/centrodeinfancia/{centro.pk}/formularios/{ajeno.pk}/editar/"
        ).status_code
        == 404
    )
    with override_settings(ROOT_URLCONF="config.urls_all"):
        esperado = Client().get(crear)
    assert Client().get(crear).status_code == esperado.status_code
    assert _usuario("prev-form-edit-sin")[1].get(crear).status_code == 403


def test_production_urlconf_keeps_the_native_pages(datos):
    centro, formulario, _, _ = datos
    _, client = _usuario("prev-form-nativo", "view_formulariocdi")

    lista = client.get(f"/centrodeinfancia/{centro.pk}/formularios/")
    detalle = client.get(f"/centrodeinfancia/{centro.pk}/formularios/{formulario.pk}/")

    assert "centrodeinfancia/formulario_cdi_list.html" in [
        t.name for t in lista.templates
    ]
    assert "centrodeinfancia/formulario_cdi_detail.html" in [
        t.name for t in detalle.templates
    ]


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        cdi_formularios_preview_patterns(tmp_path)
