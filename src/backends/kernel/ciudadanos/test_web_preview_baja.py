"""Local React preview entry of the Ciudadano baja page (C05.03, ``ciudadanos.web_preview``)."""

import types

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client, override_settings

from ciudadanos.models import Ciudadano
from ciudadanos.web_preview import ciudadanos_preview_patterns
from config.urls_all import urlpatterns as monolith_patterns

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
    module = types.ModuleType("ciudadanos_preview_baja_urls")
    module.urlpatterns = ciudadanos_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


def _client(codename):
    user, _ = User.objects.get_or_create(username=f"prev_baja_{codename}")
    user.user_permissions.add(
        Permission.objects.get(content_type__app_label="ciudadanos", codename=codename)
    )
    client = Client()
    client.force_login(user)
    return client


def test_native_guards_then_frozen_index(preview):
    ciudadano = Ciudadano.objects.create(nombre="Ana", apellido="Prev", documento=3111)
    url = f"/ciudadanos/eliminar/{ciudadano.pk}"
    assert Client().get(url).status_code == 302
    assert _client("view_ciudadano").get(url).status_code == 403
    baja = _client("delete_ciudadano")
    assert baja.get("/ciudadanos/eliminar/99999").status_code == 404
    respuesta = baja.get(url)
    assert respuesta.status_code == 200
    assert "/ciudadanos/react/assets/app-1.js" in respuesta.content.decode()
    # The page is only the index: nothing is deleted by looking at it.
    assert Ciudadano.objects.filter(pk=ciudadano.pk).exists()


def test_familiar_nuevo_native_guards_then_frozen_index(preview):
    ciudadano = Ciudadano.objects.create(nombre="Ana", apellido="Prev", documento=3112)
    url = f"/ciudadanos/{ciudadano.pk}/familiares/nuevo"
    assert Client().get(url).status_code == 302
    # The native view looks the ciudadano up before checking the permission.
    assert (
        _client("view_ciudadano").get("/ciudadanos/99999/familiares/nuevo").status_code
        == 404
    )
    assert _client("view_ciudadano").get(url).status_code == 403
    respuesta = _client("change_ciudadano").get(url)
    assert respuesta.status_code == 200
    assert "/ciudadanos/react/assets/app-1.js" in respuesta.content.decode()
