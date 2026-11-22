"""Local React preview entries of AC01 (``acompanamientos.web_preview``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from acompanamientos.models.acompanamiento import Acompanamiento
from acompanamientos.models.hitos import Hitos
from acompanamientos.web_preview import acompanamientos_preview_patterns
from admisiones.models.admisiones import Admision
from comedores.models import Comedor
from config.urls_all import urlpatterns as monolith_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
LISTA = "/acompanamientos/acompanamiento/"

pytestmark = pytest.mark.django_db


@pytest.fixture(name="build")
def build_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    return tmp_path


@pytest.fixture(name="preview")
def preview_fixture(build):
    module = types.ModuleType("acompanamientos_preview_test_urls")
    module.urlpatterns = acompanamientos_preview_patterns(build) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.fixture(name="lector")
def lector_fixture():
    usuario = get_user_model().objects.create_user("lector_preview_acomp")
    usuario.user_permissions.add(
        Permission.objects.get(codename="view_informacionrelevante")
    )
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="comedor")
def comedor_fixture():
    comedor = Comedor.objects.create(nombre="Comedor preview")
    admision = Admision.objects.create(
        comedor=comedor, activa=True, enviado_acompaniamiento=True
    )
    Hitos.objects.create(
        acompanamiento=Acompanamiento.objects.create(admision=admision),
        retiro_tarjeta=True,
    )
    return comedor


@pytest.mark.usefixtures("preview")
def test_list_and_ficha_get_the_frozen_index(lector, comedor):
    for url in (LISTA, f"{LISTA}{comedor.pk}/detalle/"):
        respuesta = lector.get(url)
        assert respuesta.status_code == 200, url
        body = respuesta.content.decode()
        assert '/acompanamientos/react/assets/app-1.js"' in body
        assert "no-store" in respuesta["Cache-Control"]
        assert "Cookie" in respuesta["Vary"]
        assert "csrftoken" in respuesta.cookies
    asset = lector.get("/acompanamientos/react/assets/app-1.js")
    assert asset.content == b"console.log(1);"


@pytest.mark.usefixtures("preview")
def test_native_guards_scope_and_pages_decide_first(lector, comedor):
    sin_permiso = Client()
    sin_permiso.force_login(get_user_model().objects.create_user("sin_permiso_prev"))
    for url in (LISTA, f"{LISTA}{comedor.pk}/detalle/"):
        assert Client().get(url).status_code == 403, url
        assert sin_permiso.get(url).status_code == 403, url
    assert lector.get(LISTA, {"page": "5"}).status_code == 404
    assert lector.get(f"{LISTA}999999/detalle/").status_code == 404


@pytest.mark.usefixtures("preview")
def test_export_and_native_restore_stay_native(lector, comedor):
    assert lector.get(f"{LISTA}exportar/").status_code == 403
    respuesta = lector.post(
        f"/acompanamientos/comedor/{comedor.pk}/restaurar-hito/",
        {"campo": "retiro_tarjeta"},
    )
    assert respuesta.status_code == 403
    assert Hitos.objects.get().retiro_tarjeta is True


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        acompanamientos_preview_patterns(tmp_path)
