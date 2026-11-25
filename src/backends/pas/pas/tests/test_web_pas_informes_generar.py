"""Web API (G1 v1) of the report request: ``/api/web/pas/informes/`` (PAS04.02).

The three routes share the native form and services: ``PasInformeGenerarForm``,
``preview_payload`` and ``generar_informe_pas``. Access is the native rule of
``pas/informes/generar`` and ``pas/informes/previsualizar``.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.utils import timezone

from core import web_gate
from core.models import Municipio, Provincia
from core.services.csv_export import UTF8_BOM
from pas.models import PasAviso, PasEstado, PasHistorialEstado, PasInforme, PasPersona
from pas.services.informe_service import CSV_COLUMNS

ROOT = "/api/web/pas/informes/"
OPCIONES = f"{ROOT}opciones/"
PREVIEW = f"{ROOT}previsualizar/"
GENERAR = f"{ROOT}generar/"
CODES = (("pas", "view_paspersona"), ("pas", "add_pasinforme"))

pytestmark = pytest.mark.django_db


def _permission(app_label, codename):
    if (app_label, codename) == ("auth", "role_exportar_a_csv"):
        return Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Group),
            codename=codename,
            defaults={"name": "Exportar a csv"},
        )[0]
    return Permission.objects.get(content_type__app_label=app_label, codename=codename)


def _user(username, *codes, **extra):
    user = get_user_model().objects.create_user(username, **extra)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    user.user_permissions.add(*[_permission(*code) for code in codes])
    return user


def _client(user, **kwargs):
    client = Client(**kwargs)
    client.force_login(user)
    return client


@pytest.fixture(name="solicitante")
def solicitante_fixture():
    return _user("pide_informe", *CODES)


@pytest.fixture(name="web")
def web_fixture(solicitante):
    return _client(solicitante)


@pytest.fixture(name="mundo")
def mundo_fixture():
    provincia = Provincia.objects.create(nombre="Provincia gen")
    otra = Provincia.objects.create(nombre="Otra gen")
    municipio = Municipio.objects.create(nombre="Municipio gen", provincia=provincia)
    ajeno = Municipio.objects.create(nombre="Municipio ajeno", provincia=otra)
    activo = PasEstado.objects.get_or_create(nombre="Activo")[0]
    baja = PasEstado.objects.get_or_create(nombre="Baja")[0]
    aviso = PasAviso.objects.create(codigo=9101, descripcion="Aviso gen")
    return {
        "provincia": provincia,
        "otra": otra,
        "municipio": municipio,
        "ajeno": ajeno,
        "activo": activo,
        "baja": baja,
        "aviso": aviso,
    }


def _persona(mundo, indice, estado=None):
    return PasPersona.objects.create(
        id_persona=indice,
        apellidos=f"Apellido {indice:03d}",
        nombres=f"Nombre {indice:03d}",
        dni=30000000 + indice,
        cuit=f"2030000{indice:04d}",
        provincia=mundo["provincia"],
        municipio=mundo["municipio"],
        estado=estado or mundo["activo"],
    )


# --- Access ---------------------------------------------------------------------


def test_anonymous_gets_401_json(client):
    for metodo, url in (("get", OPCIONES), ("post", PREVIEW), ("post", GENERAR)):
        respuesta = getattr(client, metodo)(url)
        assert respuesta.status_code == 401, url
        assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}


@pytest.mark.parametrize(
    "codes",
    [(), (("pas", "view_paspersona"),), (("pas", "add_pasinforme"),)],
)
def test_every_route_needs_both_codes_like_the_native_ones(codes):
    web = _client(_user("incompleto_gen", *codes))

    assert web.get(OPCIONES).status_code == 403
    assert web.post(PREVIEW, {}).status_code == 403
    assert web.post(GENERAR, {}).status_code == 403
    assert not PasInforme.objects.exists()


def test_view_informe_alone_does_not_open_the_request():
    web = _client(
        _user("solo_lee_inf", ("pas", "view_paspersona"), ("pas", "view_pasinforme"))
    )

    assert web.get(OPCIONES).status_code == 403
    assert web.post(GENERAR, {}).status_code == 403


def test_superuser_passes():
    web = _client(_user("super_gen", is_superuser=True))

    assert web.get(OPCIONES).status_code == 200
    assert web.post(PREVIEW, {}).status_code == 200


def test_methods_and_csrf(solicitante):
    web = _client(solicitante)
    assert web.post(OPCIONES).status_code == 405
    assert web.get(PREVIEW).status_code == 405
    assert web.get(GENERAR).status_code == 405
    protegido = _client(solicitante, enforce_csrf_checks=True)

    assert protegido.post(PREVIEW, {}).status_code == 403
    assert protegido.post(GENERAR, {}).status_code == 403
    assert not PasInforme.objects.exists()


# --- Options --------------------------------------------------------------------


def test_options_list_the_choices_in_the_form_order(web, mundo):
    data = web.get(OPCIONES).json()

    assert data["breadcrumb"] == [
        {"text": "PAS", "url": "/pas/listar"},
        {"text": "Informes", "url": "/pas/informes"},
        {"text": "Generar", "url": None},
    ]
    assert [e["nombre"] for e in data["estados"]] == ["Activo", "Baja"]
    assert data["avisos"] == [{"id": mundo["aviso"].pk, "texto": "9101 - Aviso gen"}]
    assert [p["nombre"] for p in data["provincias"]] == ["Otra gen", "Provincia gen"]
    assert data["municipios"] == []


def test_options_load_the_municipios_of_the_province(web, mundo):
    data = web.get(OPCIONES, {"provincia": mundo["provincia"].pk}).json()

    assert data["municipios"] == [
        {"id": mundo["municipio"].pk, "nombre": "Municipio gen"}
    ]


@pytest.mark.parametrize("valor", ["x", "-1", "0", "99999999"])
def test_options_ignore_an_unusable_province(web, mundo, valor):
    assert web.get(OPCIONES, {"provincia": valor}).json()["municipios"] == []


def test_options_are_private(web):
    respuesta = web.get(OPCIONES)

    assert respuesta["Cache-Control"] == "private, no-store"
    assert "Cookie" in respuesta["Vary"]


# --- Preview --------------------------------------------------------------------


def test_preview_returns_the_native_payload(web, mundo):
    _persona(mundo, 1)
    _persona(mundo, 2, mundo["baja"])

    data = web.post(PREVIEW, {"estado_actual": mundo["activo"].pk}).json()

    assert data["ok"] is True
    assert data["modo"] == "registros"
    assert data["total"] == data["total_personas"] == 1
    assert data["limit"] == 50
    assert data["columns"] == [{"key": k, "label": label} for k, label in CSV_COLUMNS]
    assert len(data["rows"]) == 1


def test_preview_caps_the_rows_at_fifty(web, mundo):
    for indice in range(1, 52):
        _persona(mundo, indice)

    data = web.post(PREVIEW, {}).json()

    assert data["total"] == 51
    assert len(data["rows"]) == 50


def test_preview_is_in_changes_mode_with_a_change_filter(web, mundo):
    persona = _persona(mundo, 1)
    PasHistorialEstado.objects.create(
        persona=persona,
        estado_anterior=mundo["baja"],
        estado_nuevo=mundo["activo"],
        fecha_cambio=timezone.now(),
    )

    data = web.post(PREVIEW, {"estado_nuevo": mundo["activo"].pk}).json()

    assert data["modo"] == "cambios"
    assert data["total"] == data["total_cambios"] == 1


def test_preview_reports_the_form_errors_in_the_native_shape(web, mundo):
    respuesta = web.post(
        PREVIEW,
        {
            "fecha_creacion_desde": "2026-02-01",
            "fecha_creacion_hasta": "2026-01-01",
            "fecha_cambio_desde": "2026-02-01",
            "fecha_cambio_hasta": "2026-01-01",
            "provincia": mundo["provincia"].pk,
            "municipio": mundo["ajeno"].pk,
            "dni": "abc",
        },
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["ok"] is False
    errores = respuesta.json()["errors"]
    assert errores["fecha_creacion_hasta"] == [
        "La fecha de creación desde no puede ser posterior a la fecha hasta."
    ]
    assert errores["fecha_cambio_hasta"] == [
        "La fecha de cambios desde no puede ser posterior a la fecha hasta."
    ]
    assert "municipio" in errores
    assert "dni" in errores


def test_a_municipio_of_another_province_is_rejected(web, mundo):
    respuesta = web.post(
        PREVIEW, {"provincia": mundo["provincia"].pk, "municipio": mundo["ajeno"].pk}
    )

    assert respuesta.status_code == 400
    assert not PasInforme.objects.exists()


# --- Generate -------------------------------------------------------------------


def test_generate_creates_one_report_and_returns_its_csv(web, solicitante, mundo):
    _persona(mundo, 1)

    respuesta = web.post(GENERAR, {})

    informe = PasInforme.objects.get()
    assert informe.usuario == solicitante
    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == "text/csv; charset=utf-8"
    assert (
        respuesta["Content-Disposition"]
        == f'attachment; filename="pas-inf-{informe.pk:06d}.csv"'
    )
    assert respuesta["X-PAS-Informe-Id"] == str(informe.pk)
    assert respuesta["Cache-Control"] == "private, no-store"
    cuerpo = respuesta.content.decode("utf-8")
    assert cuerpo.startswith(UTF8_BOM + CSV_COLUMNS[0][1])
    assert "Apellido 001" in cuerpo


def test_generate_without_the_export_code_still_returns_the_csv(web, solicitante):
    assert not solicitante.user_permissions.filter(codename="role_exportar_a_csv")

    respuesta = web.post(GENERAR, {})

    assert respuesta.status_code == 200
    assert PasInforme.objects.count() == 1


def test_generate_stores_the_same_snapshot_as_the_native_view(web, mundo):
    _persona(mundo, 1)
    datos = {"estado_actual": mundo["activo"].pk}

    web.post(GENERAR, datos)
    nativo = _client(_user("nativo_gen", *CODES)).post("/pas/informes/generar", datos)

    api, nativo_informe = PasInforme.objects.order_by("pk")
    assert api.resultado == nativo_informe.resultado
    assert api.filtros == nativo_informe.filtros
    assert nativo.content.decode("utf-8").startswith(UTF8_BOM)


def test_invalid_generate_creates_nothing(web, mundo):
    respuesta = web.post(
        GENERAR,
        {"fecha_cambio_desde": "2026-02-01", "fecha_cambio_hasta": "2026-01-01"},
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["errors"]["fecha_cambio_hasta"] == [
        "La fecha de cambios desde no puede ser posterior a la fecha hasta."
    ]
    assert not PasInforme.objects.exists()


def test_the_native_requests_are_unchanged(web, mundo):
    assert web.get("/pas/informes/generar").status_code == 200
    assert web.post("/pas/informes/previsualizar", {}).json()["ok"] is True
