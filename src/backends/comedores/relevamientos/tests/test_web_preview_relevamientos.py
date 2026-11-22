"""Local React preview entries of R01.01 (``relevamientos.web_preview``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from comedores.models import Comedor
from config.urls_all import urlpatterns as monolith_patterns
from relevamientos.models import Relevamiento
from relevamientos.web_preview import relevamientos_preview_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)

pytestmark = pytest.mark.django_db


@pytest.fixture(name="build")
def build_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    return tmp_path


@pytest.fixture(name="preview")
def preview_fixture(build):
    module = types.ModuleType("relevamientos_preview_test_urls")
    module.urlpatterns = relevamientos_preview_patterns(build) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


def _login(nombre, con_permiso=True):
    usuario = get_user_model().objects.create_user(nombre)
    if con_permiso:
        usuario.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="relevamientos", codename="view_relevamiento"
            )
        )
    client = Client()
    client.force_login(usuario)
    return client


@pytest.mark.usefixtures("preview")
def test_list_and_detail_get_the_frozen_index():
    comedor = Comedor.objects.create(nombre="Prev")
    relevamiento = Relevamiento.objects.create(comedor=comedor)
    client = _login("lector_prev_rel")

    for url in (
        f"/comedores/{comedor.pk}/relevamiento/listar",
        f"/comedores/{comedor.pk}/relevamiento/{relevamiento.pk}",
    ):
        respuesta = client.get(url)
        assert respuesta.status_code == 200
        assert (
            '/comedores/react/relevamientos/assets/app-1.js"'
            in respuesta.content.decode()
        )
        assert "csrftoken" in respuesta.cookies
    asset = client.get("/comedores/react/relevamientos/assets/app-1.js")
    assert asset.content == b"console.log(1);"


@pytest.mark.usefixtures("preview")
def test_native_guards_decide_first():
    comedor = Comedor.objects.create(nombre="Prev2")
    relevamiento = Relevamiento.objects.create(comedor=comedor)
    listado = f"/comedores/{comedor.pk}/relevamiento/listar"
    detalle = f"/comedores/{comedor.pk}/relevamiento/{relevamiento.pk}"

    assert Client().get(listado).status_code == 403
    assert _login("sin_prev_rel", False).get(detalle).status_code == 403
    lector = _login("lector2_prev_rel")
    assert lector.get("/comedores/999999/relevamiento/listar").status_code == 404
    assert lector.get(f"/comedores/{comedor.pk}/relevamiento/999999").status_code == 404
    relevamiento.delete()
    assert lector.get(detalle).status_code == 404


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        relevamientos_preview_patterns(tmp_path)


@pytest.mark.usefixtures("preview")
def test_the_baja_confirmation_gets_the_frozen_index_and_post_stays_native():
    comedor = Comedor.objects.create(nombre="Prev baja")
    relevamiento = Relevamiento.objects.create(comedor=comedor)
    url = f"/comedores/{comedor.pk}/relevamiento/{relevamiento.pk}/eliminar"
    usuario = get_user_model().objects.create_user("editor_prev_baja")
    usuario.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="relevamientos", codename="change_relevamiento"
        )
    )
    client = Client()
    client.force_login(usuario)

    assert Client().get(url).status_code == 403
    assert _login("lector_prev_baja").get(url).status_code == 403
    assert client.get(f"{url[:-8]}9999/eliminar").status_code == 404
    respuesta = client.get(url)
    assert respuesta.status_code == 200
    assert (
        "/comedores/react/relevamientos/assets/app-1.js" in respuesta.content.decode()
    )
    assert client.post(url).status_code == 302
    assert client.get(url).status_code == 404
