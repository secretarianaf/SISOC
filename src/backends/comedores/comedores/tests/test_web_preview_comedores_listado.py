"""Local React preview entry of the comedor list (``comedores.web_preview_comedores``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from comedores.models import Comedor
from comedores.web_preview_comedores import comedores_preview_patterns
from config.urls_all import urlpatterns as monolith_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
LISTA = "/comedores/listar"

pytestmark = pytest.mark.django_db


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("comedores_listado_preview_test_urls")
    module.urlpatterns = comedores_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.fixture(name="lector")
def lector_fixture():
    usuario = get_user_model().objects.create_user("lector_preview_listado")
    usuario.user_permissions.add(Permission.objects.get(codename="view_comedor"))
    client = Client()
    client.force_login(usuario)
    return client


@pytest.mark.usefixtures("preview")
def test_list_gets_the_frozen_index(lector):
    respuesta = lector.get(LISTA)

    assert respuesta.status_code == 200
    assert '/comedores/react/assets/app-1.js"' in respuesta.content.decode()
    assert "no-store" in respuesta["Cache-Control"]
    assert "csrftoken" in respuesta.cookies
    assert lector.get("/comedores/react/assets/app-1.js").content == b"console.log(1);"


@pytest.mark.usefixtures("preview")
def test_native_guards_and_page_validation_decide_first(lector):
    Comedor.objects.create(nombre="Uno")
    sin_permiso = Client()
    sin_permiso.force_login(get_user_model().objects.create_user("sin_permiso_lst"))

    assert Client().get(LISTA).status_code in (302, 403)
    assert sin_permiso.get(LISTA).status_code == 403
    assert lector.get(LISTA, {"page": "x"}).status_code == 200


@pytest.mark.usefixtures("preview")
def test_export_and_create_stay_native(lector):
    assert lector.get("/comedores/exportar").status_code == 403
    assert lector.get("/comedores/crear").status_code == 403


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        comedores_preview_patterns(tmp_path)
