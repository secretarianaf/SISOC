"""V04.01 (U4): web API and preview entries of the schedule list and detail (``/api/web/vat/comisiones-horarios/``). Synthetic data."""

import itertools
import types
from datetime import date, time

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings
from django.utils.html import escape
from rest_framework.test import APIClient

from config.urls_all import urlpatterns as monolith_patterns
from core.models import Dia, Programa, Provincia
from VAT.models import (
    Centro,
    Comision,
    ComisionHorario,
    ModalidadCursada,
    OfertaInstitucional,
    PlanVersionCurricular,
    Sector,
)
from VAT.web_preview_vat_comision_horarios import comision_horarios_preview_patterns

pytestmark = pytest.mark.django_db

_COUNTER = itertools.count()
ROOT = "/api/web/vat/comisiones-horarios/"
NATIVA = "/vat/comisiones/horarios/"
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)


def _client(*codes, sse=False, csrf=False):
    user = get_user_model().objects.create_user(f"hl{next(_COUNTER)}")
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


@pytest.fixture(name="comision")
def comision_fixture():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    plan = PlanVersionCurricular.objects.create(
        nombre="Electricidad",
        provincia=provincia,
        sector=Sector.objects.create(nombre="Industria"),
        modalidad_cursada=ModalidadCursada.objects.create(nombre="Presencial"),
        horas_reloj=100,
    )
    oferta = OfertaInstitucional.objects.create(
        centro=Centro.objects.create(
            nombre="CFP 401", codigo="060144900", provincia=provincia
        ),
        plan_curricular=plan,
        programa=Programa.objects.create(nombre="Programa Sintetico"),
        ciclo_lectivo=2026,
    )
    return Comision.objects.create(
        oferta=oferta,
        codigo_comision="COM-001",
        nombre="Comision Uno",
        fecha_inicio=date(2026, 3, 1),
        fecha_fin=date(2026, 12, 1),
        cupo=10,
    )


@pytest.fixture(name="horarios")
def horarios_fixture(comision):
    lunes = Dia.objects.create(nombre="Lunes")
    martes = Dia.objects.create(nombre="Martes")
    primero = ComisionHorario.objects.create(
        comision=comision,
        dia_semana=lunes,
        hora_desde=time(9, 0),
        hora_hasta=time(12, 30),
        aula_espacio="Aula <2>",
        vigente=True,
    )
    segundo = ComisionHorario.objects.create(
        comision=comision,
        dia_semana=martes,
        hora_desde=time(18, 0),
        hora_hasta=time(20, 0),
        vigente=False,
    )
    return primero, segundo


def test_access_follows_the_native_route_rule(horarios):
    primero, _ = horarios
    for url in (ROOT, f"{ROOT}{primero.pk}/"):
        assert APIClient().get(url).status_code == 401
        assert _client("view_comision", sse=True).get(url).status_code == 403
        assert _client("view_comisionhorario", sse=True).get(url).status_code == 200
    # Out of the user's scope the native detail queryset gives 404 and the list is empty.
    assert (
        _client("view_comisionhorario").get(f"{ROOT}{primero.pk}/").status_code == 404
    )
    assert _client("view_comisionhorario").get(ROOT).json()["results"] == []
    api = _client("view_comisionhorario", sse=True)
    assert api.get(f"{ROOT}999999/").status_code == 404


def test_list_projects_the_native_rows_filters_and_buttons(horarios, comision):
    primero, segundo = horarios
    api = _client("view_comisionhorario", "change_comisionhorario", sse=True)
    data = api.get(ROOT).json()
    assert [r["id"] for r in data["results"]] == [primero.pk, segundo.pk]
    fila, otra = data["results"]
    assert fila["comision"] == str(comision)
    assert (fila["dia"], fila["desde"], fila["hasta"]) == ("Lunes", "09:00", "12:30")
    assert (fila["aula"], fila["vigente"]) == ("Aula <2>", True)
    assert (otra["aula"], otra["vigente"]) == ("—", False)
    assert fila["detail_url"] == f"{NATIVA}{primero.pk}/"
    assert fila["update_url"] == f"{NATIVA}{primero.pk}/editar/"
    assert fila["delete_url"] == f"{NATIVA}{primero.pk}/eliminar/"
    assert data["permisos"] == {"editar": True, "eliminar": False}
    assert data["urls"] == {"list": NATIVA, "create": f"{NATIVA}nuevo/"}
    assert data["page"]["is_paginated"] is False and data["messages"] == []
    assert data["busqueda"] == ""
    por_dia = api.get(ROOT, {"dia_semana": segundo.dia_semana_id}).json()["results"]
    assert [r["id"] for r in por_dia] == [segundo.pk]
    por_comision = api.get(ROOT, {"comision_id": comision.pk}).json()["results"]
    assert len(por_comision) == 2
    assert api.get(ROOT, {"comision_id": comision.pk + 99}).json()["results"] == []
    assert api.get(ROOT, {"page": 9}).status_code == 404


def test_detail_projects_the_texts_the_native_page_prints(horarios):
    primero, segundo = horarios
    api = _client("view_comisionhorario", sse=True)
    nativo = Client()
    nativo.force_login(api.user)
    detalle = api.get(f"{ROOT}{primero.pk}/").json()
    html = nativo.get(f"{NATIVA}{primero.pk}/").content.decode()
    assert (detalle["desde"], detalle["hasta"], detalle["vigente"]) == (
        "09:00",
        "12:30",
        True,
    )
    for clave in (
        "title",
        "comision",
        "dia",
        "aula",
        "desde",
        "hasta",
        "creado",
        "modificado",
    ):
        assert escape(detalle[clave]) in html, clave
    assert detalle["urls"] == {
        "list": NATIVA,
        "update": f"{NATIVA}{primero.pk}/editar/",
        "delete": f"{NATIVA}{primero.pk}/eliminar/",
    }
    assert detalle["messages"] == []
    sin = api.get(f"{ROOT}{segundo.pk}/").json()
    assert (sin["aula"], sin["vigente"]) == ("—", False)
    # ``ComisionHorario`` has no ``observaciones``: the native block that would print it never renders.
    assert "Observaciones" not in nativo.get(f"{NATIVA}{segundo.pk}/").content.decode()
    assert "observaciones" not in sin


def test_the_list_text_matches_the_native_page(horarios):
    api = _client("view_comisionhorario", sse=True)
    nativo = Client()
    nativo.force_login(api.user)
    html = nativo.get(NATIVA).content.decode()
    for fila in api.get(ROOT).json()["results"]:
        for clave in ("comision", "dia", "desde", "hasta", "aula"):
            assert escape(fila[clave]) in html, clave


def test_the_forms_prefix_keeps_working_next_to_the_list_routes(horarios):
    primero, _ = horarios
    api = _client("view_comisionhorario", "add_comisionhorario", sse=True)
    assert api.get(f"{ROOT}nuevo/").status_code == 200
    assert api.get(f"{ROOT}{primero.pk}/editar/").status_code == 403


def test_writes_are_not_allowed_on_the_read_routes(horarios):
    primero, _ = horarios
    api = _client("view_comisionhorario", "add_comisionhorario", sse=True)
    assert api.post(ROOT, {}).status_code == 405
    assert api.post(f"{ROOT}{primero.pk}/", {}).status_code == 405
    assert ComisionHorario.objects.count() == 2


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("vat_comision_horarios_preview_test_urls")
    module.urlpatterns = comision_horarios_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_entries_serve_the_frozen_index_behind_the_native_guards(horarios):
    primero, _ = horarios
    for url in (NATIVA, f"{NATIVA}{primero.pk}/"):
        response = _client("view_comisionhorario", sse=True).get(url)
        assert response.status_code == 200
        body = response.content.decode()
        assert '/vat/react/assets/app-1.js"' in body and "/v2/sisoc/assets/" not in body
        assert "no-store" in response["Cache-Control"]
        assert "csrftoken" in response.cookies
        assert Client().get(url).status_code == 403
        assert _client("view_comision", sse=True).get(url).status_code == 403
    # Native scope and page rules run before the index is served.
    assert (
        _client("view_comisionhorario").get(f"{NATIVA}{primero.pk}/").status_code == 404
    )
    assert (
        _client("view_comisionhorario", sse=True).get(NATIVA, {"page": 9}).status_code
        == 404
    )
