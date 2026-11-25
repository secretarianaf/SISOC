"""Local React preview entries of the monthly rendición form screens (RM01.02)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from comedores.models import Comedor
from config.urls_all import urlpatterns as monolith_patterns
from organizaciones.models import Organizacion
from rendicioncuentasmensual.models import RendicionCuentaMensual
from rendicioncuentasmensual.web_preview import rendicion_preview_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
PREFIJO = "/rendicioncuentasmensual/rendicioncuentasmensual"
VER = "rendicioncuentasmensual.view_rendicioncuentamensual"
EDITAR = "rendicioncuentasmensual.edit_rendicion_data"
R = RendicionCuentaMensual

pytestmark = pytest.mark.django_db


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("rendicion_form_preview_test_urls")
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
def test_each_form_gets_the_frozen_index():
    rendicion = R.objects.create(mes=1, anio=2026)
    client = _login("editor_prev_form", VER, EDITAR)

    for ruta in (
        f"{PREFIJO}/nuevo/7/",
        f"{PREFIJO}/editar/{rendicion.pk}/",
        f"{PREFIJO}/eliminar/{rendicion.pk}/",
    ):
        respuesta = client.get(ruta)

        assert respuesta.status_code == 200
        assert (
            '/rendicioncuentasmensual/react/assets/app-1.js"'
            in respuesta.content.decode()
        )
        assert "no-store" in respuesta["Cache-Control"]
        assert "csrftoken" in respuesta.cookies


@pytest.mark.usefixtures("preview")
def test_native_guards_decide_first():
    rendicion = R.objects.create(mes=1, anio=2026)
    borrada = R.objects.create(mes=2, anio=2026)
    borrada.delete()
    lector = _login("lector_prev_form", VER)
    editor = _login("editor2_prev_form", VER, EDITAR)
    otro = _login("etapa_prev_form", "rendicioncuentasmensual.manage_territorial_stage")

    for ruta in ("nuevo/7", f"editar/{rendicion.pk}", f"eliminar/{rendicion.pk}"):
        assert Client().get(f"{PREFIJO}/{ruta}/").status_code == 403
        assert otro.get(f"{PREFIJO}/{ruta}/").status_code == 403
    assert lector.get(f"{PREFIJO}/editar/{rendicion.pk}/").status_code == 403
    for ruta in ("editar", "eliminar"):
        assert editor.get(f"{PREFIJO}/{ruta}/{borrada.pk}/").status_code == 404
        assert editor.get(f"{PREFIJO}/{ruta}/{rendicion.pk + 999}/").status_code == 404


@pytest.mark.usefixtures("preview")
def test_posts_stay_the_native_actions():
    organizacion = Organizacion.objects.create(nombre="Org preview form")
    comedor = Comedor.objects.create(
        nombre="Comedor preview form", organizacion=organizacion
    )
    rendicion = R.objects.create(comedor=comedor, mes=1, anio=2026)
    editor = _login("editor3_prev_form", VER, EDITAR)

    guardada = editor.post(f"{PREFIJO}/editar/{rendicion.pk}/", {"nombre": "Nuevo"})
    baja = editor.post(f"{PREFIJO}/eliminar/{rendicion.pk}/")

    assert guardada.status_code == 302
    assert guardada["Location"] == f"{PREFIJO}/detalle/{rendicion.pk}/"
    assert baja.status_code == 302
    assert R.objects.filter(pk=rendicion.pk).count() == 0
