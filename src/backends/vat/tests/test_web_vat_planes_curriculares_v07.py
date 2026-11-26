"""V07.01/V07.02: web API and preview entries of the curricular plans (``/api/web/vat/catalogos/planes-curriculares/``). Synthetic data."""

import itertools
import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings
from django.utils.html import escape
from rest_framework.test import APIClient

from config.urls_all import urlpatterns as monolith_patterns
from core.models import Provincia
from users.models import Profile
from VAT.models import (
    ModalidadCursada,
    PlanVersionCurricular,
    Sector,
    Subsector,
    TituloReferencia,
)
from VAT.web_preview_vat_planes import planes_preview_patterns

pytestmark = pytest.mark.django_db

_COUNTER = itertools.count()
ROOT = "/api/web/vat/catalogos/planes-curriculares/"
NATIVA = "/vat/catalogos/planes-curriculares/"
SUFIJO = "planversioncurricular"
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)


def _role(user, codename):
    permiso, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Group),
        codename=codename,
        defaults={"name": codename},
    )
    user.user_permissions.add(permiso)


def _client(*codes, sse=False, provincial=None, csrf=False):
    user = get_user_model().objects.create_user(f"pl{next(_COUNTER)}")
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="VAT", codename__in=codes)
    )
    if sse:
        _role(user, "role_vat_sse")
    if provincial is not None:
        _role(user, "role_provincia_vat")
        Profile.objects.update_or_create(
            user=user,
            defaults={"es_usuario_provincial": True, "provincia": provincial},
        )
    client = APIClient(enforce_csrf_checks=csrf)
    client.force_login(user)
    client.user = user
    return client


@pytest.fixture(name="base")
def base_fixture():
    sector = Sector.objects.create(nombre="Industria")
    return {
        "provincia": Provincia.objects.create(nombre="Buenos Aires"),
        "otra": Provincia.objects.create(nombre="Cordoba"),
        "sector": sector,
        "subsector": Subsector.objects.create(nombre="Electricidad", sector=sector),
        "modalidad": ModalidadCursada.objects.create(nombre="Presencial"),
    }


@pytest.fixture(name="plan")
def plan_fixture(base):
    plan = PlanVersionCurricular.objects.create(
        nombre="Electricista <domiciliario>",
        provincia=base["provincia"],
        sector=base["sector"],
        subsector=base["subsector"],
        modalidad_cursada=base["modalidad"],
        horas_reloj=120,
        normativa="Res. libre || Resolución 45/2020",
        nivel_requerido="primario_completo",
        nivel_certifica="nivel_2",
    )
    TituloReferencia.objects.create(nombre=plan.nombre, plan_estudio=plan, activo=True)
    return plan


def _campos(base, **extra):
    return {
        "nombre": "Plan nuevo",
        "sector": base["sector"].pk,
        "subsector": base["subsector"].pk,
        "modalidad_cursada": base["modalidad"].pk,
        "horas_reloj": "80",
        "activo": "on",
        **extra,
    }


def test_access_follows_each_native_route_and_dispatch_guard(plan):
    rutas = {
        ROOT: "view",
        f"{ROOT}{plan.pk}/": "view",
        f"{ROOT}nuevo/": "add",
        f"{ROOT}{plan.pk}/editar/": "change",
    }
    for url, accion in rutas.items():
        assert APIClient().get(url).status_code == 401
        for otra in {"view", "add", "change"} - {accion}:
            assert _client(f"{otra}_{SUFIJO}", sse=True).get(url).status_code == 403
        # The route permission alone is not enough: the native dispatch also asks for the SSE or provincial role.
        assert _client(f"{accion}_{SUFIJO}").get(url).status_code == 403
        assert _client(f"{accion}_{SUFIJO}", sse=True).get(url).status_code == 200
    assert _client(f"view_{SUFIJO}", sse=True).get(f"{ROOT}999999/").status_code == 404
    assert (
        _client(f"change_{SUFIJO}", sse=True).get(f"{ROOT}999999/editar/").status_code
        == 404
    )


def test_list_projects_the_native_rows_filters_and_buttons(plan, base):
    inactivo = PlanVersionCurricular.objects.create(
        nombre="Plomeria",
        provincia=base["provincia"],
        sector=base["sector"],
        modalidad_cursada=base["modalidad"],
        activo=False,
    )
    api = _client(f"view_{SUFIJO}", f"change_{SUFIJO}", sse=True)
    data = api.get(ROOT).json()
    assert {r["id"] for r in data["results"]} == {plan.pk, inactivo.pk}
    filas = {r["id"]: r for r in data["results"]}
    fila = filas[plan.pk]
    assert (fila["sector"], fila["subsector"], fila["nombre"]) == (
        "Industria",
        "Electricidad",
        "Electricista <domiciliario>",
    )
    assert (fila["modalidad"], fila["horas"], fila["activo"]) == (
        "Presencial",
        "120",
        True,
    )
    assert (filas[inactivo.pk]["subsector"], filas[inactivo.pk]["horas"]) == ("—", "—")
    assert filas[inactivo.pk]["activo"] is False
    assert fila["detail_url"] == f"{NATIVA}{plan.pk}/"
    assert fila["update_url"] == f"{NATIVA}{plan.pk}/editar/"
    assert fila["delete_url"] == f"{NATIVA}{plan.pk}/eliminar/"
    assert data["permisos"] == {"editar": True, "eliminar": False}
    assert data["urls"] == {"list": NATIVA, "create": f"{NATIVA}nuevo/"}
    assert data["filters_config"] and data["favorites"]["section"] == ""
    assert data["page"]["is_paginated"] is False and data["messages"] == []
    activos = api.get(ROOT, {"activo": "true"}).json()["results"]
    assert [r["id"] for r in activos] == [plan.pk]
    por_titulo = api.get(ROOT, {"titulo": plan.titulos.get().pk}).json()["results"]
    assert [r["id"] for r in por_titulo] == [plan.pk]
    assert api.get(ROOT, {"page": 9}).status_code == 404


def test_scope_limits_a_provincial_user_to_the_province_plans(plan, base):
    ajeno = PlanVersionCurricular.objects.create(
        nombre="Plan de otra provincia",
        provincia=base["otra"],
        sector=base["sector"],
        modalidad_cursada=base["modalidad"],
    )
    api = _client(f"view_{SUFIJO}", provincial=base["provincia"])
    assert [r["id"] for r in api.get(ROOT).json()["results"]] == [plan.pk]
    assert api.get(f"{ROOT}{plan.pk}/").status_code == 200
    assert api.get(f"{ROOT}{ajeno.pk}/").status_code == 404


def test_detail_projects_the_texts_the_native_page_prints(plan):
    api = _client(f"view_{SUFIJO}", f"delete_{SUFIJO}", sse=True)
    nativo = Client()
    nativo.force_login(api.user)
    detalle = api.get(f"{ROOT}{plan.pk}/").json()
    html = nativo.get(f"{NATIVA}{plan.pk}/").content.decode()
    assert detalle["titulo"] == str(plan)
    assert (detalle["normativa"], detalle["horas_reloj"]) == ("Res. libre", "120")
    assert (
        detalle["normativa_tipo"],
        detalle["normativa_numero"],
        detalle["normativa_anio"],
    ) == ("Resolución", "45", "2020")
    assert (detalle["nivel_requerido"], detalle["nivel_certifica"]) == (
        "primario_completo",
        "nivel_2",
    )
    for clave in (
        "titulo",
        "nombre",
        "sector",
        "subsector",
        "modalidad",
        "normativa",
        "normativa_tipo",
        "normativa_numero",
        "normativa_anio",
        "horas_reloj",
        "nivel_requerido",
        "nivel_certifica",
    ):
        assert escape(detalle[clave]) in html, clave
    assert detalle["permisos"] == {"editar": False, "eliminar": True}
    assert detalle["urls"]["delete"] == f"{NATIVA}{plan.pk}/eliminar/"
    assert detalle["messages"] == []


def test_detail_prints_the_dash_for_the_empty_values(base):
    vacio = PlanVersionCurricular.objects.create(
        nombre="Plan minimo",
        provincia=base["provincia"],
        sector=base["sector"],
        modalidad_cursada=base["modalidad"],
    )
    detalle = _client(f"view_{SUFIJO}", sse=True).get(f"{ROOT}{vacio.pk}/").json()
    assert (detalle["subsector"], detalle["normativa"], detalle["horas_reloj"]) == (
        "-",
        "-",
        "-",
    )
    assert (detalle["nivel_requerido"], detalle["normativa_anio"]) == ("-", "-")


def test_form_projects_the_native_fields_and_title(plan, base):
    api = _client(f"add_{SUFIJO}", f"change_{SUFIJO}", sse=True)
    nuevo = api.get(f"{ROOT}nuevo/").json()
    assert nuevo["editing"] is False
    assert [f["name"] for f in nuevo["fields"]][:3] == ["provincia", "nombre", "sector"]
    assert nuevo["page"] == {
        "page_title": "Nuevo Plan de Estudio",
        "submit_text": "Crear plan",
    }
    assert nuevo["urls"] == {"list": NATIVA, "cancel": NATIVA}
    assert nuevo["normativa_actual"] == "" and nuevo["messages"] == []
    activo = {f["name"]: f for f in nuevo["fields"]}["activo"]
    assert (activo["value"], activo["attrs"]["type"]) == (True, "checkbox")
    edicion = api.get(f"{ROOT}{plan.pk}/editar/").json()
    assert edicion["editing"] is True
    por_nombre = {f["name"]: f for f in edicion["fields"]}
    assert "provincia" not in por_nombre
    assert por_nombre["nombre"]["value"] == "Electricista <domiciliario>"
    assert por_nombre["sector"]["value"] == str(base["sector"].pk)
    assert por_nombre["normativa_numero"]["value"] == "45"
    assert por_nombre["normativa_tipo"]["value"] == "Resolución"
    assert edicion["normativa_actual"] == "Res. libre"
    assert edicion["page"]["submit_text"] == "Guardar cambios"
    assert edicion["urls"]["cancel"] == f"{NATIVA}{plan.pk}/"
    assert all(f["disabled"] is False for f in edicion["fields"])


def test_create_persists_with_its_title_and_queues_the_message(base):
    api = _client(f"add_{SUFIJO}", f"view_{SUFIJO}", sse=True)
    rechazo = api.post(
        f"{ROOT}nuevo/",
        {"nombre": "   ", "sector": base["sector"].pk},
        format="multipart",
    )
    assert rechazo.status_code == 400
    assert any(f["errors"] for f in rechazo.json()["fields"])
    assert PlanVersionCurricular.objects.count() == 0
    respuesta = api.post(
        f"{ROOT}nuevo/",
        _campos(
            base,
            provincia=base["provincia"].pk,
            normativa_tipo="Resolución",
            normativa_numero="45",
            normativa_anio="2020",
        ),
        format="multipart",
    )
    assert respuesta.status_code == 200
    plan = PlanVersionCurricular.objects.get()
    assert respuesta.json() == {"ok": True, "redirect": f"{NATIVA}{plan.pk}/"}
    assert (plan.nombre, plan.horas_reloj, plan.activo) == ("Plan nuevo", 80, True)
    assert plan.provincia_id == base["provincia"].pk
    assert plan.titulos.get().nombre == "Plan nuevo"
    assert "45" in plan.normativa and "2020" in plan.normativa
    assert api.get(ROOT).json()["messages"] == [
        {"message": "Plan de estudio creado correctamente.", "level": "success"}
    ]


def test_create_rejects_an_incomplete_normativa_and_a_foreign_subsector(base):
    api = _client(f"add_{SUFIJO}", sse=True)
    otro = Subsector.objects.create(
        nombre="Otro", sector=Sector.objects.create(nombre="Servicios")
    )
    respuesta = api.post(
        f"{ROOT}nuevo/",
        _campos(
            base,
            provincia=base["provincia"].pk,
            subsector=otro.pk,
            normativa_tipo="Resolución",
        ),
        format="multipart",
    )
    assert respuesta.status_code == 400
    errores = {f["name"]: f["errors"] for f in respuesta.json()["fields"]}
    assert errores["normativa_numero"] and errores["normativa_anio"]
    assert PlanVersionCurricular.objects.count() == 0


def test_update_persists_syncs_the_title_and_rejection_keeps_the_stored_data(
    plan, base
):
    api = _client(f"change_{SUFIJO}", f"view_{SUFIJO}", sse=True)
    url = f"{ROOT}{plan.pk}/editar/"
    rechazo = api.post(
        url, {"nombre": "", "sector": base["sector"].pk}, format="multipart"
    )
    assert rechazo.status_code == 400
    plan.refresh_from_db()
    assert plan.nombre == "Electricista <domiciliario>"
    respuesta = api.post(
        url,
        _campos(
            base,
            nombre="Electricista renovado",
            horas_reloj="200",
            normativa_tipo="Resolución",
            normativa_numero="45",
            normativa_anio="2020",
        ),
        format="multipart",
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": f"{NATIVA}{plan.pk}/"}
    plan.refresh_from_db()
    assert (plan.nombre, plan.horas_reloj) == ("Electricista renovado", 200)
    assert plan.normativa == "Res. libre || Resolución 45/2020"
    assert plan.titulos.get().nombre == "Electricista renovado"
    assert api.get(ROOT).json()["messages"] == [
        {"message": "Plan de estudio actualizado correctamente.", "level": "success"}
    ]


def test_writes_require_csrf_the_write_permission_and_the_role(plan, base):
    escritor = _client(f"add_{SUFIJO}", f"change_{SUFIJO}", sse=True, csrf=True)
    assert escritor.post(f"{ROOT}nuevo/", _campos(base)).status_code == 403
    assert escritor.post(f"{ROOT}{plan.pk}/editar/", _campos(base)).status_code == 403
    lector = _client(f"view_{SUFIJO}", sse=True)
    assert lector.post(f"{ROOT}nuevo/", _campos(base)).status_code == 403
    assert lector.post(f"{ROOT}{plan.pk}/editar/", _campos(base)).status_code == 403
    sin_rol = _client(f"add_{SUFIJO}", f"change_{SUFIJO}")
    assert sin_rol.post(f"{ROOT}nuevo/", _campos(base)).status_code == 403
    assert sin_rol.post(f"{ROOT}{plan.pk}/editar/", _campos(base)).status_code == 403
    assert PlanVersionCurricular.objects.count() == 1
    plan.refresh_from_db()
    assert plan.nombre == "Electricista <domiciliario>"


def test_the_read_routes_do_not_accept_writes(plan):
    api = _client(f"view_{SUFIJO}", sse=True)
    assert api.post(ROOT, {}).status_code == 405
    assert api.post(f"{ROOT}{plan.pk}/", {}).status_code == 405


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("vat_planes_preview_test_urls")
    module.urlpatterns = planes_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_entries_serve_the_frozen_index_behind_the_native_guards(plan):
    rutas = {
        NATIVA: "view",
        f"{NATIVA}{plan.pk}/": "view",
        f"{NATIVA}nuevo/": "add",
        f"{NATIVA}{plan.pk}/editar/": "change",
    }
    for url, accion in rutas.items():
        response = _client(f"{accion}_{SUFIJO}", sse=True).get(url)
        assert response.status_code == 200
        body = response.content.decode()
        assert '/vat/react/assets/app-1.js"' in body and "/v2/sisoc/assets/" not in body
        assert "no-store" in response["Cache-Control"]
        assert "csrftoken" in response.cookies
        assert Client().get(url).status_code == 403
        assert _client("view_centro", sse=True).get(url).status_code == 403
        # Role guard of the native dispatch runs before the index is served.
        assert _client(f"{accion}_{SUFIJO}").get(url).status_code == 403
    assert (
        _client(f"view_{SUFIJO}", sse=True).get(NATIVA, {"page": 9}).status_code == 404
    )
    assert (
        _client(f"change_{SUFIJO}", sse=True).get(f"{NATIVA}999999/editar/").status_code
        == 404
    )
