"""Local React preview entry of the CDI intervention detail (CDI06)."""

import types

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client, override_settings

from centrodeinfancia.models import CentroDeInfancia, IntervencionCentroInfancia
from centrodeinfancia.web_preview import cdi_preview_patterns
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
    module = types.ModuleType("cdi_preview_intervencion_urls")
    module.urlpatterns = cdi_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


def _cliente(username, *, con_permiso):
    user = User.objects.create_user(username)
    if con_permiso:
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="centrodeinfancia",
                codename="view_centrodeinfancia",
            )
        )
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.usefixtures("preview")
def test_intervention_detail_entry_returns_the_index_after_the_native_checks():
    centro = CentroDeInfancia.objects.create(nombre="CDI Preview")
    intervencion = IntervencionCentroInfancia.objects.create(centro=centro)
    ruta = f"/centrodeinfancia/intervencion/detalle/{intervencion.pk}/"
    operador = _cliente("preview-int", con_permiso=True)

    respuesta = operador.get(ruta)

    assert respuesta.status_code == 200
    assert b"/centrodeinfancia/react/assets/app-1.js" in respuesta.content
    assert "no-store" in respuesta["Cache-Control"]
    assert "csrftoken" in respuesta.cookies
    assert operador.head(ruta).content == b""
    assert (
        operador.get("/centrodeinfancia/intervencion/detalle/999999/").status_code
        == 404
    )
    assert _cliente("preview-int-sin", con_permiso=False).get(ruta).status_code == 403
    assert Client().get(ruta).status_code in (302, 401, 403)
    assert operador.post(ruta).status_code == 405
