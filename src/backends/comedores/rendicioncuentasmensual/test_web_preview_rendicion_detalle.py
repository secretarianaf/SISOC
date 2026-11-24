"""Local React preview entry of the monthly rendición detail (RM01.01)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from config.urls_all import urlpatterns as monolith_patterns
from rendicioncuentasmensual.models import RendicionCuentaMensual
from rendicioncuentasmensual.web_preview import rendicion_preview_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
DETALLE = "/rendicioncuentasmensual/rendicioncuentasmensual/detalle/{}/"
R = RendicionCuentaMensual

pytestmark = pytest.mark.django_db


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("rendicion_detalle_preview_test_urls")
    module.urlpatterns = rendicion_preview_patterns(tmp_path) + list(monolith_patterns)
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
def test_the_detail_gets_the_frozen_index():
    rendicion = R.objects.create(mes=1, anio=2026)
    client = _login(
        "lector_prev_det", "rendicioncuentasmensual.view_rendicioncuentamensual"
    )

    respuesta = client.get(DETALLE.format(rendicion.pk))

    assert respuesta.status_code == 200
    assert (
        '/rendicioncuentasmensual/react/assets/app-1.js"' in respuesta.content.decode()
    )
    assert "no-store" in respuesta["Cache-Control"]
    assert "csrftoken" in respuesta.cookies


@pytest.mark.usefixtures("preview")
def test_native_guards_decide_first():
    rendicion = R.objects.create(mes=1, anio=2026)
    borrada = R.objects.create(mes=2, anio=2026)
    borrada.delete()
    lector = _login(
        "lector2_prev_det", "rendicioncuentasmensual.manage_territorial_stage"
    )

    assert Client().get(DETALLE.format(rendicion.pk)).status_code == 403
    assert _login("sin_prev_det").get(DETALLE.format(rendicion.pk)).status_code == 403
    assert lector.get(DETALLE.format(borrada.pk)).status_code == 404
    assert lector.get(DETALLE.format(rendicion.pk + 999)).status_code == 404


@pytest.mark.usefixtures("preview")
def test_posts_stay_the_native_actions():
    rendicion = R.objects.create(
        mes=1,
        anio=2026,
        etapa_proceso=R.ETAPA_REVISION_DOCUMENTACION,
        subestado_proceso=R.SUBESTADO_PENDIENTE,
    )
    territorial = _login(
        "territorial_prev_det", "rendicioncuentasmensual.manage_territorial_stage"
    )
    lector = _login(
        "lector3_prev_det", "rendicioncuentasmensual.view_rendicioncuentamensual"
    )

    denegado = lector.post(
        DETALLE.format(rendicion.pk),
        {"accion_proceso": "iniciar_revision_territorial"},
    )
    respuesta = territorial.post(
        DETALLE.format(rendicion.pk),
        {"accion_proceso": "iniciar_revision_territorial"},
    )

    assert denegado.status_code == 403
    assert respuesta.status_code == 302
    assert respuesta["Location"] == DETALLE.format(rendicion.pk)
    rendicion.refresh_from_db()
    assert rendicion.subestado_proceso == R.SUBESTADO_EN_CURSO
