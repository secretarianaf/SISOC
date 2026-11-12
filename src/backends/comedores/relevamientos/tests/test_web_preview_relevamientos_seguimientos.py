"""Local React preview entries of R03.01 and R02.01 (``relevamientos.web_preview``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from comedores.models import Comedor
from config.urls_all import urlpatterns as monolith_patterns
from relevamientos.models import (
    ActaComplementaria,
    PrimerSeguimiento,
    Relevamiento,
    SeguimientoPnud,
)
from relevamientos.web_preview import relevamientos_preview_patterns

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
    module = types.ModuleType("relevamientos_seg_preview_test_urls")
    module.urlpatterns = relevamientos_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
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


def _datos():
    comedor = Comedor.objects.create(nombre="Prev seg")
    relevamiento = Relevamiento.objects.create(comedor=comedor)
    seguimiento = PrimerSeguimiento.objects.create(id_relevamiento=relevamiento)
    pnud = SeguimientoPnud.objects.create(comedor=comedor, formulario="iia")
    acta = ActaComplementaria.objects.create(comedor=comedor)
    base = f"/comedores/{comedor.pk}"
    return {
        "seguimiento": f"{base}/relevamiento/{relevamiento.pk}/seguimiento/{seguimiento.pk}/",
        "alias": f"{base}/relevamiento/{relevamiento.pk}/primer-seguimiento/",
        "pnud": f"{base}/seguimiento-pnud/{pnud.pk}",
        "acta": f"{base}/acta-complementaria/{acta.pk}",
        "vacio": f"{base}/relevamiento/{Relevamiento.objects.create(comedor=comedor).pk}/primer-seguimiento/",
    }


@pytest.mark.usefixtures("preview")
def test_the_details_get_the_frozen_index():
    urls = _datos()
    client = _login("lector_prev_seg")

    for clave in ("seguimiento", "alias", "pnud", "acta"):
        respuesta = client.get(urls[clave])
        assert respuesta.status_code == 200, clave
        assert (
            '/comedores/react/relevamientos/assets/app-1.js"'
            in respuesta.content.decode()
        )
        assert "csrftoken" in respuesta.cookies


@pytest.mark.usefixtures("preview")
def test_native_guards_and_404s_decide_first():
    urls = _datos()

    assert Client().get(urls["seguimiento"]).status_code == 403
    assert _login("sin_prev_seg", False).get(urls["acta"]).status_code == 403
    lector = _login("lector2_prev_seg")
    assert lector.get(urls["vacio"]).status_code == 404
    assert (
        lector.get(
            urls["pnud"].replace("seguimiento-pnud/", "seguimiento-pnud/9")
        ).status_code
        == 404
    )
    assert lector.get(urls["acta"] + "9").status_code == 404
