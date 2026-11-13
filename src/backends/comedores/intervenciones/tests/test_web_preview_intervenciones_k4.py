"""Local React preview entries of the comedor interventions (``intervenciones.web_preview``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings
from django.utils import timezone

from catalogo_intervenciones.models import (
    TipoContacto,
    TipoDestinatario,
    TipoIntervencion,
)
from comedores.models import Comedor
from config.urls_all import urlpatterns as monolith_patterns
from intervenciones.models.intervenciones import Intervencion
from intervenciones.web_preview import intervenciones_preview_patterns

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
    module = types.ModuleType("intervenciones_preview_test_urls")
    module.urlpatterns = intervenciones_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


def _cliente(nombre, *codes):
    usuario = get_user_model().objects.create_user(nombre)
    for code in codes:
        app, codename = code.split(".")
        usuario.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="datos")
def datos_fixture():
    comedor = Comedor.objects.create(nombre="Comedor preview")
    intervencion = Intervencion.objects.create(
        comedor=comedor,
        tipo_intervencion=TipoIntervencion.objects.create(nombre="Visita"),
        destinatario=TipoDestinatario.objects.create(nombre="Titular"),
        forma_contacto=TipoContacto.objects.create(nombre="Presencial"),
        fecha=timezone.now(),
    )
    return comedor, intervencion


def _entradas(comedor, intervencion):
    return {
        f"/comedores/intervencion/ver/{comedor.pk}": "intervenciones.view_intervencion",
        f"/intervencion/detalle/{intervencion.pk}/": "intervenciones.view_intervencion",
        f"/comedores/intervencion/crear/{comedor.pk}": "intervenciones.add_intervencion",
        f"/comedores/intervencion/editar/{intervencion.pk}/{comedor.pk}": (
            "intervenciones.change_intervencion"
        ),
        f"/comedores/intervencion/borrar/{comedor.pk}/{intervencion.pk}/": (
            "comedores.delete_nomina"
        ),
    }


@pytest.mark.usefixtures("preview")
def test_every_entry_serves_the_frozen_index_with_its_native_permission(datos):
    entradas = _entradas(*datos)

    for url, permiso in entradas.items():
        respuesta = _cliente(f"u_{abs(hash(url))}", permiso).get(url)
        assert respuesta.status_code == 200, url
        assert '/intervenciones/react/assets/app-1.js"' in respuesta.content.decode()
        assert "no-store" in respuesta["Cache-Control"]
        assert "csrftoken" in respuesta.cookies
    asset = Client().get("/intervenciones/react/assets/app-1.js")
    assert asset.content == b"console.log(1);"


@pytest.mark.usefixtures("preview")
def test_native_guards_and_missing_objects_decide_first(datos):
    comedor, intervencion = datos
    sin_permiso = _cliente("sin_permiso_prev_k4")

    for url in _entradas(comedor, intervencion):
        assert Client().get(url).status_code == 403, url
        assert sin_permiso.get(url).status_code == 403, url
    root = get_user_model().objects.create_user("root_prev_k4", is_superuser=True)
    cliente = Client()
    cliente.force_login(root)
    for url in (
        "/comedores/intervencion/ver/999999",
        "/intervencion/detalle/999999/",
        "/comedores/intervencion/crear/999999",
        f"/comedores/intervencion/editar/999999/{comedor.pk}",
        f"/comedores/intervencion/editar/{intervencion.pk}/999999",
        f"/comedores/intervencion/borrar/{comedor.pk}/999999/",
    ):
        assert cliente.get(url).status_code == 404, url
