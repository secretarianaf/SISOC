"""Canonical Cupos screens project the native dashboard and province context."""

import pytest
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.urls import reverse

from ciudadanos.models import Ciudadano
from core.models import Provincia
from celiaquia.models import (
    CupoMovimiento,
    EstadoCupo,
    EstadoExpediente,
    EstadoLegajo,
    Expediente,
    ExpedienteCiudadano,
    ProvinciaCupo,
    ResultadoSintys,
    RevisionTecnico,
)
from celiaquia.services.cupo_service import CupoService
from celiaquia.tests.test_permisos_dashboard_reporte import _usuario

pytestmark = pytest.mark.django_db
DASHBOARD = "/celiaquia/cupos/"
ACCEPT = {"HTTP_ACCEPT": "application/json"}


def _province_path(provincia):
    return f"/celiaquia/cupos/provincia/{provincia.pk}/"


def _legajo(expediente, provincia, documento, **fields):
    ciudadano = Ciudadano.objects.create(
        apellido="Synthetic",
        nombre=f"N{documento}",
        documento=documento,
        provincia=provincia,
    )
    estado, _ = EstadoLegajo.objects.get_or_create(nombre="VALIDO")
    values = {
        "rol": ExpedienteCiudadano.ROLE_BENEFICIARIO,
        "revision_tecnico": RevisionTecnico.APROBADO,
        "resultado_sintys": ResultadoSintys.MATCH,
    }
    values.update(fields)
    return ExpedienteCiudadano.objects.create(
        expediente=expediente, ciudadano=ciudadano, estado=estado, **values
    )


@pytest.fixture
def scenario():
    provincia = Provincia.objects.create(nombre="Synthetica")
    ProvinciaCupo.objects.create(provincia=provincia, total_asignado=5, usados=0)
    owner = _usuario("cupos_owner")
    estado, _ = EstadoExpediente.objects.get_or_create(nombre="CRUCE_FINALIZADO")
    expediente = Expediente.objects.create(usuario_provincia=owner, estado=estado)
    active = _legajo(expediente, provincia, 30000001)
    CupoService.reservar_slot(legajo=active, usuario=owner)
    suspended = _legajo(expediente, provincia, 30000002)
    CupoService.reservar_slot(legajo=suspended, usuario=owner)
    CupoService.suspender_slot(legajo=suspended, usuario=owner, motivo="Synthetic")
    waiting = _legajo(
        expediente,
        provincia,
        30000003,
        estado_cupo=EstadoCupo.FUERA,
        es_titular_activo=False,
    )
    return {
        "provincia": provincia,
        "active": active,
        "suspended": suspended,
        "waiting": waiting,
    }


def _enabled(settings):
    settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",)


def test_dashboard_projects_native_rows_including_unconfigured(
    client, settings, scenario
):
    _enabled(settings)
    empty = Provincia.objects.create(nombre="Zeta sin cupo")
    client.force_login(_usuario("cupos_viewer", "view_cupo_dashboard"))
    native = client.get(DASHBOARD, HTTP_ACCEPT="text/html")
    native_rows = native.context["rows"]

    response = client.get(DASHBOARD, **ACCEPT)

    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    data = response.json()
    assert data["version"] == 1
    assert [row["provincia"]["id"] for row in data["rows"]] == [
        row["provincia"].id for row in native_rows
    ]
    by_id = {row["provincia"]["id"]: row for row in data["rows"]}
    configured = by_id[scenario["provincia"].pk]
    assert configured == {
        "provincia": {"id": scenario["provincia"].pk, "nombre": "Synthetica"},
        "total_asignado": 5,
        "usados": 2,
        "disponibles": 3,
        "fuera": 1,
        "url": reverse("cupo_provincia_detail", args=[scenario["provincia"].pk]),
    }
    assert by_id[empty.pk]["total_asignado"] is None
    assert by_id[empty.pk]["fuera"] is None
    assert data["urls"]["expedientes"] == reverse("expediente_list")
    assert data["messages"] == []


def test_province_projection_matches_native_context_and_actions(
    client, settings, scenario
):
    _enabled(settings)
    provincia = scenario["provincia"]
    client.force_login(_usuario("cupos_province", "view_cupo_dashboard"))
    native = client.get(_province_path(provincia), HTTP_ACCEPT="text/html").context

    data = client.get(_province_path(provincia), **ACCEPT).json()

    assert data["version"] == 1
    assert data["provincia"] == {"id": provincia.pk, "nombre": "Synthetica"}
    assert data["metrics"] == native["metrics"]
    for key in ("ocupados", "suspendidos", "lista_espera"):
        assert [row["id"] for row in data[key]] == [leg.id for leg in native[key]]
    assert [m["id"] for m in data["movimientos"]] == [
        m.id for m in native["movimientos"]
    ]
    active = data["ocupados"][0]
    assert active["documento"] == "30000001"
    assert active["revision_tecnico"] == "APROBADO"
    assert active["estado_cupo"] == "DENTRO"
    assert active["es_titular_activo"] is True
    assert [a["kind"] for a in active["actions"]] == ["suspender", "baja"]
    assert active["actions"][0]["url"] == reverse(
        "cupo_legajo_suspender", args=[provincia.pk, scenario["active"].pk]
    )
    suspended = data["suspendidos"][0]
    assert [a["kind"] for a in suspended["actions"]] == ["reactivar", "baja"]
    assert suspended["actions"][0]["url"] == reverse(
        "cupo_legajo_reactivar", args=[provincia.pk, scenario["suspended"].pk]
    )
    assert data["lista_espera"][0]["actions"] == []
    movement = next(m for m in data["movimientos"] if m["tipo"] == "SUSPENDIDO")
    assert movement["usuario"] == "cupos_owner"
    assert movement["legajo"]["documento"] == "30000002"
    assert data["forms"] == {
        "baja": {"name": "motivo", "label": "Motivo de la baja", "required": True},
        "suspender": {
            "name": "motivo",
            "label": "Motivo de la suspensión",
            "required": True,
        },
    }
    assert data["urls"] == {
        "dashboard": reverse("cupo_dashboard"),
        "config": reverse("cupo_provincia_detail", args=[provincia.pk]),
        "pagos": reverse("pago_expediente_list", args=[provincia.pk]),
        "crear_pago": reverse("pago_expediente_create", args=[provincia.pk]),
    }
    assert data["csrf_token"]


def test_province_without_cupo_projects_null_metrics(client, settings):
    _enabled(settings)
    provincia = Provincia.objects.create(nombre="Sin configurar")
    client.force_login(_usuario("cupos_unset", "view_cupo_dashboard"))
    data = client.get(_province_path(provincia), **ACCEPT).json()
    assert data["metrics"] is None
    assert data["ocupados"] == data["movimientos"] == []


def test_unknown_province_is_404_as_native(client, settings):
    _enabled(settings)
    client.force_login(_usuario("cupos_404", "view_cupo_dashboard"))
    assert client.get("/celiaquia/cupos/provincia/999999/", **ACCEPT).status_code == 404


def test_pending_messages_are_projected_once(client, settings, monkeypatch, scenario):
    _enabled(settings)
    provincia = scenario["provincia"]
    client.force_login(_usuario("cupos_messages", "view_cupo_dashboard"))

    def reject(**kwargs):
        raise ValidationError("Synthetic rejection")

    monkeypatch.setattr(
        "celiaquia.views.pago.PagoService.crear_expediente_pago", reject
    )
    redirect = client.post(reverse("pago_expediente_create", args=[provincia.pk]))
    assert redirect["Location"] == _province_path(provincia)

    data = client.get(_province_path(provincia), **ACCEPT).json()
    assert data["messages"] == [{"level": "error", "text": "['Synthetic rejection']"}]
    assert client.get(_province_path(provincia), **ACCEPT).json()["messages"] == []


@pytest.mark.parametrize("path_kind", ["dashboard", "province"])
def test_guard_precedes_json_and_static(
    client, settings, monkeypatch, scenario, path_kind
):
    _enabled(settings)
    path = (
        DASHBOARD if path_kind == "dashboard" else _province_path(scenario["provincia"])
    )
    monkeypatch.setattr(
        "core.v2_frontend.frontend_v2",
        lambda *a, **k: pytest.fail("unauthorized request reached static upstream"),
    )
    assert client.get(path, **ACCEPT).status_code == 403
    client.force_login(_usuario(f"cupos_denied_{path_kind}", "view_expediente"))
    assert client.get(path, **ACCEPT).status_code == 403
    assert client.get(path).status_code == 403


@pytest.mark.parametrize("enabled,markers", [(False, ["cupos"]), (True, ["report"])])
def test_native_fallback_without_flag_or_marker(
    client, settings, monkeypatch, enabled, markers
):
    settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",) if enabled else ()
    body = "".join(f'<meta name="sisoc-celiaquia-{m}" content="v1">' for m in markers)
    monkeypatch.setattr(
        "core.v2_frontend.frontend_v2", lambda *a, **k: HttpResponse(body.encode())
    )
    client.force_login(_usuario(f"cupos_fallback_{enabled}", "view_cupo_dashboard"))
    response = client.get(DASHBOARD, **(ACCEPT if not enabled else {}))
    assert response.status_code == 200
    assert "celiaquia/cupo_dashboard.html" in [t.name for t in response.templates]


def test_province_shell_requires_its_own_marker(client, settings, monkeypatch):
    _enabled(settings)
    provincia = Provincia.objects.create(nombre="Shell")
    shell = b'<meta name="sisoc-celiaquia-cupo-provincia" content="v1"><div id="root"></div>'
    monkeypatch.setattr(
        "core.v2_frontend.frontend_v2", lambda *a, **k: HttpResponse(shell)
    )
    client.force_login(_usuario("cupos_shell", "view_cupo_dashboard"))
    assert client.get(_province_path(provincia)).content == shell


def test_unauthorized_posts_have_no_effect(client, settings, scenario):
    _enabled(settings)
    provincia = scenario["provincia"]
    client.force_login(_usuario("cupos_post_denied", "view_expediente"))
    config = client.post(
        _province_path(provincia),
        {"accion": "config", "total_asignado": "99"},
        **ACCEPT,
    )
    baja = client.post(
        reverse("cupo_legajo_baja", args=[provincia.pk, scenario["active"].pk]),
        {"motivo": "Synthetic"},
        **ACCEPT,
    )
    assert config.status_code == baja.status_code == 403
    assert ProvinciaCupo.objects.get(provincia=provincia).total_asignado == 5
    scenario["active"].refresh_from_db()
    assert scenario["active"].es_titular_activo is True
    assert CupoMovimiento.objects.filter(tipo="BAJA").count() == 0


def test_authorized_config_post_still_reaches_native_view(client, settings, scenario):
    _enabled(settings)
    provincia = scenario["provincia"]
    client.force_login(_usuario("cupos_config", "view_cupo_dashboard"))
    response = client.post(
        _province_path(provincia),
        {"accion": "config", "total_asignado": "7"},
        **ACCEPT,
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert ProvinciaCupo.objects.get(provincia=provincia).total_asignado == 7
