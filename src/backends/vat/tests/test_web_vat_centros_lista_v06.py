"""V06.01/V06.02: web API de la lista y la baja de centros (``/api/web/vat/centros-lista/``). Datos sintéticos."""

import itertools
import json
import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings
from rest_framework.test import APIClient

from config.urls_all import urlpatterns as monolith_patterns
from core.models import Localidad, Municipio, Provincia
from VAT.models import Centro
from VAT.web_preview_vat_centros_lista import centros_preview_patterns

pytestmark = pytest.mark.django_db

ROOT = "/api/web/vat/centros-lista/"
NATIVA = "/vat/centros/"
MENSAJE = "Centro dado de baja correctamente."
_COUNTER = itertools.count()
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)


def _client(*codes, sse=False, referente=False, csrf=False):
    user = get_user_model().objects.create_user(f"cl{next(_COUNTER)}")
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="VAT", codename__in=codes)
    )
    for activo, rol in ((sse, "role_vat_sse"), (referente, "role_referentecentrovat")):
        if activo:
            permiso, _ = Permission.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(Group),
                codename=rol,
                defaults={"name": rol},
            )
            user.user_permissions.add(permiso)
    client = APIClient(enforce_csrf_checks=csrf)
    client.force_login(user)
    client.user = user
    return client


def _centro(nombre="CFP 401", **extra):
    provincia, _ = Provincia.objects.get_or_create(nombre="Buenos Aires")
    municipio, _ = Municipio.objects.get_or_create(
        nombre="La Plata", provincia=provincia
    )
    localidad, _ = Localidad.objects.get_or_create(nombre="Tolosa", municipio=municipio)
    datos = {
        "codigo": f"06{next(_COUNTER):07d}",
        "provincia": provincia,
        "municipio": municipio,
        "localidad": localidad,
        **extra,
    }
    return Centro.objects.create(nombre=nombre, **datos)


def test_access_follows_each_native_route_rule():
    centro = _centro()
    for url in (ROOT, f"{ROOT}{centro.pk}/eliminar/"):
        assert APIClient().get(url).status_code == 401
        assert _client("view_sector").get(url).status_code == 403
    assert _client("view_centro").get(ROOT).status_code == 200
    # the native delete view also asks for the SSE role or the centro's own referente
    assert _client("view_centro").get(f"{ROOT}{centro.pk}/eliminar/").status_code == 403
    assert (
        _client("view_centro", sse=True).get(f"{ROOT}{centro.pk}/eliminar/").status_code
        == 200
    )
    assert (
        _client("view_centro", sse=True).get(f"{ROOT}999999/eliminar/").status_code
        == 404
    )


def test_list_projects_the_native_rows_and_what_each_user_may_do():
    centro = _centro(calle="Calle 12", telefono="221 555", activo=True)
    _centro("CFP 402", activo=False)
    client = _client("view_centro", "delete_centro", sse=True)
    data = client.get(ROOT).json()
    assert data["can_add"] is True
    assert data["permisos"] == {"eliminar": True}
    assert data["urls"] == {"list": NATIVA, "create": f"{NATIVA}nuevo/"}
    fila = {r["id"]: r for r in data["results"]}[centro.pk]
    assert (fila["nombre"], fila["calle"], fila["telefono"], fila["activo"]) == (
        "CFP 401",
        "Calle 12",
        "221 555",
        True,
    )
    assert fila["detail_url"] == f"{NATIVA}{centro.pk}/"
    assert fila["update_url"] == f"{NATIVA}{centro.pk}/editar/"
    assert fila["delete_url"] == f"{NATIVA}{centro.pk}/eliminar/"
    assert data["page"]["is_paginated"] is False
    assert data["favorites"]["section"] == "vat_centros"
    assert data["messages"] == []
    # a referente sees only the centros assigned to it and neither the add button nor the delete form
    asignado = _centro("CFP 500")
    referente = _client("view_centro", referente=True)
    asignado.referente = referente.user
    asignado.save()
    propio = referente.get(ROOT).json()
    assert [r["nombre"] for r in propio["results"]] == ["CFP 500"]
    assert (propio["can_add"], propio["permisos"]) == (False, {"eliminar": False})


def test_list_filters_search_and_exact_pages_without_a_count():
    for numero in range(11):
        _centro(f"Centro {numero:02d}")
    client = _client("view_centro", sse=True)
    primera = client.get(ROOT, {"busqueda": "Centro", "otro": "a b"}).json()
    assert len(primera["results"]) == 10
    assert primera["page"]["is_paginated"] is True
    assert (
        primera["page"]["number"],
        primera["page"]["previous"],
        primera["page"]["next"],
    ) == (1, None, 2)
    assert primera["page"]["query_prefix"] == "busqueda=Centro&otro=a%20b&"
    segunda = client.get(ROOT, {"busqueda": "Centro", "page": 2}).json()
    assert len(segunda["results"]) == 1
    assert (segunda["page"]["previous"], segunda["page"]["next"]) == (1, None)
    assert segunda["page"]["range"] == [1, 2]
    filtro = json.dumps(
        {
            "logic": "AND",
            "items": [{"field": "nombre", "op": "eq", "value": "Centro 03"}],
        }
    )
    assert [
        r["nombre"] for r in client.get(ROOT, {"filters": filtro}).json()["results"]
    ] == ["Centro 03"]
    vacia = client.get(ROOT, {"busqueda": "no existe", "page": 3}).json()
    assert vacia["results"] == []
    assert vacia["page"]["range"] == []


def test_filters_config_options_are_the_strings_the_page_script_reads():
    campos = {
        c["name"]: c
        for c in _client("view_centro").get(ROOT).json()["filters_config"]["fields"]
    }
    assert [o["value"] for o in campos["estado_carga"]["options"]] == ["true", "false"]
    assert "options" not in campos["nombre"]


def test_delete_get_projects_the_cascade_preview_and_post_removes_the_centro():
    centro = _centro("CFP 401")
    client = _client("view_centro", sse=True)
    url = f"{ROOT}{centro.pk}/eliminar/"
    data = client.get(url).json()
    assert (data["id"], data["nombre"]) == (centro.pk, "CFP 401")
    assert data["preview"]["total_afectados"] >= 1
    assert (data["confirm_text"], data["cancel_text"]) == ("Dar de baja", "Cancelar")
    assert data["urls"] == {"detail": f"{NATIVA}{centro.pk}/"}
    respuesta = client.post(url)
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": NATIVA}
    assert not Centro.objects.filter(pk=centro.pk).exists()
    assert [m["message"] for m in client.get(ROOT).json()["messages"]] == [MENSAJE]


def test_delete_rejections_leave_the_centro_untouched():
    centro = _centro()
    url = f"{ROOT}{centro.pk}/eliminar/"
    assert _client("view_centro", sse=True, csrf=True).post(url).status_code == 403
    assert APIClient().post(url).status_code == 401
    assert _client("view_centro").post(url).status_code == 403
    assert (
        _client("view_centro", sse=True).post(f"{ROOT}999999/eliminar/").status_code
        == 404
    )
    assert Centro.objects.filter(pk=centro.pk).exists()


def test_the_referente_of_a_centro_may_delete_it():
    centro = _centro()
    referente = _client("view_centro", referente=True)
    centro.referente = referente.user
    centro.save()
    assert referente.post(f"{ROOT}{centro.pk}/eliminar/").status_code == 200
    assert not Centro.objects.filter(pk=centro.pk).exists()


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("vat_centros_baja_preview_test_urls")
    module.urlpatterns = centros_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_preview_entries_serve_the_index_behind_the_native_guards():
    centro = _centro()
    lista = _client("view_centro")
    assert Client().get(NATIVA).status_code == 403
    assert _client("view_sector").get(NATIVA).status_code == 403
    respuesta = lista.get(NATIVA)
    assert respuesta.status_code == 200
    assert '/vat/react/assets/app-1.js"' in respuesta.content.decode()
    assert "no-store" in respuesta["Cache-Control"]
    baja = f"{NATIVA}{centro.pk}/eliminar/"
    assert lista.get(baja).status_code == 403
    assert _client("view_centro", sse=True).get(baja).status_code == 200
    assert (
        _client("view_centro", sse=True).get(f"{NATIVA}999999/eliminar/").status_code
        == 404
    )
