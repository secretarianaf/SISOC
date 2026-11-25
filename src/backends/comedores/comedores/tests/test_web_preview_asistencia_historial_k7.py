"""Local React preview entry of the nómina attendance history (``comedores.web_preview_asistencia``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from admisiones.models.admisiones import Admision
from comedores.models import Comedor
from comedores.web_preview_asistencia import asistencia_preview_patterns
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
    module = types.ModuleType("comedores_asistencia_preview_test_urls")
    module.urlpatterns = asistencia_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.fixture(name="lector")
def lector_fixture():
    usuario = get_user_model().objects.create_user("lector_preview_asistencia")
    usuario.user_permissions.add(Permission.objects.get(codename="view_nomina"))
    client = Client()
    client.force_login(usuario)
    return client


def _url(comedor, admision):
    return f"/comedores/{comedor.pk}/admision/{admision.pk}/nomina/asistencia/"


@pytest.mark.usefixtures("preview")
def test_entry_gets_the_frozen_index(lector):
    comedor = Comedor.objects.create(nombre="Preview Asistencia")
    admision = Admision.objects.create(comedor=comedor)

    respuesta = lector.get(_url(comedor, admision), {"periodo": "2026-10-01"})

    assert respuesta.status_code == 200
    assert '/comedores/react/assets/app-1.js"' in respuesta.content.decode()
    assert "no-store" in respuesta["Cache-Control"]
    assert "csrftoken" in respuesta.cookies
    assert lector.get("/comedores/react/assets/app-1.js").content == b"console.log(1);"


@pytest.mark.usefixtures("preview")
def test_native_guards_and_scope_decide_first(lector):
    comedor = Comedor.objects.create(nombre="Preview Asistencia Guard")
    admision = Admision.objects.create(comedor=comedor)
    ajena = Admision.objects.create(comedor=Comedor.objects.create(nombre="Otro"))
    sin_permiso = Client()
    sin_permiso.force_login(
        get_user_model().objects.create_user("sin_permiso_pasistencia")
    )

    assert Client().get(_url(comedor, admision)).status_code in (302, 403)
    assert sin_permiso.get(_url(comedor, admision)).status_code == 403
    assert lector.get(_url(Comedor(pk=999999), admision)).status_code == 404
    assert lector.get(_url(comedor, ajena)).status_code == 404


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        asistencia_preview_patterns(tmp_path)
