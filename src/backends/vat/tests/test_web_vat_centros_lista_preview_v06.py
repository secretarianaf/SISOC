"""V06.01: vista previa de las pantallas de centros e institución; cada entrada conserva la guarda nativa."""

import itertools
import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from config.urls_all import urlpatterns as monolith_patterns
from core.models import Localidad, Municipio, Provincia
from VAT.models import Centro, InstitucionContacto, ModalidadInstitucional
from VAT.web_preview_vat_centros_lista import ROUTES, centros_preview_patterns

pytestmark = pytest.mark.django_db

_COUNTER = itertools.count()
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)


def _client(*codes):
    user = get_user_model().objects.create_user(f"pv{next(_COUNTER)}")
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="VAT", codename__in=codes)
    )
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("vat_centros_lista_preview_test_urls")
    module.urlpatterns = centros_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


def crear_centro():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)
    localidad = Localidad.objects.create(nombre="Tolosa", municipio=municipio)
    return Centro.objects.create(
        nombre="CFP 401",
        codigo="060144900",
        provincia=provincia,
        municipio=municipio,
        localidad=localidad,
    )


def _pks():
    centro = crear_centro()
    return {
        ModalidadInstitucional: ModalidadInstitucional.objects.create(nombre="M").pk,
        InstitucionContacto: InstitucionContacto.objects.create(
            centro=centro, tipo="email", valor="a@b.com"
        ).pk,
    }


@pytest.mark.usefixtures("preview")
def test_entries_serve_the_frozen_index_behind_the_native_guards():
    pks = _pks()
    for route, view, permission, _kind in ROUTES:
        url = "/" + route.replace("<int:pk>", str(pks[view.model]))
        response = _client(permission.split(".")[1]).get(url)
        assert response.status_code == 200, url
        body = response.content.decode()
        assert '/vat/react/assets/app-1.js"' in body and "/v2/sisoc/assets/" not in body
        assert "no-store" in response["Cache-Control"]
        assert "csrftoken" in response.cookies
        assert Client().get(url).status_code == 403, url
        assert _client("view_sector").get(url).status_code == 403, url
        if "<int:pk>" in route:
            missing = "/" + route.replace("<int:pk>", "999999")
            assert _client(permission.split(".")[1]).get(missing).status_code == 404
    lista = "/vat/modalidades-institucionales/"
    assert (
        _client("view_modalidadinstitucional").get(lista, {"page": 9}).status_code
        == 404
    )
