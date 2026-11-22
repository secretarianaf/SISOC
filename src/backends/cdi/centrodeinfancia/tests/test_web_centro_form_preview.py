"""Local React preview entries of the CDI centre form (``web_preview_centro_form``)."""

import types

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.test import Client, override_settings
from django.urls import reverse

from centrodeinfancia.models import CentroDeInfancia
from centrodeinfancia.web_preview_centro_form import centro_form_preview_patterns
from config.urls_all import urlpatterns as monolith_patterns
from core.constants import UserGroups
from core.models import Provincia
from users.models import Profile

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
VETO = "El rol Auditoría tiene acceso de solo lectura."

pytestmark = pytest.mark.django_db


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("cdi_preview_centro_form_test_urls")
    module.urlpatterns = centro_form_preview_patterns(tmp_path) + list(
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


def _usuario(username, *codenames):
    user = User.objects.create_user(username)
    for codename in codenames:
        user.user_permissions.add(Permission.objects.get(codename=codename))
    perfil = Profile.objects.get_or_create(user=user)[0]
    perfil.acceso_web = True
    perfil.must_change_password = False
    perfil.needs_profile_confirmation = False
    perfil.save()
    return User.objects.get(pk=user.pk)


@pytest.mark.usefixtures("preview")
def test_entries_serve_the_index_after_the_native_guards(centro):
    admin = User.objects.create_superuser("c9-preview-admin", "", "test1234")

    for url in (
        reverse("centrodeinfancia_crear"),
        reverse("centrodeinfancia_editar", args=[centro.pk]),
    ):
        respuesta = _cliente(admin).get(url)
        assert respuesta.status_code == 200
        assert b"/centrodeinfancia/react/assets/app-1.js" in respuesta.content
        assert respuesta["Cache-Control"] == "private, no-store"


@pytest.mark.usefixtures("preview")
def test_entries_keep_the_native_rejections(centro):
    crear = reverse("centrodeinfancia_crear")
    editar = reverse("centrodeinfancia_editar", args=[centro.pk])
    solo_alta = _usuario("c9-preview-alta", "add_centrodeinfancia")

    assert _cliente(solo_alta).get(crear).status_code == 200
    assert _cliente(solo_alta).get(editar).status_code == 403
    assert Client().get(crear).status_code in (302, 401, 403)


@pytest.mark.usefixtures("preview")
def test_unknown_centre_is_404_and_the_auditor_cannot_post(centro):
    admin = User.objects.create_superuser("c9-preview-admin2", "", "test1234")
    assert (
        _cliente(admin)
        .get(reverse("centrodeinfancia_editar", args=[987654]))
        .status_code
        == 404
    )

    auditor = _usuario("c9-preview-auditor", "add_centrodeinfancia")
    auditor.groups.add(Group.objects.get_or_create(name=UserGroups.SIMEPI_AUDITORIA)[0])
    antes = CentroDeInfancia.objects.count()
    respuesta = _cliente(auditor).post(
        reverse("centrodeinfancia_crear"),
        {"nombre": "No crear", "provincia": Provincia.objects.create(nombre="X").pk},
    )

    assert respuesta.status_code == 403
    assert CentroDeInfancia.objects.count() == antes
