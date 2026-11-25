"""V05.01 (U6): web API and preview entries of the offer list/detail and course detail screens. Synthetic data."""

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
    Curso,
    ModalidadCursada,
    OfertaInstitucional,
    PlanVersionCurricular,
    Sector,
    VoucherParametria,
)
from VAT.web_preview_vat_oferta_curso import oferta_curso_preview_patterns

pytestmark = pytest.mark.django_db

_COUNTER = itertools.count()
OFERTA = "/api/web/vat/ofertas-institucionales/"
CURSO = "/api/web/vat/cursos-detalle/"
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)


def _client(*codes, sse=False, csrf=False):
    user = get_user_model().objects.create_user(f"u{next(_COUNTER)}")
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


@pytest.fixture(name="base")
def base_fixture():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    return {
        "centro": Centro.objects.create(
            nombre="CFP 401", codigo="060144900", provincia=provincia
        ),
        "plan": PlanVersionCurricular.objects.create(
            nombre="Electricidad",
            provincia=provincia,
            sector=Sector.objects.create(nombre="Industria"),
            modalidad_cursada=ModalidadCursada.objects.create(nombre="Presencial"),
            horas_reloj=100,
        ),
        "programa": Programa.objects.create(nombre="Programa Sintetico"),
    }


@pytest.fixture(name="oferta")
def oferta_fixture(base):
    return OfertaInstitucional.objects.create(
        centro=base["centro"],
        plan_curricular=base["plan"],
        programa=base["programa"],
        ciclo_lectivo=2026,
        nombre_local="Local Uno",
        costo="1234.5",
        observaciones="Con <b> y acentos: sí",
    )


@pytest.fixture(name="curso")
def curso_fixture(base):
    curso = Curso.objects.create(
        nombre="Electricidad básica",
        centro=base["centro"],
        plan_estudio=base["plan"],
        modalidad=base["plan"].modalidad_cursada,
        inscripcion_libre=True,
        costo_creditos=3,
        usa_voucher=True,
    )
    curso.voucher_parametrias.add(
        VoucherParametria.objects.create(
            nombre="Voucher Uno",
            programa=base["programa"],
            activa=True,
            cantidad_inicial=10,
            fecha_vencimiento=date(2030, 1, 1),
            creado_por=get_user_model().objects.create_user("creador"),
        )
    )
    return curso


def test_access_follows_each_native_route_rule(oferta, curso):
    reglas = [
        (OFERTA, "view_ofertainstitucional"),
        (f"{OFERTA}{oferta.pk}/", "view_ofertainstitucional"),
        (f"{CURSO}{curso.pk}/", "view_curso"),
    ]
    for url, codigo in reglas:
        assert APIClient().get(url).status_code == 401
        assert _client("view_centro", sse=True).get(url).status_code == 403
        assert _client(codigo, sse=True).get(url).status_code == 200
    # Out of the user's scope (no global role) the native queryset gives 404, not 403.
    assert (
        _client("view_ofertainstitucional").get(f"{OFERTA}{oferta.pk}/").status_code
        == 404
    )
    assert _client("view_curso").get(f"{CURSO}{curso.pk}/").status_code == 404
    assert (
        _client("view_ofertainstitucional", sse=True)
        .get(f"{OFERTA}999999/")
        .status_code
        == 404
    )
    assert _client("view_curso", sse=True).get(f"{CURSO}999999/").status_code == 404


def test_list_projects_rows_filters_pages_and_buttons(oferta, base):
    otra = OfertaInstitucional.objects.create(
        centro=base["centro"],
        plan_curricular=base["plan"],
        programa=base["programa"],
        ciclo_lectivo=2025,
        estado="cancelada",
        nombre_local="Otro nombre",
    )
    api = _client("view_ofertainstitucional", "change_ofertainstitucional", sse=True)
    data = api.get(OFERTA).json()
    assert [r["id"] for r in data["results"]] == [oferta.pk, otra.pk]
    fila = data["results"][0]
    assert (fila["centro"], fila["ciclo"], fila["estado"]) == (
        "CFP 401",
        "2026",
        "planificada",
    )
    assert fila["plan"] == str(base["plan"]) and fila["usa_voucher"] is False
    assert fila["detail_url"] == f"/vat/ofertas-institucionales/{oferta.pk}/"
    assert data["permisos"] == {"editar": True, "eliminar": False}
    assert data["urls"] == {
        "list": "/vat/ofertas-institucionales/",
        "create": "/vat/ofertas-institucionales/nueva/",
    }
    assert data["page"]["is_paginated"] is False and data["messages"] == []
    cancelada = api.get(OFERTA, {"estado": "cancelada"}).json()["results"]
    assert [r["id"] for r in cancelada] == [otra.pk]
    buscada = api.get(OFERTA, {"busqueda": "Local Uno"}).json()
    assert [r["id"] for r in buscada["results"]] == [oferta.pk]
    assert buscada["busqueda"] == "Local Uno"
    assert api.get(OFERTA, {"page": 9}).status_code == 404


def test_detail_projects_the_texts_the_native_pages_print(oferta, curso):
    api = _client("view_ofertainstitucional", "view_curso", sse=True)
    nativo = Client()
    nativo.force_login(api.user)
    lista = api.get(OFERTA).json()["results"][0]
    html = nativo.get("/vat/ofertas-institucionales/").content.decode()
    assert escape(lista["plan"]) in html and escape(lista["centro"]) in html
    detalle = api.get(f"{OFERTA}{oferta.pk}/").json()
    html = nativo.get(f"/vat/ofertas-institucionales/{oferta.pk}/").content.decode()
    assert detalle["costo"].startswith("$1234")
    assert detalle["nombre_local"] == "Local Uno"
    assert detalle["fecha_publicacion"] == "—"
    for clave in (
        "titulo",
        "plan",
        "programa",
        "ciclo",
        "nombre_local",
        "costo",
        "fecha_creacion",
        "fecha_modificacion",
        "observaciones",
    ):
        assert escape(detalle[clave]) in html, clave
    assert (
        detalle["urls"]["update"] == f"/vat/ofertas-institucionales/{oferta.pk}/editar/"
    )
    c = api.get(f"{CURSO}{curso.pk}/").json()
    html = nativo.get(f"/vat/cursos/{curso.pk}/").content.decode()
    assert (c["inscripcion_libre"], c["prioritario"], c["usa_voucher"]) == (
        "Sí",
        "No",
        "Sí",
    )
    assert (c["tipo"], c["observaciones"], c["costo_creditos"]) == ("-", "-", "3")
    assert c["vouchers"] == ["Voucher Uno"] and c["comisiones_count"] == 0
    assert c["puede_editar"] is False
    for clave in ("nombre", "plan_titulo", "centro", "estado_label", "plan"):
        assert escape(c[clave]) in html, clave
    assert "Voucher Uno" in html
    editor = _client("view_curso", "change_curso", sse=True).get(f"{CURSO}{curso.pk}/")
    assert editor.json()["puede_editar"] is True
    assert editor.json()["urls"]["update"] == f"/vat/cursos/{curso.pk}/editar/"


def test_writes_are_not_allowed(oferta, curso):
    api = _client("view_ofertainstitucional", "view_curso", sse=True)
    assert api.post(OFERTA, {}).status_code == 405
    assert api.post(f"{OFERTA}{oferta.pk}/", {}).status_code == 405
    assert api.post(f"{CURSO}{curso.pk}/", {}).status_code == 405
    oferta.refresh_from_db()
    assert oferta.ciclo_lectivo == 2026


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("vat_oferta_curso_preview_test_urls")
    module.urlpatterns = oferta_curso_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_entries_serve_the_frozen_index_behind_the_native_guards(oferta, curso):
    for url, codigo in [
        ("/vat/ofertas-institucionales/", "view_ofertainstitucional"),
        (f"/vat/ofertas-institucionales/{oferta.pk}/", "view_ofertainstitucional"),
        (f"/vat/cursos/{curso.pk}/", "view_curso"),
    ]:
        response = _client(codigo, sse=True).get(url)
        assert response.status_code == 200
        body = response.content.decode()
        assert '/vat/react/assets/app-1.js"' in body and "/v2/sisoc/assets/" not in body
        assert "no-store" in response["Cache-Control"]
        assert "csrftoken" in response.cookies
        assert Client().get(url).status_code == 403
        assert _client("view_centro", sse=True).get(url).status_code == 403
    # Native scope and page rules run before the index is served.
    assert (
        _client("view_ofertainstitucional")
        .get(f"/vat/ofertas-institucionales/{oferta.pk}/")
        .status_code
        == 404
    )
    assert _client("view_curso").get(f"/vat/cursos/{curso.pk}/").status_code == 404
    assert (
        _client("view_ofertainstitucional", sse=True)
        .get("/vat/ofertas-institucionales/", {"page": 9})
        .status_code
        == 404
    )
