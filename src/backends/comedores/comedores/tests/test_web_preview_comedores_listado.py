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
def test_export_stays_native(lector):
    assert lector.get("/comedores/exportar").status_code == 403


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        comedores_preview_patterns(tmp_path)


@pytest.mark.usefixtures("preview")
def test_baja_entry_gets_the_index_after_the_native_guard_and_scope():
    comedor = Comedor.objects.create(nombre="Para baja")
    gestor = get_user_model().objects.create_user("gestor_preview_baja")
    gestor.user_permissions.add(Permission.objects.get(codename="delete_comedor"))
    client = Client()
    client.force_login(gestor)
    url = f"/comedores/{comedor.pk}/eliminar"

    assert client.get(url).status_code == 200
    assert client.get("/comedores/999999/eliminar").status_code == 404
    assert Client().get(url).status_code in (302, 403)
    # The POST reaches the native view: the baja itself is native.
    assert client.post(url).status_code == 302
    assert not Comedor.objects.filter(pk=comedor.pk).exists()


@pytest.mark.usefixtures("preview")
def test_form_entries_get_the_index_after_the_native_guard_and_scope():
    comedor = Comedor.objects.create(nombre="Para editar")
    gestor = get_user_model().objects.create_user("gestor_preview_form")
    gestor.user_permissions.add(Permission.objects.get(codename="add_comedor"))
    gestor.user_permissions.add(Permission.objects.get(codename="change_comedor"))
    client = Client()
    client.force_login(gestor)
    lector = get_user_model().objects.create_user("lector_preview_form")
    lector.user_permissions.add(Permission.objects.get(codename="view_comedor"))
    solo_lector = Client()
    solo_lector.force_login(lector)

    assert client.get("/comedores/crear").status_code == 200
    assert client.get(f"/comedores/{comedor.pk}/editar").status_code == 200
    assert client.get("/comedores/999999/editar").status_code == 404
    assert solo_lector.get("/comedores/crear").status_code == 403
    assert solo_lector.get(f"/comedores/{comedor.pk}/editar").status_code == 403
    assert Client().get("/comedores/crear").status_code in (302, 403)
    # The POST reaches the native view (it renders its errors: nothing is saved).
    antes = Comedor.objects.count()
    assert client.post("/comedores/crear", {}).status_code == 200
    assert Comedor.objects.count() == antes
