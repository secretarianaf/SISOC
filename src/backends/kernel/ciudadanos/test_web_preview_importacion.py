"""Local React preview entries of the ciudadanos bulk import (C01, ``ciudadanos.web_preview_importacion``)."""

import types

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client, override_settings

from ciudadanos.models import CiudadanosImportJob
from ciudadanos.web_preview_importacion import importacion_preview_patterns
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
    module = types.ModuleType("ciudadanos_preview_importacion_urls")
    module.urlpatterns = importacion_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


def _client(codename):
    user, _ = User.objects.get_or_create(username=f"prev_imp_{codename}")
    user.user_permissions.add(
        Permission.objects.get(content_type__app_label="ciudadanos", codename=codename)
    )
    client = Client()
    client.force_login(user)
    return client, user


def test_native_guards_then_frozen_index(preview):
    url = "/ciudadanos/importacion-masiva/"
    assert Client().get(url).status_code == 302
    assert _client("view_ciudadano")[0].get(url).status_code == 403
    cliente, _ = _client("add_ciudadano")
    respuesta = cliente.get(url)
    assert respuesta.status_code == 200
    assert "/ciudadanos/react/assets/app-1.js" in respuesta.content.decode()
    assert CiudadanosImportJob.objects.count() == 0


def test_lote_keeps_the_native_404_and_guards(preview, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    cliente, user = _client("add_ciudadano")
    job = CiudadanosImportJob.objects.create(
        requested_by=user, original_filename="lote.xlsx", archivo="x.xlsx"
    )
    url = f"/ciudadanos/importacion-masiva/lotes/{job.pk}/"
    assert Client().get(url).status_code == 302
    assert _client("view_ciudadano")[0].get(url).status_code == 403
    assert cliente.get("/ciudadanos/importacion-masiva/lotes/99999/").status_code == 404
    respuesta = cliente.get(url)
    assert respuesta.status_code == 200
    assert "/ciudadanos/react/assets/app-1.js" in respuesta.content.decode()
