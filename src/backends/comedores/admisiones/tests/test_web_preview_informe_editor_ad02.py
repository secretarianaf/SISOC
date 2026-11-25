"""Local React preview of the report editor pages (AD02.01, U3b)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings

from admisiones.models.admisiones import Admision, InformeTecnico
from admisiones.tests.test_web_api_informe_detalle_ad02 import (
    _cliente,
    _informe,
    _usuario,
)
from admisiones.web_preview_informes import informes_preview_patterns
from comedores.models import Comedor
from config.urls_all import urlpatterns as monolith_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
NATIVO = "/comedores/admision/informe_tecnico/"

pytestmark = pytest.mark.django_db


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("informe_editor_preview_test_urls")
    module.urlpatterns = informes_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.fixture(name="admision")
def admision_fixture():
    comedor = Comedor.objects.create(nombre="Comedor Preview Editor")
    return Admision.objects.create(comedor=comedor, tipo="incorporacion")


@pytest.mark.usefixtures("preview")
def test_editor_pages_get_the_frozen_index_after_the_native_guards(admision):
    informe = _informe(admision)
    web = _cliente(_usuario("editor_preview", "comedores.view_comedor"))
    sin_permiso = _cliente(get_user_model().objects.create_user("sin_permiso_ed"))

    for url in (
        f"{NATIVO}base/{admision.pk}/crear/",
        f"{NATIVO}base/{informe.pk}/editar/",
    ):
        respuesta = web.get(url)
        assert respuesta.status_code == 200, url
        assert '/comedores/react/assets/app-1.js"' in respuesta.content.decode()
        assert "csrftoken" in respuesta.cookies
        assert Client().get(url).status_code in (302, 403)
        assert sin_permiso.get(url).status_code == 403
    assert web.get(f"{NATIVO}base/999999/crear/").status_code == 404
    assert web.get(f"{NATIVO}base/999999/editar/").status_code == 404


@pytest.mark.usefixtures("preview")
def test_the_native_post_and_the_unavailable_type_stay_native(admision):
    web = _cliente(_usuario("editor_preview_post", "comedores.view_comedor"))

    guardado = web.post(
        f"{NATIVO}base/{admision.pk}/crear/",
        {"action": "draft", "expediente_nro": "EX-P"},
    )
    assert guardado.status_code == 302
    assert InformeTecnico.objects.get().expediente_nro == "EX-P"
    otro = web.get(f"{NATIVO}otro/{admision.pk}/crear/")
    assert otro.status_code == 302
    assert (
        otro["Location"].endswith("/tecnicos/editar/") or "tecnicos" in otro["Location"]
    )
