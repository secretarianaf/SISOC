"""Local React preview entries of EX01 (``expedientespagos.web_preview``)."""

import types
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from comedores.models import Comedor
from config.urls_all import urlpatterns as monolith_patterns
from expedientespagos.models import ExpedientePago
from expedientespagos.web_preview import expedientes_preview_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
BASE = "/expedientespagos/expedientespagos/"

pytestmark = pytest.mark.django_db


@pytest.fixture(name="build")
def build_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    return tmp_path


@pytest.fixture(name="preview")
def preview_fixture(build):
    module = types.ModuleType("expedientes_preview_test_urls")
    module.urlpatterns = expedientes_preview_patterns(build) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


def _login(nombre, *codenames):
    usuario = get_user_model().objects.create_user(nombre)
    for codename in codenames:
        usuario.user_permissions.add(Permission.objects.get(codename=codename))
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="expediente")
def expediente_fixture():
    comedor = Comedor.objects.create(nombre="Comedor preview")
    return ExpedientePago.objects.create(
        comedor=comedor,
        expediente_convenio="EC",
        **{
            f"prestaciones_mensuales_{c}": 1
            for c in ("desayuno", "almuerzo", "merienda", "cena")
        },
        **{
            f"monto_mensual_{c}": Decimal("1")
            for c in ("desayuno", "almuerzo", "merienda", "cena")
        },
    )


def _urls(expediente):
    return (
        f"{BASE}{expediente.comedor_id}/",
        f"{BASE}{expediente.pk}/detalle/",
        f"{BASE}{expediente.comedor_id}/nuevo/",
        f"{BASE}{expediente.pk}/editar/",
        f"{BASE}{expediente.pk}/eliminar/",
    )


@pytest.mark.usefixtures("preview")
def test_every_page_gets_the_frozen_index(expediente):
    client = _login("lector_prev_exp", "view_expedientepago")
    for url in _urls(expediente):
        respuesta = client.get(url)
        assert respuesta.status_code == 200, url
        assert '/expedientespagos/react/assets/app-1.js"' in respuesta.content.decode()
        assert "no-store" in respuesta["Cache-Control"]
        assert "csrftoken" in respuesta.cookies
    assert client.get("/expedientespagos/react/assets/app-1.js").content == (
        b"console.log(1);"
    )


@pytest.mark.usefixtures("preview")
def test_native_guards_decide_first(expediente):
    lista, detalle, nuevo, editar, eliminar = _urls(expediente)
    anonimo = Client()
    assert anonimo.get(lista).status_code == 302
    assert anonimo.get(detalle).status_code == 302
    for url in (nuevo, editar, eliminar):
        assert anonimo.get(url).status_code == 403, url
    sin_codigos = _login("sin_codigos_prev_exp")
    assert sin_codigos.get(lista).status_code == 200
    assert sin_codigos.get(detalle).status_code == 200
    for url in (nuevo, editar, eliminar):
        assert sin_codigos.get(url).status_code == 403, url
    lector = _login("lector2_prev_exp", "view_expedientepago")
    assert lector.get(lista, {"page": "9"}).status_code == 404
    assert lector.get(f"{BASE}999999/detalle/").status_code == 404
    assert lector.get(f"{BASE}999999/editar/").status_code == 404


@pytest.mark.usefixtures("preview")
def test_posts_still_reach_the_native_views(expediente):
    lector = _login("lector3_prev_exp", "view_expedientepago")
    respuesta = lector.post(f"{BASE}{expediente.pk}/eliminar/")
    assert respuesta.status_code == 302
    assert respuesta["Location"] == "/acompanamientos/acompanamiento/"
    assert not ExpedientePago.objects.filter(pk=expediente.pk).exists()


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        expedientes_preview_patterns(tmp_path)
