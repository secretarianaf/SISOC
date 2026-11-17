"""Local React preview entries of the "Agregar a Nómina" screen (``comedores.web_preview_nomina_crear``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from admisiones.models.admisiones import Admision
from comedores.models import Comedor, Programas
from comedores.web_preview_nomina_crear import nomina_crear_preview_patterns
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
    module = types.ModuleType("nomina_crear_preview_test_urls")
    module.urlpatterns = nomina_crear_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


def _cliente(nombre, *codes, **extra):
    usuario = get_user_model().objects.create_user(nombre, **extra)
    for code in codes:
        app, codename = code.split(".")
        usuario.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    client = Client()
    client.force_login(usuario)
    return client


def _entradas():
    programa = Programas.objects.create(
        nombre="Programa directo preview", usa_admision_para_nomina=False
    )
    directa = Comedor.objects.create(nombre="Directa preview", programa=programa)
    comedor = Comedor.objects.create(nombre="Con admision preview")
    admision = Admision.objects.create(comedor=comedor)
    return directa, comedor, admision


@pytest.mark.usefixtures("preview")
def test_both_entries_serve_the_frozen_index_with_their_native_permission():
    directa, comedor, admision = _entradas()
    cliente = _cliente("u_nomina_crear_co01", "comedores.add_nomina")

    for url in (
        f"/comedores/{directa.pk}/nomina/crear/",
        f"/comedores/{comedor.pk}/admision/{admision.pk}/nomina/crear/",
    ):
        respuesta = cliente.get(url)
        assert respuesta.status_code == 200, url
        assert (
            '/comedores/nomina-crear/react/assets/app-1.js"'
            in respuesta.content.decode()
        )
        assert "no-store" in respuesta["Cache-Control"]
        assert "csrftoken" in respuesta.cookies
    asset = Client().get("/comedores/nomina-crear/react/assets/app-1.js")
    assert asset.content == b"console.log(1);"


@pytest.mark.usefixtures("preview")
def test_native_guards_and_scoped_lookups_decide_first():
    directa, comedor, admision = _entradas()
    sin_permiso = _cliente("sin_permiso_nomina_crear_co01")
    root = _cliente("root_nomina_crear_co01", is_superuser=True)

    for url in (
        f"/comedores/{directa.pk}/nomina/crear/",
        f"/comedores/{comedor.pk}/admision/{admision.pk}/nomina/crear/",
    ):
        assert Client().get(url).status_code in (302, 403), url
        assert sin_permiso.get(url).status_code == 403, url
    # A direct nómina of a comedor that needs an admission, and missing objects: 404.
    assert root.get(f"/comedores/{comedor.pk}/nomina/crear/").status_code == 404
    assert root.get(f"/comedores/999999/nomina/crear/").status_code == 404
    assert (
        root.get(
            f"/comedores/{directa.pk}/admision/{admision.pk}/nomina/crear/"
        ).status_code
        == 404
    )
