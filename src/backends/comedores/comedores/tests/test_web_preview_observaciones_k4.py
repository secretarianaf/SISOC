"""Local React preview entries of the comedor observations (``comedores.web_preview_observaciones``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings
from django.utils import timezone

from comedores.models import Comedor, Observacion
from comedores.web_preview_observaciones import observaciones_preview_patterns
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
    module = types.ModuleType("observaciones_preview_test_urls")
    module.urlpatterns = observaciones_preview_patterns(tmp_path) + list(
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


@pytest.fixture(name="datos")
def datos_fixture():
    comedor = Comedor.objects.create(nombre="Comedor preview")
    observacion = Observacion.objects.create(
        comedor=comedor, observacion="Texto", fecha_visita=timezone.now()
    )
    return comedor, observacion


def _entradas(comedor, observacion):
    return {
        f"/comedores/{comedor.pk}/observacion/crear": "comedores.add_observacion",
        f"/comedores/observacion/{observacion.pk}": "comedores.view_observacion",
        f"/comedores/observacion/{observacion.pk}/editar": (
            "comedores.change_observacion"
        ),
        f"/comedores/observacion/{observacion.pk}/eliminar": (
            "comedores.delete_observacion"
        ),
    }


@pytest.mark.usefixtures("preview")
def test_every_entry_serves_the_frozen_index_with_its_native_permission(datos):
    for indice, (url, permiso) in enumerate(_entradas(*datos).items()):
        respuesta = _cliente(f"u{indice}_obs_k4", permiso).get(url)
        assert respuesta.status_code == 200, url
        assert '/observaciones/react/assets/app-1.js"' in respuesta.content.decode()
        assert "no-store" in respuesta["Cache-Control"]
        assert "csrftoken" in respuesta.cookies
    asset = Client().get("/observaciones/react/assets/app-1.js")
    assert asset.content == b"console.log(1);"


@pytest.mark.usefixtures("preview")
def test_native_guards_and_missing_objects_decide_first(datos):
    comedor, observacion = datos
    sin_permiso = _cliente("sin_permiso_obs_k4")

    for url in _entradas(comedor, observacion):
        assert Client().get(url).status_code == 403, url
        assert sin_permiso.get(url).status_code == 403, url
    root = _cliente("root_obs_k4", is_superuser=True)
    for url in (
        "/comedores/999999/observacion/crear",
        "/comedores/observacion/999999",
        "/comedores/observacion/999999/editar",
        "/comedores/observacion/999999/eliminar",
    ):
        assert root.get(url).status_code == 404, url
