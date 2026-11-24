"""Canonical Pagos screens project the native views; uploads stay native."""

import pytest
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.urls import reverse

from celiaquia.models import PagoEstado, PagoExpediente, PagoNomina
from celiaquia.tests.test_permisos_dashboard_reporte import _usuario
from celiaquia.tests.test_tablero_celiaquia import _Datos
from core.models import Provincia

pytestmark = pytest.mark.django_db
ACCEPT = {"HTTP_ACCEPT": "application/json"}


@pytest.fixture
def enabled(settings):
    settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",)


@pytest.fixture
def pagos():
    provincia = Provincia.objects.create(nombre="Provincia Sintética")
    otra = Provincia.objects.create(nombre="Otra Provincia")
    user = _usuario("canonical_pagos_owner")
    viejo = PagoExpediente.objects.create(
        provincia=provincia,
        periodo="2026-01",
        estado=PagoEstado.BORRADOR,
        creado_por=user,
        total_candidatos=5,
        total_validados=3,
        total_excluidos=2,
    )
    nuevo = PagoExpediente.objects.create(
        provincia=provincia, periodo="2026-02", creado_por=user
    )
    PagoExpediente.objects.create(provincia=otra, periodo="2026-03", creado_por=user)
    return {"provincia": provincia, "user": user, "viejo": viejo, "nuevo": nuevo}


def test_list_projection_matches_native_queryset_and_columns(client, enabled, pagos):
    client.force_login(pagos["user"])
    provincia = pagos["provincia"]
    path = reverse("pago_expediente_list", args=[provincia.id])
    assert path == f"/celiaquia/pagos/provincia/{provincia.id}/"

    native = client.get(path, HTTP_ACCEPT="text/html")
    response = client.get(path, **ACCEPT)

    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    assert {"Accept", "Cookie"} <= set(response["Vary"].split(", "))
    data = response.json()
    assert data["version"] == 1
    assert data["provincia"] == {"id": provincia.id, "nombre": "Provincia Sintética"}
    assert [row["id"] for row in data["rows"]] == [
        p.id for p in native.context["pagos"]
    ]
    viejo = next(row for row in data["rows"] if row["id"] == pagos["viejo"].id)
    assert viejo == {
        "id": pagos["viejo"].id,
        "periodo": "2026-01",
        "estado": "BORRADOR",
        "candidatos": 5,
        "validados": 3,
        "excluidos": 2,
        "creado": pagos["viejo"].creado_en.strftime("%Y-%m-%d"),
        "url": reverse("pago_expediente_detail", args=[pagos["viejo"].id]),
    }
    assert data["urls"] == {
        "volver": reverse("cupo_provincia_detail", args=[provincia.id]),
        "crear": reverse("pago_expediente_create", args=[provincia.id]),
    }
    assert data["messages"] == []


def test_list_projection_unknown_provincia_is_404(client, enabled, pagos):
    client.force_login(pagos["user"])
    path = reverse("pago_expediente_list", args=[999999])
    assert client.get(path, **ACCEPT).status_code == 404


def test_detail_projection_fields_links_upload_and_nomina(client, enabled, pagos):
    pago = pagos["viejo"]
    pago.archivo_envio.save("envio.xlsx", ContentFile(b"x"), save=True)
    datos = _Datos()
    legajo = datos.legajo(datos.expediente(), pagos["provincia"])
    PagoNomina.objects.create(
        pago=pago,
        legajo=legajo,
        documento="20111222",
        nombre="Nombre Sintético",
        apellido="Apellido Sintético",
        observacion="ok",
    )
    client.force_login(pagos["user"])
    path = reverse("pago_expediente_detail", args=[pago.id])

    data = client.get(path, **ACCEPT).json()

    assert data["version"] == 1
    assert data["pago"] == {
        "id": pago.id,
        "provincia": {"id": pagos["provincia"].id, "nombre": "Provincia Sintética"},
        "periodo": "2026-01",
        "estado": "BORRADOR",
        "candidatos": 5,
        "validados": 3,
        "excluidos": 2,
    }
    assert data["urls"] == {
        "volver": reverse("cupo_provincia_detail", args=[pagos["provincia"].id]),
        "archivo_envio": reverse("pago_expediente_export", args=[pago.id]),
        "exportar_nomina": reverse("pago_nomina_export_actual", args=[pago.id]),
    }
    assert data["upload"] == {
        "action": path,
        "field": "archivo",
        "label": "Respuesta de Sintys (XLSX/CSV)",
        "required": True,
    }
    assert data["nomina"] == [
        {
            "documento": "20111222",
            "nombre": "Nombre Sintético",
            "apellido": "Apellido Sintético",
            "estado": PagoNomina.objects.get().estado,
            "observacion": "ok",
        }
    ]


def test_detail_without_envio_file_has_no_download_link(client, enabled, pagos):
    client.force_login(pagos["user"])
    path = reverse("pago_expediente_detail", args=[pagos["nuevo"].id])
    data = client.get(path, **ACCEPT).json()
    assert data["urls"]["archivo_envio"] is None
    assert data["nomina"] == []
    assert (
        client.get(
            reverse("pago_expediente_detail", args=[999999]), **ACCEPT
        ).status_code
        == 404
    )


def test_upload_stays_native_and_its_feedback_is_projected_once(client, enabled, pagos):
    client.force_login(pagos["user"])
    path = reverse("pago_expediente_detail", args=[pagos["viejo"].id])

    # Multipart form post without file: the native view validates and redirects.
    response = client.post(path, {})
    assert response.status_code == 302
    assert response["Location"] == path

    data = client.get(path, **ACCEPT).json()
    assert data["messages"] == [{"level": "error", "text": "Subí un archivo válido."}]
    assert client.get(path, **ACCEPT).json()["messages"] == []


def test_messages_are_projected_in_list(client, enabled, pagos):
    client.force_login(pagos["user"])
    provincia = pagos["provincia"]
    # The native export view leaves an error message when there is no file.
    client.get(reverse("pago_expediente_export", args=[pagos["nuevo"].id]))
    data = client.get(
        reverse("pago_expediente_list", args=[provincia.id]), **ACCEPT
    ).json()
    assert data["messages"] == [
        {"level": "error", "text": "El expediente no tiene archivo de envío."}
    ]


@pytest.mark.parametrize("enabled_flag,marker", [(False, "pagos"), (True, "cupos")])
def test_native_fallback_without_flag_or_marker(
    client, settings, monkeypatch, pagos, enabled_flag, marker
):
    settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",) if enabled_flag else ()
    monkeypatch.setattr(
        "core.v2_frontend.frontend_v2",
        lambda *a, **k: HttpResponse(
            f'<meta name="sisoc-celiaquia-{marker}" content="v1">'
        ),
    )
    client.force_login(pagos["user"])
    path = reverse("pago_expediente_list", args=[pagos["provincia"].id])
    response = client.get(path)
    assert response.status_code == 200
    assert "Expedientes de pago" in response.content.decode()
    if not enabled_flag:
        json_response = client.get(path, **ACCEPT)
        assert "Expedientes de pago" in json_response.content.decode()


@pytest.mark.parametrize(
    "screen,name,key",
    [
        ("pagos", "pago_expediente_list", "provincia"),
        ("pago-detalle", "pago_expediente_detail", "pago"),
    ],
)
def test_shell_served_with_screen_marker(
    client, enabled, monkeypatch, pagos, screen, name, key
):
    monkeypatch.setattr(
        "core.v2_frontend.frontend_v2",
        lambda *a, **k: HttpResponse(
            f'<meta name="sisoc-celiaquia-{screen}" content="v1">'
        ),
    )
    client.force_login(pagos["user"])
    arg = pagos["provincia"].id if key == "provincia" else pagos["viejo"].id
    response = client.get(reverse(name, args=[arg]))
    assert response.status_code == 200
    assert f"sisoc-celiaquia-{screen}".encode() in response.content


def test_anonymous_json_gets_same_status_as_native(client, enabled, pagos):
    # Pre-existing: these URLs carry no permission decorator; preserve exactly.
    path = reverse("pago_expediente_list", args=[pagos["provincia"].id])
    native_status = client.get(path, HTTP_ACCEPT="text/html").status_code
    assert client.get(path, **ACCEPT).status_code == native_status
