"""Local React preview entry of the identity review queue (C02, ``ciudadanos.web_preview_cola_revision``)."""

import types

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client, override_settings

from ciudadanos.models import Ciudadano
from ciudadanos.web_preview_cola_revision import cola_revision_preview_patterns
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
    module = types.ModuleType("ciudadanos_preview_cola_revision_urls")
    module.urlpatterns = cola_revision_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


def _client(codename):
    user, _ = User.objects.get_or_create(username=f"prev_cola_{codename}")
    user.user_permissions.add(
        Permission.objects.get(content_type__app_label="ciudadanos", codename=codename)
    )
    client = Client()
    client.force_login(user)
    return client


def test_native_guards_then_frozen_index(preview):
    url = "/ciudadanos/revision/"
    assert Client().get(url).status_code == 302
    assert _client("view_ciudadano").get(url).status_code == 403
    cliente = _client("revision_identidad")
    respuesta = cliente.get(url)
    assert respuesta.status_code == 200
    assert "/ciudadanos/react/assets/app-1.js" in respuesta.content.decode()
    # The native paginator keeps its 404 for a page out of range.
    assert cliente.get(f"{url}?page=9").status_code == 404


def test_looking_at_the_queue_writes_nothing(preview):
    pendiente = Ciudadano.objects.create(
        nombre="Ana",
        apellido="Cola",
        tipo_registro_identidad=Ciudadano.TIPO_REGISTRO_SIN_DNI,
        requiere_revision_manual=True,
        estado_revision_manual=Ciudadano.REVISION_IDENTIDAD_PENDIENTE,
    )
    _client("revision_identidad").get("/ciudadanos/revision/")
    pendiente.refresh_from_db()
    assert pendiente.requiere_revision_manual is True
    assert pendiente.estado_revision_manual == Ciudadano.REVISION_IDENTIDAD_PENDIENTE
