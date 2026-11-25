"""Web API (G1 v1) of the Actas tab: ``/api/web/inspecciones/actas/``.

Read-only projection of ``views_actas.ActasView`` for the React screen. The
monolith tests go through ``config.settings_all`` (policy evaluated locally);
the runtime tests switch to ``SISOC_BACKEND="inspecciones"`` with the real
runtime URLconf, where only a request the core signed reaches the view.
"""

import uuid
from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from core import web_gate
from core.models import Provincia
from inspecciones.models import Acta, Inspeccion
from inspecciones.services.formato import hoy

ROOT = "/api/web/inspecciones/actas/"
INSPECTORES = "/api/web/inspecciones/inspectores/"
WRITES = ("INSERT", "UPDATE", "DELETE")

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


@pytest.fixture(name="gestor_web")
def gestor_web_fixture(gestor):
    gestor.first_name, gestor.last_name = "Gestora", "Panel"
    gestor.save()
    return _ready(gestor)


@pytest.fixture(name="web")
def web_fixture(gestor_web):
    client = Client()
    client.force_login(gestor_web)
    return client


def _acta(inspector, escuela, secuencia, **campos):
    fecha = campos.pop("fecha", hoy())
    inspeccion = Inspeccion.objects.create(
        uuid=uuid.uuid4(),
        inspector=inspector,
        estado=Inspeccion.Estado.FINALIZADA,
        revision=1,
        escuela=escuela,
        fecha_visita=fecha,
        turno="tarde",
        resultado="cerrada",
    )
    numero = f"ACTA-2026-{secuencia:06d}"
    datos = {
        "cerrada_at": timezone.now() - timedelta(minutes=secuencia),
        "firma_tipo": "excepcion",
    }
    datos.update(campos)
    return Acta.objects.create(
        inspeccion=inspeccion,
        inspector=inspector,
        escuela=escuela,
        numero=numero,
        anio=2026,
        secuencia=secuencia,
        fecha_visita=fecha,
        turno="tarde",
        resultado="cerrada",
        formulario_version="v1",
        instantanea={"numero": numero, "payload": {}},
        instantanea_sha256="0" * 64,
        **datos,
    )


def _numeros(data):
    return [fila["numero"] for fila in data["results"]]


def _native_numeros(client, params):
    respuesta = client.get(reverse("inspecciones_actas"), params)
    return [fila["acta"].numero for fila in respuesta.context["filas"]]


# --- Monolith: shape, parity and permissions --------------------------------


def test_list_projects_the_native_rows_frame_and_filters(
    web, escuela, inspector_a, gestor_web
):
    firmada = _acta(inspector_a, escuela, 230, firma_tipo="firma")
    _acta(
        inspector_a,
        escuela,
        231,
        estado=Acta.Estado.ANULADA,
        es_prueba=True,
        notificacion_estado=Acta.EstadoNotificacion.CARGADA,
    )
    del gestor_web

    respuesta = web.get(ROOT)

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == "application/json"
    assert respuesta["Cache-Control"] == "private, no-store"
    assert "Cookie" in respuesta["Vary"]
    data = respuesta.json()
    assert set(data) == {
        "layout",
        "tabs",
        "filters",
        "options",
        "has_query",
        "results",
        "page",
    }
    assert data["layout"] == {
        "breadcrumb": [
            {"text": "Inicio", "url": "/inicio/"},
            {"text": "Inspecciones escolares", "url": "/inspecciones/"},
            {"text": "Actas", "url": None},
        ],
        "display_name": "Gestora Panel",
        "role": "",
        "initials": "GP",
    }
    assert data["tabs"] == [
        {"id": "tablero", "label": "Tablero", "url": "/inspecciones/tablero/"},
        {"id": "escuelas", "label": "Escuelas", "url": "/inspecciones/"},
        {
            "id": "asignaciones",
            "label": "Asignaciones",
            "url": "/inspecciones/asignaciones/",
        },
        {"id": "actas", "label": "Actas", "url": "/inspecciones/actas/"},
    ]
    assert data["filters"] == {
        "fecha": "",
        "inspector": None,
        "provincia": "",
        "estado": "",
        "numero": "",
    }
    assert data["options"]["estados"] == [
        {"value": "", "label": "Todas las actas"},
        {"value": "validas", "label": "Válidas"},
        {"value": "anuladas", "label": "Anuladas"},
        {"value": "prueba", "label": "De prueba"},
    ]
    assert data["options"]["inspectores_url"] == (
        "/api/web/inspecciones/inspectores/?alcance=programa"
    )
    assert data["has_query"] is False
    assert _numeros(data) == ["ACTA-2026-000230", "ACTA-2026-000231"]
    primera, segunda = data["results"]
    local = timezone.localtime(firmada.cerrada_at)
    assert primera == {
        "numero": "ACTA-2026-000230",
        "url": "/inspecciones/actas/ACTA-2026-000230/",
        "anulada": False,
        "prueba": False,
        "escuela": {
            "nombre": escuela.nombre,
            "cueanexo": escuela.cueanexo,
            "provincia": "",
            "localidad": escuela.localidad,
        },
        "turno": "tarde",
        "inspector": "Inspector_A",
        "fecha": hoy().strftime("%d/%m/%Y"),
        "hora": local.strftime("%H:%M"),
        "firma": "firma",
        "notificacion": "pendiente",
    }
    assert (segunda["anulada"], segunda["prueba"], segunda["notificacion"]) == (
        True,
        True,
        "cargada",
    )
    assert segunda["firma"] == "excepcion"
    assert data["page"] == {
        "number": 1,
        "count": 2,
        "start_index": 1,
        "end_index": 2,
        "has_other_pages": False,
        "previous": None,
        "next": None,
        "range": [1],
        "query_without_page": "",
    }


def test_filters_match_the_native_list_exactly(web, escuela, inspector_a, inspector_b):
    provincia = Provincia.objects.create(nombre="Provincia sintética")
    _acta(inspector_a, escuela, 230)
    _acta(inspector_b, escuela, 231, estado=Acta.Estado.ANULADA)
    _acta(inspector_a, escuela, 45, fecha=hoy() - timedelta(days=1))
    casos = [
        {"numero": "23"},
        {"numero": " acta-2026-00023 "},
        {"estado": "anuladas"},
        {"estado": "validas"},
        {"inspector": str(inspector_a.pk)},
        {"fecha": hoy().isoformat()},
        {"fecha": "no-es-fecha", "estado": "inventado"},
        {"provincia": str(provincia.pk)},
    ]

    for params in casos:
        data = web.get(ROOT, params).json()
        assert _numeros(data) == _native_numeros(web, params), params
        assert data["has_query"] is True

    eco = web.get(
        ROOT, {"numero": "23", "inspector": str(inspector_a.pk), "fecha": "x"}
    ).json()
    assert eco["filters"]["numero"] == "23"
    assert eco["filters"]["fecha"] == "x"
    assert eco["filters"]["inspector"] == {
        "id": inspector_a.pk,
        "text": "Inspector_A",
        "detalle": "inspector_a",
    }
    assert {"id": provincia.pk, "nombre": "Provincia sintética"} in eco["options"][
        "provincias"
    ]


def test_pagination_keeps_filters_and_rejects_an_invalid_page(
    web, escuela, inspector_a
):
    for secuencia in range(1, 28):
        _acta(inspector_a, escuela, secuencia)

    segunda = web.get(ROOT, {"numero": "0", "page": "2"}).json()

    assert segunda["page"] == {
        "number": 2,
        "count": 27,
        "start_index": 26,
        "end_index": 27,
        "has_other_pages": True,
        "previous": 1,
        "next": None,
        "range": [1, 2],
        "query_without_page": "numero=0&",
    }
    assert _numeros(segunda) == _native_numeros(web, {"numero": "0", "page": "2"})
    for invalida in ("3", "abc"):
        respuesta = web.get(ROOT, {"page": invalida})
        assert respuesta.status_code == 404
        assert respuesta["Content-Type"] == "application/json"
        nativo = web.get(reverse("inspecciones_actas"), {"page": invalida})
        assert nativo.status_code == 404


def test_reads_never_write(web, escuela, inspector_a):
    _acta(inspector_a, escuela, 230)

    with CaptureQueriesContext(connection) as queries:
        assert web.get(ROOT, {"numero": "230"}).status_code == 200
        assert web.get(INSPECTORES, {"q": "inspector"}).status_code == 200

    escrituras = [
        q["sql"] for q in queries if q["sql"].lstrip().upper().startswith(WRITES)
    ]
    assert escrituras == []


def test_anonymous_gets_401_json(client):
    for url in (ROOT, INSPECTORES):
        respuesta = client.get(url)
        assert respuesta.status_code == 401
        assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
        assert respuesta["Cache-Control"] == "private, no-store"


def test_authenticated_without_management_gets_403(client, inspector_a):
    _ready(inspector_a)
    sin_permiso = _ready(get_user_model().objects.create_user("sin_permiso_web"))

    for usuario in (inspector_a, sin_permiso):
        client.force_login(usuario)
        for url in (ROOT, INSPECTORES):
            respuesta = client.get(url)
            assert respuesta.status_code == 403, (usuario.username, url)
            assert "state" not in respuesta.json()


def test_pending_web_requirement_is_reported_and_a_forged_header_is_ignored(
    web, gestor_web, escuela, inspector_a
):
    _acta(inspector_a, escuela, 230)
    gestor_web.profile.must_change_password = True
    gestor_web.profile.save()
    falso = web_gate.sign(
        audience="inspecciones",
        user_pk=gestor_web.pk,
        session_key=web.cookies[settings.SESSION_COOKIE_NAME].value,
        method="GET",
        target=ROOT,
    )

    respuesta = web.get(ROOT, HTTP_X_SISOC_WEB_GATE=falso, RAW_URI=ROOT)

    assert respuesta.status_code == 403
    assert respuesta.json() == {
        "detail": web_gate.DETAIL_REQUIREMENT,
        "state": "password_change_required",
        "required_action_url": "/password/first-change/",
    }


def test_only_get_is_served(web):
    for metodo in ("post", "put", "patch", "delete"):
        assert getattr(web, metodo)(ROOT).status_code == 405, metodo
    assert Acta.objects.count() == 0


def test_superuser_and_coordination_keep_the_native_management_rule(
    client, coordinacion
):
    superuser = _ready(
        get_user_model().objects.create_superuser("super_web", password="x")
    )
    for usuario in (superuser, _ready(coordinacion)):
        client.force_login(usuario)
        assert client.get(ROOT).status_code == 200, usuario.username


def test_admindocs_head_does_not_bypass_the_web_api(client):
    staff = _ready(get_user_model().objects.create_user("staff_web", is_staff=True))
    client.force_login(staff)

    respuesta = client.head(ROOT)

    assert respuesta.status_code == 403
    assert "X-View" not in respuesta


# --- Inspector selector (J2) ------------------------------------------------


def test_inspector_search_matches_the_native_select2_endpoint(
    web, inspector_a, coordinacion
):
    for params in (
        {"q": "in"},
        {"q": "inspector"},
        {"q": "coordinacion", "alcance": "programa"},
        {"q": "coordinacion"},
    ):
        data = web.get(INSPECTORES, params).json()
        native = web.get(reverse("inspecciones_ajax_inspectores"), params).json()
        assert data == native, params
    assert web.get(INSPECTORES, {"q": "inspector"}).json()["results"] == [
        {"id": inspector_a.pk, "text": "Inspector_A", "detalle": "inspector_a"}
    ]


# --- Runtime: only the core's signed attestation reaches the view -----------


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="inspecciones",
        ROOT_URLCONF="inspecciones_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, *, target=ROOT, method="GET", now=None, audience=None):
    return web_gate.sign(
        audience=audience or "inspecciones",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method=method,
        target=target,
        now=now,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_a_signed_request(web, gestor_web, escuela, inspector_a):
    _acta(inspector_a, escuela, 230)
    target = ROOT + "?numero=230"

    respuesta = web.get(
        target,
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(gestor_web, web, target=target),
    )

    assert respuesta.status_code == 200
    assert _numeros(respuesta.json()) == ["ACTA-2026-000230"]
    assert respuesta["Cache-Control"] == "private, no-store"


@pytest.mark.usefixtures("runtime")
def test_runtime_rejects_missing_tampered_and_expired_attestations(
    web, gestor_web, escuela, inspector_a
):
    _acta(inspector_a, escuela, 230)
    valido = _signed(gestor_web, web)
    alterados = {
        "missing": None,
        "other_target": _signed(gestor_web, web, target=ROOT + "?numero=1"),
        "other_audience": _signed(gestor_web, web, audience="pas"),
        "other_method": _signed(gestor_web, web, method="POST"),
        "expired": _signed(gestor_web, web, now=timezone.now().timestamp() - 61),
        "bad_signature": valido[:-2] + ("AA" if not valido.endswith("AA") else "BB"),
    }

    for motivo, token in alterados.items():
        extra = {"RAW_URI": ROOT}
        if token is not None:
            extra["HTTP_X_SISOC_WEB_GATE"] = token
        respuesta = web.get(ROOT, **extra)
        assert respuesta.status_code == 403, motivo
        assert respuesta.json() == {"detail": web_gate.DETAIL_REJECTED}, motivo
    # The policy lives in the core: a pending requirement does not matter here.
    gestor_web.profile.must_change_password = True
    gestor_web.profile.save()
    assert web.get(ROOT, RAW_URI=ROOT, HTTP_X_SISOC_WEB_GATE=valido).status_code == 200


@pytest.mark.usefixtures("runtime")
def test_runtime_still_applies_the_owner_permission(client, inspector_a):
    client.force_login(_ready(inspector_a))

    respuesta = client.get(
        ROOT, RAW_URI=ROOT, HTTP_X_SISOC_WEB_GATE=_signed(inspector_a, client)
    )

    assert respuesta.status_code == 403
    assert respuesta.json() != {"detail": web_gate.DETAIL_REJECTED}


@pytest.mark.usefixtures("runtime")
def test_runtime_anonymous_gets_401(client):
    respuesta = client.get(ROOT, RAW_URI=ROOT)

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}


def test_inspecciones_publishes_its_web_api_prefix():
    from config.backends import load_backends_registry

    prefijos = load_backends_registry()["inspecciones"]["url_prefixes"]

    assert web_gate.web_api_prefix("inspecciones") in prefijos
