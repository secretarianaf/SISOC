"""V04.01 (U4): web API and preview entry of the commission list (``/api/web/vat/comisiones-lista/``). Synthetic data."""

import itertools
import types
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings
from django.utils.html import escape
from rest_framework.test import APIClient

from config.urls_all import urlpatterns as monolith_patterns
from core.models import Programa, Provincia
from VAT.models import (
    Centro,
    Comision,
    ModalidadCursada,
    OfertaInstitucional,
    PlanVersionCurricular,
    Sector,
    TituloReferencia,
)
from VAT.web_preview_vat_comision_lista import comision_lista_preview_patterns

pytestmark = pytest.mark.django_db

_COUNTER = itertools.count()
ROOT = "/api/web/vat/comisiones-lista/"
NATIVA = "/vat/comisiones/"
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)


def _client(*codes, sse=False, csrf=False):
    user = get_user_model().objects.create_user(f"cl{next(_COUNTER)}")
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="VAT", codename__in=codes)
    )
    if sse:
        permiso, _ = Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Group),
            codename="role_vat_sse",
            defaults={"name": "role_vat_sse"},
        )
        user.user_permissions.add(permiso)
    client = APIClient(enforce_csrf_checks=csrf)
    client.force_login(user)
    client.user = user
    return client


@pytest.fixture(name="oferta")
def oferta_fixture():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    plan = PlanVersionCurricular.objects.create(
        nombre="Electricidad",
        provincia=provincia,
        sector=Sector.objects.create(nombre="Industria"),
        modalidad_cursada=ModalidadCursada.objects.create(nombre="Presencial"),
        horas_reloj=100,
    )
    return OfertaInstitucional.objects.create(
        centro=Centro.objects.create(
            nombre="CFP 401", codigo="060144900", provincia=provincia
        ),
        plan_curricular=plan,
        programa=Programa.objects.create(nombre="Programa Sintetico"),
        ciclo_lectivo=2026,
    )


@pytest.fixture(name="comisiones")
def comisiones_fixture(oferta):
    primera = Comision.objects.create(
        oferta=oferta,
        codigo_comision="COM-001",
        nombre="Comision <Uno>",
        fecha_inicio=date(2026, 3, 1),
        fecha_fin=date(2026, 12, 1),
        cupo=10,
    )
    segunda = Comision.objects.create(
        oferta=oferta,
        codigo_comision="COM-002",
        nombre="",
        fecha_inicio=date(2026, 3, 2),
        fecha_fin=date(2026, 4, 2),
        cupo=5,
        estado="cancelada",
    )
    return primera, segunda


def test_access_follows_the_native_route_rule(comisiones):
    assert APIClient().get(ROOT).status_code == 401
    assert _client("view_centro", sse=True).get(ROOT).status_code == 403
    assert _client("view_comision", sse=True).get(ROOT).status_code == 200
    # Out of the user's scope the native queryset is empty (no 404, no rows).
    assert _client("view_comision").get(ROOT).json()["results"] == []


def test_list_projects_the_native_rows_filters_and_buttons(comisiones):
    primera, segunda = comisiones
    api = _client("view_comision", "change_comision", sse=True)
    data = api.get(ROOT).json()
    assert [r["id"] for r in data["results"]] == [primera.pk, segunda.pk]
    fila, sin_nombre = data["results"]
    assert (fila["codigo"], fila["nombre"], fila["cupo"]) == (
        "COM-001",
        "Comision <Uno>",
        "10",
    )
    assert (fila["fecha_inicio"], fila["fecha_fin"]) == ("01/03/2026", "01/12/2026")
    assert fila["oferta"] == str(primera.oferta)
    assert (fila["estado"], fila["estado_label"]) == (
        primera.estado,
        primera.get_estado_display(),
    )
    assert (sin_nombre["nombre"], sin_nombre["fecha_inicio"]) == ("", "02/03/2026")
    assert sin_nombre["estado"] == "cancelada"
    assert fila["detail_url"] == f"{NATIVA}{primera.pk}/"
    assert fila["update_url"] == f"{NATIVA}{primera.pk}/editar/"
    assert fila["delete_url"] == f"{NATIVA}{primera.pk}/eliminar/"
    assert data["permisos"] == {"editar": True, "eliminar": False}
    assert data["urls"] == {"list": NATIVA, "create": f"{NATIVA}nueva/"}
    assert data["page"]["is_paginated"] is False and data["messages"] == []
    cancelada = api.get(ROOT, {"estado": "cancelada"}).json()["results"]
    assert [r["id"] for r in cancelada] == [segunda.pk]
    por_oferta = api.get(ROOT, {"oferta_id": primera.oferta_id}).json()["results"]
    assert len(por_oferta) == 2
    assert api.get(ROOT).json()["busqueda"] == ""
    assert api.get(ROOT, {"page": 9}).status_code == 404


def test_projected_texts_are_the_ones_the_native_page_prints(comisiones):
    api = _client("view_comision", sse=True)
    nativo = Client()
    nativo.force_login(api.user)
    html = nativo.get(NATIVA).content.decode()
    for fila in api.get(ROOT).json()["results"]:
        for clave in ("codigo", "oferta", "estado_label", "cupo"):
            assert escape(fila[clave]) in html, clave
    assert "01/03/2026" in html


@pytest.mark.parametrize(
    ("param", "term", "matching_indices"),
    [
        ("busqueda", "com-002", [1]),
        ("busqueda", "<Uno>", [0]),
        ("busqueda", "Electricidad", [0, 1]),
        ("q", "COM-001", [0]),
        ("busqueda", "no hay coincidencias", []),
    ],
)
def test_text_search_returns_the_same_scoped_rows_on_both_surfaces(
    comisiones, param, term, matching_indices
):
    api = _client("view_comision", sse=True)
    native = Client()
    native.force_login(api.user)

    query = {param: term}
    expected = [comisiones[index].pk for index in matching_indices]
    response = api.get(ROOT, query)
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["results"]] == expected
    response = native.get(NATIVA, query)
    assert response.status_code == 200
    assert [row.pk for row in response.context["comisiones"]] == expected
    assert _client("view_comision").get(ROOT, query).json()["results"] == []


def test_search_uses_the_local_offer_name_when_defined(comisiones, oferta):
    oferta.nombre_local = "Instalaciones Electricas"
    oferta.save(update_fields=["nombre_local"])
    api = _client("view_comision", sse=True)
    response = api.get(ROOT, {"busqueda": "Instalaciones"})
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["results"]] == [
        row.pk for row in comisiones
    ]
    assert api.get(ROOT, {"busqueda": "Electricidad"}).json()["results"] == []


def test_search_with_multiple_reference_titles_does_not_duplicate_rows(
    comisiones, oferta
):
    plan = oferta.plan_curricular
    plan.nombre = ""
    plan.save(update_fields=["nombre"])
    for name in ("Mecanica general", "Mecanica inicial"):
        TituloReferencia.objects.create(plan_estudio=plan, nombre=name)

    api = _client("view_comision", sse=True)
    response = api.get(ROOT, {"busqueda": "mecanica"})
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["results"]] == [
        row.pk for row in comisiones
    ]


def test_pagination_matches_the_native_page(oferta):
    for numero in range(21):
        Comision.objects.create(
            oferta=oferta,
            codigo_comision=f"P-{numero:02d}",
            nombre="x",
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 4, 1),
            cupo=1,
        )
    pagina = _client("view_comision", sse=True).get(ROOT, {"page": 2}).json()
    assert len(pagina["results"]) == 1
    assert (pagina["page"]["number"], pagina["page"]["num_pages"]) == (2, 2)


def test_writes_are_not_allowed(comisiones):
    api = _client("view_comision", "add_comision", sse=True)
    assert api.post(ROOT, {}).status_code == 405
    assert Comision.objects.count() == 2


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("vat_comision_lista_preview_test_urls")
    module.urlpatterns = comision_lista_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_entry_serves_the_frozen_index_behind_the_native_guards(comisiones):
    response = _client("view_comision", sse=True).get(NATIVA)
    assert response.status_code == 200
    body = response.content.decode()
    assert '/vat/react/assets/app-1.js"' in body and "/v2/sisoc/assets/" not in body
    assert "no-store" in response["Cache-Control"]
    assert "csrftoken" in response.cookies
    assert Client().get(NATIVA).status_code == 403
    assert _client("view_centro", sse=True).get(NATIVA).status_code == 403
    assert (
        _client("view_comision", sse=True).get(NATIVA, {"page": 9}).status_code == 404
    )
