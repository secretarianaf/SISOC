"""Local React preview entry of the comedor ficha (``comedores.web_preview_comedores``)."""

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

pytestmark = pytest.mark.django_db


@pytest.fixture(name="comedor_fixture", autouse=True)
def sin_dobles_del_conftest():
    """Same name as the folder's autouse double: the entry runs the real scope lookup."""


@pytest.fixture(name="preview", autouse=True)
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("comedores_ficha_preview_test_urls")
    module.urlpatterns = comedores_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


def _client(username, *codenames):
    usuario = get_user_model().objects.create_user(username)
    for codename in codenames:
        usuario.user_permissions.add(Permission.objects.get(codename=codename))
    client = Client()
    client.force_login(usuario)
    return client


def test_ficha_gets_the_frozen_index_after_the_native_guard_and_scope():
    comedor = Comedor.objects.create(nombre="Para ficha")
    url = f"/comedores/{comedor.pk}"

    respuesta = _client("lector_preview_ficha", "view_comedor").get(url)

    assert respuesta.status_code == 200
    assert '/comedores/react/assets/app-1.js"' in respuesta.content.decode()
    assert "no-store" in respuesta["Cache-Control"]
    assert "csrftoken" in respuesta.cookies
    lector = _client("lector_preview_ficha2", "view_comedor")
    assert lector.get("/comedores/999999").status_code == 404
    assert Client().get(url).status_code in (302, 403)
    assert _client("sin_permiso_preview_ficha").get(url).status_code == 403


@pytest.mark.parametrize("codename", ["view_admision", "view_informacionrelevante"])
def test_ficha_entry_accepts_each_native_permission(codename):
    comedor = Comedor.objects.create(nombre="Para ficha")

    cliente = _client(f"lector_preview_{codename}", codename)

    assert cliente.get(f"/comedores/{comedor.pk}").status_code == 200


def test_the_ficha_does_not_change_on_the_native_post():
    comedor = Comedor.objects.create(nombre="Para ficha")
    gestor = _client("gestor_preview_ficha", "view_comedor")

    # The POST (admission, discard) reaches the native view; nothing is created here.
    assert gestor.post(f"/comedores/{comedor.pk}", {}).status_code == 302
    assert Comedor.objects.filter(pk=comedor.pk).exists()
