"""Local React preview entry of the certifications history (``comedores.web_preview_certificaciones``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from comedores.models import Comedor
from comedores.web_preview_certificaciones import certificaciones_preview_patterns
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
    module = types.ModuleType("comedores_certificaciones_preview_test_urls")
    module.urlpatterns = certificaciones_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.fixture(name="lector")
def lector_fixture():
    usuario = get_user_model().objects.create_user("lector_preview_cert")
    usuario.user_permissions.add(Permission.objects.get(codename="view_comedor"))
    client = Client()
    client.force_login(usuario)
    return client


def _url(comedor):
    return f"/comedores/{comedor.pk}/certificaciones-prestaciones/"


@pytest.mark.usefixtures("preview")
def test_entry_gets_the_frozen_index(lector):
    comedor = Comedor.objects.create(nombre="Preview Certificaciones")

    respuesta = lector.get(_url(comedor), {"conforme": "true"})

    assert respuesta.status_code == 200
    assert '/comedores/react/assets/app-1.js"' in respuesta.content.decode()
    assert "no-store" in respuesta["Cache-Control"]
    assert "csrftoken" in respuesta.cookies
    assert lector.get("/comedores/react/assets/app-1.js").content == b"console.log(1);"


@pytest.mark.usefixtures("preview")
def test_native_guards_scope_and_page_decide_first(lector):
    comedor = Comedor.objects.create(nombre="Preview Certificaciones Guard")
    sin_permiso = Client()
    sin_permiso.force_login(get_user_model().objects.create_user("sin_permiso_pcert"))

    assert Client().get(_url(comedor)).status_code in (302, 403)
    assert sin_permiso.get(_url(comedor)).status_code == 403
    assert lector.get(_url(Comedor(pk=999999))).status_code == 404
    assert lector.get(_url(comedor), {"page": 9}).status_code == 404


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        certificaciones_preview_patterns(tmp_path)
