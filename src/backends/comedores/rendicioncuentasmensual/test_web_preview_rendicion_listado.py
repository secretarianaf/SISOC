"""Local React preview entry of RM01.01 (``rendicioncuentasmensual.web_preview``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings

from config.urls_all import urlpatterns as monolith_patterns
from rendicioncuentasmensual.models import RendicionCuentaMensual
from rendicioncuentasmensual.web_preview import rendicion_preview_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
LISTADO = "/rendicioncuentasmensual/rendicioncuentasmensual/listado/"

pytestmark = pytest.mark.django_db


@pytest.fixture(name="build")
def build_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    return tmp_path


@pytest.fixture(name="preview")
def preview_fixture(build):
    module = types.ModuleType("rendicion_preview_test_urls")
    module.urlpatterns = rendicion_preview_patterns(build) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


def _login(nombre, *codes):
    usuario = get_user_model().objects.create_user(nombre)
    for code in codes:
        app, codename = code.split(".")
        if app == "auth":
            permiso = Permission.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(Group),
                codename=codename,
                defaults={"name": codename},
            )[0]
        else:
            permiso = Permission.objects.get(
                content_type__app_label=app, codename=codename
            )
        usuario.user_permissions.add(permiso)
    client = Client()
    client.force_login(usuario)
    return client


@pytest.mark.usefixtures("preview")
def test_the_list_gets_the_frozen_index():
    client = _login(
        "lector_prev_rm", "rendicioncuentasmensual.manage_territorial_stage"
    )

    respuesta = client.get(LISTADO, {"filters": '{"items": []}', "page": "1"})

    assert respuesta.status_code == 200
    assert (
        '/rendicioncuentasmensual/react/assets/app-1.js"' in respuesta.content.decode()
    )
    assert "no-store" in respuesta["Cache-Control"]
    assert "csrftoken" in respuesta.cookies
    asset = client.get("/rendicioncuentasmensual/react/assets/app-1.js")
    assert asset.content == b"console.log(1);"


@pytest.mark.usefixtures("preview")
def test_native_guards_decide_first():
    # The URL decorator answers before ``LoginRequiredMixin``: 403, not a redirect.
    assert Client().get(LISTADO).status_code == 403
    assert _login("sin_prev_rm").get(LISTADO).status_code == 403
    lector = _login(
        "lector2_prev_rm", "rendicioncuentasmensual.view_rendicioncuentamensual"
    )
    assert lector.get(LISTADO, {"page": "9"}).status_code == 404
    assert lector.get(LISTADO, {"page": "x"}).status_code == 404


@pytest.mark.usefixtures("preview")
def test_the_csv_stays_the_native_download():
    RendicionCuentaMensual.objects.create(mes=1, anio=2026)
    lector = _login(
        "lector3_prev_rm", "rendicioncuentasmensual.view_rendicioncuentamensual"
    )
    assert lector.get(LISTADO, {"export": "csv"}).status_code == 403
    exporta = _login(
        "exporta_prev_rm",
        "rendicioncuentasmensual.view_rendicioncuentamensual",
        "auth.role_exportar_a_csv",
    )

    respuesta = exporta.get(LISTADO, {"export": "csv"})

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"].startswith("text/csv")
    assert 'filename="exportacion_rendiciones_' in respuesta["Content-Disposition"]


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        rendicion_preview_patterns(tmp_path)
