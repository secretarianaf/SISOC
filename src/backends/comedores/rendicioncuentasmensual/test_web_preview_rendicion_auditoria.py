"""Local React preview entries of the monthly rendición audit screens (RM01.03)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings
from django.utils import timezone

from config.urls_all import urlpatterns as monolith_patterns
from rendicioncuentasmensual.models import RendicionCuentaMensual
from rendicioncuentasmensual.web_preview import rendicion_preview_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
PREFIJO = "/rendicioncuentasmensual/rendicioncuentasmensual/auditoria/"
CODE = "rendicioncuentasmensual.manage_auditoria_stage"
R = RendicionCuentaMensual

pytestmark = pytest.mark.django_db


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("rendicion_auditoria_preview_test_urls")
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


def _disponible(mes=1, **extra):
    return R.objects.create(
        mes=mes,
        anio=2026,
        etapa_proceso=R.ETAPA_AUDITORIA,
        subestado_proceso=R.SUBESTADO_PENDIENTE,
        **extra,
    )


@pytest.mark.usefixtures("preview")
def test_search_and_form_get_the_frozen_index():
    rendicion = _disponible()
    client = _login("auditor_prev_aud", CODE)

    for ruta in (PREFIJO, f"{PREFIJO}{rendicion.pk}/"):
        respuesta = client.get(ruta)

        assert respuesta.status_code == 200
        assert (
            '/rendicioncuentasmensual/react/assets/app-1.js"'
            in respuesta.content.decode()
        )
        assert "csrftoken" in respuesta.cookies


@pytest.mark.usefixtures("preview")
def test_native_guards_redirect_and_404_decide_first():
    disponible = _disponible()
    cerrada = _disponible(2, fecha_auditada=timezone.now())
    auditor = _login("auditor2_prev_aud", CODE)
    lector = _login(
        "lector_prev_aud", "rendicioncuentasmensual.view_rendicioncuentamensual"
    )

    assert Client().get(PREFIJO).status_code == 403
    assert lector.get(PREFIJO).status_code == 403
    assert auditor.get(f"{PREFIJO}{cerrada.pk}/").status_code == 404
    assert auditor.get(f"{PREFIJO}{disponible.pk + 999}/").status_code == 404
    redireccion = auditor.get(f"{PREFIJO}?rendicion={disponible.pk}")
    assert redireccion.status_code == 302
    assert redireccion["Location"] == f"{PREFIJO}{disponible.pk}/"
    assert auditor.get(f"{PREFIJO}?rendicion=x").status_code == 404


@pytest.mark.usefixtures("preview")
def test_post_stays_the_native_action():
    rendicion = _disponible()
    auditor = _login("auditor3_prev_aud", CODE)

    respuesta = auditor.post(
        f"{PREFIJO}{rendicion.pk}/",
        {"validada": "on", "genera_acta_auditoria": "False"},
    )

    assert respuesta.status_code == 302
    rendicion.refresh_from_db()
    assert rendicion.validada is True
