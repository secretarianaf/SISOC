"""Local React preview entries of the comedor activities (``comedores.web_preview_actividades_espacio``)."""

import types
from datetime import time

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from comedores.models import Comedor, Programas
from comedores.web_preview_actividades_espacio import (
    actividades_espacio_preview_patterns,
)
from config.urls_all import urlpatterns as monolith_patterns
from core.models import Dia
from pwa.models import ActividadEspacioPWA, CatalogoActividadPWA

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
    module = types.ModuleType("actividades_espacio_preview_test_urls")
    module.urlpatterns = actividades_espacio_preview_patterns(tmp_path) + list(
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
    programa = Programas.objects.create(nombre="Programa PNUD preview")
    comedor = Comedor.objects.create(nombre="Comedor preview", programa=programa)
    actividad = ActividadEspacioPWA.objects.create(
        comedor=comedor,
        catalogo_actividad=CatalogoActividadPWA.objects.create(
            categoria="Zz Preview", actividad="Zz Taller preview"
        ),
        dia_actividad=Dia.objects.create(nombre="Lunes preview"),
        hora_inicio=time(9),
        hora_fin=time(10),
        horario_actividad="09:00 a 10:00",
    )
    return comedor, actividad


def _entradas(comedor, actividad):
    return [
        f"/comedores/{comedor.pk}/actividades/crear/",
        f"/comedores/{comedor.pk}/actividades/{actividad.pk}/editar/",
    ]


@pytest.mark.usefixtures("preview")
def test_every_entry_serves_the_frozen_index_with_its_native_permission(datos):
    for indice, url in enumerate(_entradas(*datos)):
        cliente = _cliente(
            f"u{indice}_act_k6", "pwa.manage_colaboradores_pwa", is_superuser=True
        )
        respuesta = cliente.get(url)
        assert respuesta.status_code == 200, url
        assert '/comedores/react/assets/app-1.js"' in respuesta.content.decode()
        assert "no-store" in respuesta["Cache-Control"]
        assert "csrftoken" in respuesta.cookies
    asset = Client().get("/comedores/react/assets/app-1.js")
    assert asset.content == b"console.log(1);"


@pytest.mark.usefixtures("preview")
def test_native_guards_pnud_rule_and_missing_objects_decide_first(datos):
    comedor, actividad = datos
    sin_permiso = _cliente("sin_permiso_act_k6")

    for url in _entradas(comedor, actividad):
        assert Client().get(url).status_code == 403, url
        assert sin_permiso.get(url).status_code == 403, url
    root = _cliente("root_act_k6", is_superuser=True)
    assert root.get("/comedores/999999/actividades/crear/").status_code == 404
    assert (
        root.get(f"/comedores/{comedor.pk}/actividades/999999/editar/").status_code
        == 404
    )
    comedor.programa = None  # no programa: not PNUD (ids 3 and 4 are PNUD by id)
    comedor.save()
    for url in _entradas(comedor, actividad):
        assert root.get(url).status_code == 404, url
