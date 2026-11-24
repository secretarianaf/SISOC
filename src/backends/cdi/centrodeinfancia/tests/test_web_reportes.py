"""Web API (G1 v1) of the CDI reports screen: ``/api/web/cdi/reportes/``.

Read-only projection of ``views_reportes.ReportesCDIView`` for the React page.
The monolith tests go through ``config.settings_all`` (policy evaluated
locally); the runtime tests switch to ``SISOC_BACKEND="cdi"`` with the real
runtime URLconf, where only a request the core signed reaches the view.
"""

from io import BytesIO

import openpyxl
import pytest
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.storage.cookie import CookieStorage
from django.db import connection
from django.http import HttpResponse
from django.test import Client, RequestFactory, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from centrodeinfancia.models import AccesoCDI, CentroDeInfancia, Trabajador
from centrodeinfancia.services_reportes import (
    COLUMNAS_NOMINA,
    COLUMNAS_NOMINA_REDUCIDO,
)
from core import web_gate
from core.constants import UserGroups
from core.models import Provincia

ROOT = "/api/web/cdi/reportes/"
WRITES = ("INSERT", "UPDATE", "DELETE")

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return User.objects.get(pk=user.pk)


def _permiso_reportes():
    permiso, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Group),
        codename="role_reportes_cdi",
        defaults={"name": "Reportes CDI"},
    )
    return permiso


def _usuario(username, *, reportes=True, grupo=None, superuser=False):
    user = User.objects.create_user(
        username=username, is_superuser=superuser, is_staff=superuser
    )
    if reportes:
        user.user_permissions.add(_permiso_reportes())
    if grupo:
        user.groups.add(Group.objects.get_or_create(name=grupo)[0])
    return _ready(user)


def _cliente(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="datos")
def datos_fixture():
    mendoza = Provincia.objects.create(nombre="Mendoza")
    san_juan = Provincia.objects.create(nombre="San Juan")
    propio = CentroDeInfancia.objects.create(nombre="CDI Propio", provincia=mendoza)
    otro = CentroDeInfancia.objects.create(nombre="CDI Otro", provincia=san_juan)
    Trabajador.objects.create(centro=propio, nombre="Ana", apellido="Propia")
    return {"mendoza": mendoza, "san_juan": san_juan, "propio": propio, "otro": otro}


def _hojas(contenido):
    libro = openpyxl.load_workbook(BytesIO(contenido))
    return {
        hoja.title: [list(fila) for fila in hoja.iter_rows(values_only=True)]
        for hoja in libro.worksheets
    }


def _native(client, params=None):
    return client.get(reverse("centrodeinfancia_reportes"), params or {})


def _texto(fila):
    return [str(celda) for celda in fila]


# --- Monolith: shape, parity and permissions --------------------------------


def test_projects_the_native_selectors_and_summary(datos):
    user = _usuario("web-reportes-super", superuser=True)
    client = _cliente(user)

    respuesta = client.get(ROOT)

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == "application/json"
    assert respuesta["Cache-Control"] == "private, no-store"
    assert "Cookie" in respuesta["Vary"]
    data = respuesta.json()
    assert set(data) == {
        "breadcrumb",
        "provincias",
        "provincia_seleccionada",
        "variantes",
        "resumen",
        "urls",
        "messages",
    }
    assert data["breadcrumb"] == [
        {"text": "Centro de Desarrollo Infantil", "url": "/centrodeinfancia/listar"},
        {"text": "Reportes", "url": None},
    ]
    assert data["provincias"] == [
        {"id": datos["mendoza"].pk, "nombre": "Mendoza"},
        {"id": datos["san_juan"].pk, "nombre": "San Juan"},
    ]
    assert data["provincia_seleccionada"] == ""
    assert data["variantes"] == [
        {"value": "completo", "label": "Completo (todos los campos)"},
        {"value": "reducido", "label": "Reducido (campos seleccionados)"},
    ]
    assert data["urls"] == {
        "pantalla": "/centrodeinfancia/reportes/",
        "descarga": "/centrodeinfancia/reportes/descargar/",
    }
    assert data["messages"] == []
    native = _native(client).context
    assert data["resumen"]["columnas"] == list(native["resumen_columnas"])
    assert data["resumen"]["filas"] == [_texto(f) for f in native["resumen_filas"]]
    assert ["Totales", "Centros de Desarrollo Infantil", "2"] in data["resumen"][
        "filas"
    ]


def test_summary_is_the_first_sheet_of_the_download(datos):
    user = _usuario("web-reportes-hoja")
    AccesoCDI.objects.create(user=user, centro=datos["propio"])
    client = _cliente(user)

    filas = client.get(ROOT).json()["resumen"]["filas"]
    descarga = client.get(reverse("centrodeinfancia_reportes_descargar"))

    assert filas == [_texto(f) for f in _hojas(descarga.content)["Resumen"][1:]]


def test_province_filter_only_narrows_and_invalid_values_fall_back(datos):
    user = _usuario("web-reportes-filtro", superuser=True)
    client = _cliente(user)

    for params in (
        {"provincia": str(datos["san_juan"].pk)},
        {"provincia": "abc"},
        {"provincia": "999999"},
        {"provincia": ""},
        {"variante": "inventada"},
    ):
        data = client.get(ROOT, params).json()
        native = _native(client, params).context
        assert data["provincia_seleccionada"] == native["provincia_seleccionada"]
        assert data["resumen"]["filas"] == [
            _texto(f) for f in native["resumen_filas"]
        ], params
    narrowed = client.get(ROOT, {"provincia": datos["san_juan"].pk}).json()
    assert ["Totales", "Centros de Desarrollo Infantil", "1"] in narrowed["resumen"][
        "filas"
    ]
    invalid = client.get(ROOT, {"provincia": "abc"}).json()
    assert ["Totales", "Centros de Desarrollo Infantil", "2"] in invalid["resumen"][
        "filas"
    ]


def test_scope_limits_the_provinces_and_a_foreign_province_adds_nothing(datos):
    user = _usuario("web-reportes-referente")
    AccesoCDI.objects.create(user=user, centro=datos["propio"])
    client = _cliente(user)

    data = client.get(ROOT).json()
    ajena = client.get(ROOT, {"provincia": datos["san_juan"].pk}).json()

    assert data["provincias"] == [{"id": datos["mendoza"].pk, "nombre": "Mendoza"}]
    assert ["Totales", "Centros de Desarrollo Infantil", "1"] in data["resumen"][
        "filas"
    ]
    assert ["Totales", "Centros de Desarrollo Infantil", "0"] in ajena["resumen"][
        "filas"
    ]


@pytest.mark.parametrize(
    ("grupo", "variantes"),
    [
        (UserGroups.SIMEPI_ADMINISTRADOR, ["completo", "reducido"]),
        (UserGroups.SIMEPI_EQUIPO_NACIONAL, ["completo", "reducido"]),
        (UserGroups.SIMEPI_ANALISTA_DATOS, ["reducido"]),
        (UserGroups.SIMEPI_AUDITORIA, ["reducido"]),
        (UserGroups.SIMEPI_EGP, ["reducido"]),
    ],
)
def test_full_variant_only_for_superuser_admin_or_national_team(
    datos, grupo, variantes
):
    del datos
    client = _cliente(_usuario(f"web-reportes-{grupo}", grupo=grupo))

    data = client.get(ROOT, {"variante": "completo"}).json()

    assert [v["value"] for v in data["variantes"]] == variantes


def test_reduced_role_cannot_widen_the_download_by_editing_the_query(datos):
    del datos
    client = _cliente(_usuario("web-reportes-egp", grupo=UserGroups.SIMEPI_EGP))

    descarga = client.get(
        reverse("centrodeinfancia_reportes_descargar"), {"variante": "completo"}
    )

    assert _hojas(descarga.content)["Nomina"][0] == list(COLUMNAS_NOMINA_REDUCIDO)


def test_xlsx_stays_the_native_private_download(datos):
    del datos
    client = _cliente(_usuario("web-reportes-xlsx", superuser=True))

    descarga = client.get(
        reverse("centrodeinfancia_reportes_descargar"), {"variante": "reducido"}
    )
    completo = client.get(reverse("centrodeinfancia_reportes_descargar"))

    hoy = timezone.localdate().strftime("%Y%m%d")
    assert descarga.status_code == 200
    assert descarga["Content-Type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert descarga["Content-Disposition"] == (
        f'attachment; filename="reporte-cdi-reducido-{hoy}.xlsx"'
    )
    assert descarga["Cache-Control"] == "private, no-store"
    assert descarga["Pragma"] == "no-cache"
    assert list(_hojas(descarga.content)) == [
        "Resumen",
        "CDI",
        "Trabajadores",
        "Nomina",
        "Diccionario",
        "Metadatos",
    ]
    assert completo["Content-Disposition"] == (
        f'attachment; filename="reporte-cdi-{hoy}.xlsx"'
    )
    assert _hojas(completo.content)["Nomina"][0] == list(COLUMNAS_NOMINA)


def test_reads_never_write(datos):
    del datos
    client = _cliente(_usuario("web-reportes-lectura", superuser=True))
    client.get(ROOT)

    with CaptureQueriesContext(connection) as queries:
        assert client.get(ROOT, {"provincia": "1"}).status_code == 200

    assert not [
        q["sql"] for q in queries.captured_queries if q["sql"].startswith(WRITES)
    ]


def _queue_message(client, text):
    """Queue a message in the client's cookie, as a native view would."""
    request = RequestFactory().get("/")
    request.COOKIES = {k: v.value for k, v in client.cookies.items()}
    storage = CookieStorage(request)
    storage.add(messages.SUCCESS, text)
    response = HttpResponse()
    storage.update(response)
    client.cookies.update(response.cookies)


def test_pending_messages_are_returned_once_like_the_native_toasts(datos):
    del datos
    client = _cliente(_usuario("web-reportes-mensajes", superuser=True))
    _queue_message(client, "Listo.")

    primera = client.get(ROOT).json()["messages"]
    segunda = client.get(ROOT).json()["messages"]

    assert primera == [{"message": "Listo.", "level": "success"}]
    assert segunda == []


def test_anonymous_gets_401_json():
    respuesta = Client().get(ROOT)

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert respuesta["Cache-Control"] == "private, no-store"


def test_without_the_reports_permission_gets_403(datos):
    del datos
    sin_permiso = _usuario("web-reportes-sin-permiso", reportes=False)
    csv = _usuario("web-reportes-csv", reportes=False)
    csv.user_permissions.add(
        Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Group),
            codename="role_exportar_a_csv",
            defaults={"name": "Exportar a csv"},
        )[0]
    )
    csv.user_permissions.add(Permission.objects.get(codename="view_centrodeinfancia"))

    for user in (sin_permiso, User.objects.get(pk=csv.pk)):
        respuesta = _cliente(user).get(ROOT)
        assert respuesta.status_code == 403
        assert respuesta.json() != {"detail": web_gate.DETAIL_REQUIREMENT}


def test_pending_web_requirement_is_reported_and_a_forged_header_is_ignored(datos):
    del datos
    user = _usuario("web-reportes-pendiente", superuser=True)
    user.profile.must_change_password = True
    user.profile.save()
    client = _cliente(user)
    falso = web_gate.sign(
        audience="cdi",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method="GET",
        target=ROOT,
    )

    respuesta = client.get(ROOT, HTTP_X_SISOC_WEB_GATE=falso, RAW_URI=ROOT)

    assert respuesta.status_code == 403
    assert respuesta.json()["detail"] == web_gate.DETAIL_REQUIREMENT
    assert respuesta.json()["state"]


def test_only_get_is_served(datos):
    del datos
    client = _cliente(_usuario("web-reportes-metodos", superuser=True))

    assert client.post(ROOT).status_code == 405
    assert client.head(ROOT).status_code == 200


def test_admindocs_head_does_not_bypass_the_web_api():
    staff = User.objects.create_user("web-reportes-staff", is_staff=True)
    client = _cliente(_ready(staff))

    respuesta = client.head(ROOT)

    assert "X-View" not in respuesta
    assert respuesta.status_code == 403


# --- Runtime: only the core's signed attestation reaches the view -----------


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="cdi",
        ROOT_URLCONF="cdi_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, *, target=ROOT, method="GET", now=None, audience=None):
    return web_gate.sign(
        audience=audience or "cdi",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method=method,
        target=target,
        now=now,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_a_signed_request(datos):
    user = _usuario("web-reportes-runtime", superuser=True)
    client = _cliente(user)
    target = f"{ROOT}?provincia={datos['san_juan'].pk}"

    respuesta = client.get(
        target,
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(user, client, target=target),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["provincia_seleccionada"] == str(datos["san_juan"].pk)
    assert respuesta["Cache-Control"] == "private, no-store"


@pytest.mark.usefixtures("runtime")
def test_runtime_rejects_missing_tampered_and_expired_attestations(datos):
    del datos
    user = _usuario("web-reportes-runtime-mal", superuser=True)
    client = _cliente(user)
    valido = _signed(user, client)
    alterados = {
        "missing": None,
        "other_target": _signed(user, client, target=ROOT + "?provincia=1"),
        "other_audience": _signed(user, client, audience="inspecciones"),
        "other_method": _signed(user, client, method="POST"),
        "expired": _signed(user, client, now=timezone.now().timestamp() - 61),
        "bad_signature": valido[:-2] + ("AA" if not valido.endswith("AA") else "BB"),
    }

    for motivo, token in alterados.items():
        extra = {"RAW_URI": ROOT}
        if token is not None:
            extra["HTTP_X_SISOC_WEB_GATE"] = token
        respuesta = client.get(ROOT, **extra)
        assert respuesta.status_code == 403, motivo
        assert respuesta.json() == {"detail": web_gate.DETAIL_REJECTED}, motivo
    assert (
        client.get(ROOT, RAW_URI=ROOT, HTTP_X_SISOC_WEB_GATE=valido).status_code == 200
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_still_applies_the_reports_permission(datos):
    del datos
    user = _usuario("web-reportes-runtime-sin", reportes=False)
    client = _cliente(user)

    respuesta = client.get(
        ROOT, RAW_URI=ROOT, HTTP_X_SISOC_WEB_GATE=_signed(user, client)
    )

    assert respuesta.status_code == 403
    assert respuesta.json() != {"detail": web_gate.DETAIL_REJECTED}


@pytest.mark.usefixtures("runtime")
def test_runtime_anonymous_gets_401():
    respuesta = Client().get(ROOT, RAW_URI=ROOT)

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}


def test_cdi_publishes_its_web_api_prefix():
    from config.backends import load_backends_registry

    prefijos = load_backends_registry()["cdi"]["url_prefixes"]

    assert web_gate.web_api_prefix("cdi") in prefijos
