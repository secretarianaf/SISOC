"""Local React preview entry of the CDI nomina attendance (``web_preview_nomina_asistencia``)."""

import types

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client, override_settings

from centrodeinfancia.models import AccesoCDI, CentroDeInfancia
from centrodeinfancia.web_preview_nomina_asistencia import (
    nomina_asistencia_preview_patterns,
)
from config.urls_all import urlpatterns as monolith_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
CAMBIO = "centrodeinfancia.change_centrodeinfancia"

pytestmark = pytest.mark.django_db


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("cdi_preview_nomina_asistencia_test_urls")
    module.urlpatterns = nomina_asistencia_preview_patterns(tmp_path) + list(
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


@pytest.mark.usefixtures("preview")
def test_entry_serves_the_frozen_index_after_the_native_guards():
    centro = CentroDeInfancia.objects.create(nombre="CDI Vista previa")
    url = f"/centrodeinfancia/{centro.pk}/nomina/asistencia/"

    _, con_permiso = _usuario("prev-asis-ok", CAMBIO)
    _, sin_permiso = _usuario("prev-asis-sin")
    respuesta = con_permiso.get(url)

    assert respuesta.status_code == 200
    assert b"/centrodeinfancia/react/assets/app-1.js" in respuesta.content
    assert "no-store" in respuesta["Cache-Control"]
    assert Client().get(url).status_code in (302, 401, 403)
    assert sin_permiso.get(url).status_code == 403


@pytest.mark.usefixtures("preview")
def test_entry_keeps_the_native_scope_404_and_the_native_calendar():
    centro = CentroDeInfancia.objects.create(nombre="CDI Vista previa")
    otro = CentroDeInfancia.objects.create(nombre="CDI Otro")
    user, client = _usuario("prev-asis-scope", CAMBIO)
    AccesoCDI.objects.create(user=user, centro=otro)

    assert (
        client.get(f"/centrodeinfancia/{centro.pk}/nomina/asistencia/").status_code
        == 404
    )
    assert client.get("/centrodeinfancia/999999/nomina/asistencia/").status_code == 404
    calendario = client.get(
        f"/centrodeinfancia/{otro.pk}/nomina/asistencia/calendario/?mes=2026-07"
    )
    assert calendario.status_code == 200
    assert calendario.json() == {"dias": []}
