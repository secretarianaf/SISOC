"""Local React preview entries of the CDI form screens (``web_preview_formularios``)."""

import types

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.test import Client, override_settings
from django.urls import reverse

from centrodeinfancia.models import AccesoCDI, CentroDeInfancia
from centrodeinfancia.web_preview_formularios import formularios_preview_patterns
from config.urls_all import urlpatterns as monolith_patterns
from core.constants import UserGroups

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
    module = types.ModuleType("cdi_preview_formularios_test_urls")
    module.urlpatterns = formularios_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


def _cliente(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="centro")
def centro_fixture():
    return CentroDeInfancia.objects.create(nombre="CDI Vista previa")


def _url(centro):
    return reverse("centrodeinfancia_generar_usuario", args=[centro.pk])


@pytest.mark.usefixtures("preview")
def test_generar_usuario_entry_serves_the_index_after_the_native_guards(centro):
    Group.objects.get_or_create(name=UserGroups.CDI_REFERENTE_CENTRO)
    admin = User.objects.create_superuser("c7-preview-admin", "", "test1234")

    respuesta = _cliente(admin).get(_url(centro))

    assert respuesta.status_code == 200
    assert b"/centrodeinfancia/react/assets/app-1.js" in respuesta.content
    assert respuesta["Cache-Control"] == "private, no-store"


@pytest.mark.usefixtures("preview")
def test_generar_usuario_entry_keeps_the_native_rejections(centro):
    plano = User.objects.create_user("c7-preview-plano")
    plano.user_permissions.add(Permission.objects.get(codename="view_centrodeinfancia"))
    sin_permiso = User.objects.create_user("c7-preview-sin")

    assert _cliente(plano).get(_url(centro)).status_code == 403
    assert _cliente(sin_permiso).get(_url(centro)).status_code == 403
    assert Client().get(_url(centro)).status_code in (302, 401, 403)
    assert not AccesoCDI.objects.exists()


@pytest.mark.usefixtures("preview")
def test_generar_usuario_entry_unknown_centre_is_404():
    admin = User.objects.create_superuser("c7-preview-admin2", "", "test1234")

    assert (
        _cliente(admin)
        .get(reverse("centrodeinfancia_generar_usuario", args=[987654]))
        .status_code
        == 404
    )


@pytest.mark.usefixtures("preview")
def test_assets_are_served_only_from_the_frozen_build():
    assert Client().get("/centrodeinfancia/react/assets/app-1.js").status_code == 200
    assert Client().get("/centrodeinfancia/react/assets/missing.js").status_code == 404
