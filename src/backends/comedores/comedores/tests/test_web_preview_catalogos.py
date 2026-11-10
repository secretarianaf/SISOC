"""Local React preview entries of the Comedores catalogs (``comedores.web_preview_catalogos``)."""

import types
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from config.urls_all import urlpatterns as monolith_patterns
from comedores.web_preview_catalogos import catalogos_preview_patterns
from core.models import MontoPrestacionPrograma, Programa

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
MONTOS = (
    "/montoprestacion/listar",
    "/montoprestacion/crear",
    "/montoprestacion/{pk}/editar",
    "/montoprestacion/{pk}/eliminar",
    "/montoprestacion/{pk}/detalle",
)

pytestmark = pytest.mark.django_db


@pytest.fixture(name="build")
def build_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    (tmp_path / "assets" / "notes.txt").write_text("not served", encoding="utf-8")
    return tmp_path


@pytest.fixture(name="preview")
def preview_fixture(build):
    module = types.ModuleType("catalogos_preview_test_urls")
    module.urlpatterns = catalogos_preview_patterns(build) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.fixture(name="gestor")
def gestor_fixture():
    client = Client()
    client.force_login(get_user_model().objects.create_superuser("super_montos"))
    return client


@pytest.fixture(name="monto")
def monto_fixture():
    return MontoPrestacionPrograma.objects.create(
        programa=Programa.objects.create(nombre="Programa"),
        usuario_creador=get_user_model().objects.create_user("creador"),
        desayuno_valor=Decimal("1"),
    )


@pytest.mark.usefixtures("preview")
def test_every_montos_page_gets_the_frozen_index(gestor, monto):
    for url in MONTOS:
        respuesta = gestor.get(url.format(pk=monto.pk))
        assert respuesta.status_code == 200, url
        body = respuesta.content.decode()
        assert '/comedores/react/assets/app-1.js"' in body
        assert "/v2/sisoc/assets/" not in body
        assert "no-store" in respuesta["Cache-Control"]
        assert "Cookie" in respuesta["Vary"]
        assert "csrftoken" in respuesta.cookies
    assert gestor.head(MONTOS[0]).content == b""


@pytest.mark.usefixtures("preview")
def test_native_guards_still_decide_before_the_index(gestor, monto):
    client = Client()
    assert client.get(MONTOS[0]).status_code == 403
    usuario = get_user_model().objects.create_user("ve_montos")
    usuario.user_permissions.add(
        Permission.objects.get(codename="view_montoprestacionprograma")
    )
    client.force_login(usuario)
    for url in MONTOS:
        assert client.get(url.format(pk=monto.pk)).status_code == 403, url

    assert gestor.get(MONTOS[0], {"page": "9"}).status_code == 404
    for url in MONTOS[2:]:
        assert gestor.get(url.format(pk=999999)).status_code == 404, url


@pytest.mark.usefixtures("preview")
def test_only_frozen_assets_are_served(client):
    asset = client.get("/comedores/react/assets/app-1.js")

    assert asset.status_code == 200
    assert asset.content == b"console.log(1);"
    assert asset["Cache-Control"] == "public, max-age=31536000, immutable"
    assert asset["X-Content-Type-Options"] == "nosniff"
    assert client.get("/comedores/react/assets/app-1.js?x=1").status_code == 404
    assert client.get("/comedores/react/assets/notes.txt").status_code == 404
    assert client.post("/comedores/react/assets/app-1.js").status_code == 405


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        catalogos_preview_patterns(tmp_path)


def test_production_urlconf_keeps_the_native_pages(gestor, monto):
    respuesta = gestor.get(MONTOS[0])

    assert respuesta.status_code == 200
    assert "monto_prestacion_list.html" in [t.name for t in respuesta.templates]
