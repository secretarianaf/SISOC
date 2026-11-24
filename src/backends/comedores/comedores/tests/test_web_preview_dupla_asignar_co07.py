"""Local React preview entry of the technical-team assignment (``comedores.web_preview_dupla_asignar``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from comedores.models import Comedor
from comedores.web_preview_dupla_asignar import dupla_asignar_preview_patterns
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
    module = types.ModuleType("dupla_asignar_preview_test_urls")
    module.urlpatterns = dupla_asignar_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


def _cliente(nombre, *codes, **extra):
    usuario = get_user_model().objects.create_user(nombre, **extra)
    for code in codes:
        app, codename = code.split(".")
        usuario.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    client = Client()
    client.force_login(usuario)
    return client


@pytest.mark.usefixtures("preview")
def test_the_entry_serves_the_frozen_index_with_its_native_permission():
    comedor = Comedor.objects.create(nombre="Comedor preview dupla")
    url = f"/comedores/dupla/asignar/{comedor.pk}"

    respuesta = _cliente("u_dupla_co07", "duplas.change_dupla").get(url)

    assert respuesta.status_code == 200
    assert '/comedores/dupla/react/assets/app-1.js"' in respuesta.content.decode()
    assert "no-store" in respuesta["Cache-Control"]
    assert "csrftoken" in respuesta.cookies
    asset = Client().get("/comedores/dupla/react/assets/app-1.js")
    assert asset.content == b"console.log(1);"


@pytest.mark.usefixtures("preview")
def test_native_guards_and_missing_objects_decide_first():
    comedor = Comedor.objects.create(nombre="Comedor preview dupla guard")
    url = f"/comedores/dupla/asignar/{comedor.pk}"

    assert Client().get(url).status_code in (302, 403)
    assert _cliente("sin_permiso_dupla_co07").get(url).status_code == 403
    root = _cliente("root_dupla_co07", is_superuser=True)
    assert root.get("/comedores/dupla/asignar/999999").status_code == 404
