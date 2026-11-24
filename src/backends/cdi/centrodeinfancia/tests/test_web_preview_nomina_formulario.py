"""Local React preview entry of the CDI nomina form detail (``web_preview_nomina_formulario``)."""

import types

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client, override_settings

from centrodeinfancia.models import AccesoCDI, CentroDeInfancia, NominaCentroInfancia
from centrodeinfancia.web_preview_nomina_formulario import (
    nomina_formulario_preview_patterns,
)
from ciudadanos.models import Ciudadano
from config.urls_all import urlpatterns as monolith_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
VER = "centrodeinfancia.view_nominacentroinfancia"

pytestmark = pytest.mark.django_db


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("cdi_preview_nomina_formulario_test_urls")
    module.urlpatterns = nomina_formulario_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


def _usuario(username, *codigos):
    user = User.objects.create_user(username)
    for codigo in codigos:
        app, codename = codigo.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    user = User.objects.get(pk=user.pk)
    client = Client()
    client.force_login(user)
    return user, client


def _nomina(nombre, documento):
    centro = CentroDeInfancia.objects.create(nombre=nombre)
    ciudadano = Ciudadano.objects.create(
        apellido="Ramirez", nombre="Sofia", documento=documento
    )
    ficha = NominaCentroInfancia.objects.create(
        centro=centro, ciudadano=ciudadano, dni=documento
    )
    return centro, ficha


@pytest.mark.usefixtures("preview")
def test_entry_serves_the_frozen_index_after_the_native_guards():
    _, ficha = _nomina("CDI Vista previa", 44555666)
    url = f"/centrodeinfancia/{ficha.pk}/nomina/formulario/"

    _, con_permiso = _usuario("prev-form-ok", VER)
    _, sin_permiso = _usuario("prev-form-sin")
    respuesta = con_permiso.get(url)

    assert respuesta.status_code == 200
    assert b"/centrodeinfancia/react/assets/app-1.js" in respuesta.content
    assert "no-store" in respuesta["Cache-Control"]
    assert Client().get(url).status_code in (302, 401, 403)
    assert sin_permiso.get(url).status_code == 403


@pytest.mark.usefixtures("preview")
def test_entry_keeps_the_native_scope_and_404():
    _, ficha = _nomina("CDI Vista previa", 44555666)
    otro, _ = _nomina("CDI Otro", 44555667)
    user, client = _usuario("prev-form-scope", VER)
    AccesoCDI.objects.create(user=user, centro=otro)

    assert (
        client.get(f"/centrodeinfancia/{ficha.pk}/nomina/formulario/").status_code
        == 404
    )
    assert client.get("/centrodeinfancia/999999/nomina/formulario/").status_code == 404
