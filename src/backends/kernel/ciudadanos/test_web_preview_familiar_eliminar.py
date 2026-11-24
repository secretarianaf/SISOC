"""Local React preview entry of the familiar unlink page (C03.02, ``ciudadanos.web_preview_familiar_eliminar``)."""

import types

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client, override_settings

from ciudadanos.models import Ciudadano, GrupoFamiliar
from ciudadanos.web_preview_familiar_eliminar import familiar_eliminar_preview_patterns
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
    module = types.ModuleType("ciudadanos_preview_familiar_eliminar_urls")
    module.urlpatterns = familiar_eliminar_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


def _client(codename):
    user, _ = User.objects.get_or_create(username=f"prev_fam_{codename}")
    user.user_permissions.add(
        Permission.objects.get(content_type__app_label="ciudadanos", codename=codename)
    )
    client = Client()
    client.force_login(user)
    return client


def test_native_guards_then_frozen_index(preview):
    ana = Ciudadano.objects.create(nombre="Ana", apellido="Prev", documento=3111)
    zoe = Ciudadano.objects.create(nombre="Zoe", apellido="Prev", documento=3112)
    relacion = GrupoFamiliar.objects.create(
        ciudadano_1=ana, ciudadano_2=zoe, vinculo="HIJO/A"
    )
    url = f"/ciudadanos/familiares/{relacion.pk}/eliminar"
    assert Client().get(url).status_code == 302
    assert _client("view_ciudadano").get(url).status_code == 403
    cliente = _client("change_ciudadano")
    assert cliente.get("/ciudadanos/familiares/99999/eliminar").status_code == 404
    respuesta = cliente.get(url)
    assert respuesta.status_code == 200
    assert "/ciudadanos/react/assets/app-1.js" in respuesta.content.decode()
    # The page is only the index: nothing is unlinked by looking at it.
    assert GrupoFamiliar.objects.filter(pk=relacion.pk).exists()
