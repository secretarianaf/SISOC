"""Local React preview entries of RF01.01 (``rendicioncuentasfinal.web_preview``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from comedores.models import Comedor
from config.urls_all import urlpatterns as monolith_patterns
from rendicioncuentasfinal.models import RendicionCuentasFinal
from rendicioncuentasfinal.web_preview import rendicion_final_preview_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
LISTADO = "/rendicion_cuentas_final/listar/"
DETALLE = "/comedores/{}/rendicion_cuentas_final/"
VIEW = "rendicioncuentasfinal.view_rendicioncuentasfinal"

pytestmark = pytest.mark.django_db


@pytest.fixture(name="build")
def build_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    return tmp_path


@pytest.fixture(name="preview")
def preview_fixture(build):
    module = types.ModuleType("rendicion_final_preview_test_urls")
    module.urlpatterns = rendicion_final_preview_patterns(build) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


def _login(nombre, *codes):
    usuario = get_user_model().objects.create_user(nombre)
    for code in codes:
        app, codename = code.split(".")
        usuario.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    client = Client()
    client.force_login(usuario)
    return client


@pytest.mark.usefixtures("preview")
@pytest.mark.parametrize("detalle", [False, True])
def test_both_screens_get_the_frozen_index(detalle):
    comedor = Comedor.objects.create(nombre="Uno")
    url = DETALLE.format(comedor.pk) if detalle else LISTADO
    client = _login("lector_prev_rf", VIEW)

    respuesta = client.get(url)

    assert respuesta.status_code == 200
    assert (
        '/rendicion_cuentas_final/react/assets/app-1.js"' in respuesta.content.decode()
    )
    assert "no-store" in respuesta["Cache-Control"]
    assert "csrftoken" in respuesta.cookies
    asset = client.get("/rendicion_cuentas_final/react/assets/app-1.js")
    assert asset.content == b"console.log(1);"


@pytest.mark.usefixtures("preview")
def test_native_guards_decide_first_and_the_detail_does_not_write():
    # The URL decorator answers before ``LoginRequiredMixin``: 403, not a redirect.
    comedor = Comedor.objects.create(nombre="Guard")
    for url in (LISTADO, DETALLE.format(comedor.pk)):
        assert Client().get(url).status_code == 403
        assert _login(f"sin_prev_rf{len(url)}").get(url).status_code == 403
    lector = _login("lector2_prev_rf", VIEW)
    assert lector.get(DETALLE.format(987654)).status_code == 404
    comedor = Comedor.objects.create(nombre="Sin rendicion")
    assert lector.get(DETALLE.format(comedor.pk)).status_code == 200
    # Only the API call creates the rendición (the native GET does).
    assert not RendicionCuentasFinal.objects.filter(comedor=comedor).exists()


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        rendicion_final_preview_patterns(tmp_path)
