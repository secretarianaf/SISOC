"""The canonical Expediente detail projects the native view context, not V2."""

from datetime import date

import pytest
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.messages.storage.cookie import CookieStorage
from django.http import HttpResponse
from django.test import RequestFactory
from django.urls import reverse

from celiaquia.models import (
    EstadoExpediente,
    EstadoLegajo,
    Expediente,
    ExpedienteCiudadano,
    ExpedienteEstadoHistorial,
)
from celiaquia.models import AsignacionTecnico
from celiaquia.tests.test_permisos_dashboard_reporte import _rol, _usuario
from ciudadanos.models import Ciudadano
from core.models import Localidad, Municipio, Provincia
from users.models import Profile, ProfileTerritorialScope

pytestmark = pytest.mark.django_db
ACCEPT = {"HTTP_ACCEPT": "application/json"}


@pytest.fixture(autouse=True)
def _react(settings, monkeypatch):
    settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",)
    # A build without this screen's marker: HTML requests fall back to native.
    monkeypatch.setattr(
        "core.v2_frontend.frontend_v2",
        lambda request, module: HttpResponse(b"<html></html>"),
    )


def _with_role(user, codename):
    user.user_permissions.add(_rol(codename))
    return User.objects.get(pk=user.pk)


def _coord(username="detail_coord"):
    return _with_role(
        _usuario(username, "view_expediente"), "role_coordinadorceliaquia"
    )


def _tecnico(username="detail_tecnico"):
    return _with_role(_usuario(username, "view_expediente"), "role_tecnicoceliaquia")


def _provincial(username, *provincias):
    user = _with_role(_usuario(username, "view_expediente"), "role_provinciaceliaquia")
    profile = Profile.objects.get(user=user)
    profile.es_usuario_provincial = True
    profile.save()
    for provincia in provincias:
        ProfileTerritorialScope.objects.create(profile=profile, provincia=provincia)
    return User.objects.get(pk=user.pk)


def _estado(nombre):
    return EstadoExpediente.objects.get_or_create(nombre=nombre)[0]


_doc = iter(range(30000000, 39999999))


def _legajo(expediente, localidad=None, **extra):
    ciudadano = Ciudadano.objects.create(
        apellido="Synthetic",
        nombre=f"Person{next(_doc)}",
        fecha_nacimiento=date(2015, 1, 1),
        documento=next(_doc),
        **(
            {
                "provincia": localidad.municipio.provincia,
                "municipio": localidad.municipio,
                "localidad": localidad,
            }
            if localidad
            else {}
        ),
    )
    estado = EstadoLegajo.objects.get_or_create(nombre="DOCUMENTO_PENDIENTE")[0]
    return ExpedienteCiudadano.objects.create(
        expediente=expediente, ciudadano=ciudadano, estado=estado, **extra
    )


def _url(expediente):
    return reverse("expediente_detail", args=[expediente.pk])


def _territorio(nombre):
    provincia = Provincia.objects.create(nombre=f"{nombre} Prov")
    municipio = Municipio.objects.create(nombre=f"{nombre} Mun", provincia=provincia)
    return provincia, Localidad.objects.create(
        nombre=f"{nombre} Loc", municipio=municipio
    )


def test_scope_404_matches_native_for_each_role(client):
    owner = _usuario("detail_owner", "view_expediente")
    stranger = _usuario("detail_stranger", "view_expediente")
    expediente = Expediente.objects.create(
        usuario_provincia=owner, estado=_estado("ASIGNADO")
    )
    provincia, localidad = _territorio("Scoped")
    other_provincia, _ = _territorio("Other")
    _legajo(expediente, localidad)
    assigned, unassigned = _tecnico("detail_assigned"), _tecnico("detail_unassigned")
    AsignacionTecnico.objects.create(expediente=expediente, tecnico=assigned)
    cases = [
        (owner, 200),
        (stranger, 404),
        (_coord(), 200),
        (assigned, 200),
        (unassigned, 404),
        (_provincial("detail_prov_in", provincia), 200),
        (_provincial("detail_prov_out", other_provincia), 404),
    ]
    for user, status in cases:
        client.force_login(user)
        native = client.get(_url(expediente), HTTP_ACCEPT="text/html")
        projected = client.get(_url(expediente), **ACCEPT)
        assert (user.username, projected.status_code) == (user.username, status)
        if status == 200:
            assert projected.json()["version"] == 1
            assert projected.json()["expediente"]["id"] == expediente.pk
        else:
            assert native.status_code == 404


def _native_and_projected(client, user, expediente, params=None):
    client.force_login(user)
    native = client.get(_url(expediente), params or {}, HTTP_ACCEPT="text/html")
    assert "celiaquia/expediente_detail.html" in native.template_name
    projected = client.get(_url(expediente), params or {}, **ACCEPT)
    assert projected.status_code == 200
    assert projected["Cache-Control"] == "private, no-store"
    assert {"Accept", "Cookie"} <= set(projected["Vary"].split(", "))
    return native.context, projected.json()


@pytest.mark.parametrize(
    "role,state",
    [
        ("coord", "ASIGNADO"),
        ("tecnico", "PROCESO_DE_CRUCE"),
        ("prov", "EN_ESPERA"),
        ("prov", "CREADO"),
    ],
)
def test_role_flags_and_state_actions_equal_native_context(client, role, state):
    provincia, localidad = _territorio(f"Flags {role} {state}")
    factories = {"coord": _coord, "tecnico": _tecnico}
    user = factories.get(role, lambda name: _provincial(name, provincia))(
        f"flags_{role}_{state}"
    )
    expediente = Expediente.objects.create(
        usuario_provincia=user, estado=_estado(state), numero_expediente="EX-FLAGS"
    )
    if role == "tecnico":
        AsignacionTecnico.objects.create(expediente=expediente, tecnico=user)
    legajo = _legajo(expediente, localidad)
    ctx, data = _native_and_projected(client, user, expediente)
    assert data["roles"] == {
        "tecnico": ctx["is_tecnico_celiaquia"],
        "coordinador": ctx["is_coord_celiaquia"],
        "provincial": ctx["is_provincial_celiaquia"],
        "admin": ctx["is_admin_celiaquia"],
    }
    for flag in (
        "can_manage_registros_erroneos",
        "can_manage_excel_masivo_audit",
        "can_download_excel_masivo",
        "can_download_nomina_aprobados",
    ):
        assert data["flags"][flag] == ctx[flag]
    actions, row = data["actions"], data["legajos"][0]["actions"]
    nacion = role in {"coord", "tecnico"}
    assert bool(actions["nomina_sintys"]) is nacion
    assert actions["subir_cruce"] == (
        reverse("expediente_cruce_cuit", args=[expediente.pk]) if nacion else None
    )
    assert actions["editar"] == (
        reverse("expediente_update", args=[expediente.pk])
        if state == "CREADO"
        else None
    )
    expected_confirm = (
        reverse("expediente_confirm", args=[expediente.pk])
        if state == "EN_ESPERA"
        else None
    )
    assert actions["confirmar_envio"] == expected_confirm
    assert row["revisar"] == (
        reverse("legajo_revisar", args=[expediente.pk, legajo.pk]) if nacion else None
    )
    expected_upload = (
        reverse("legajo_archivo_upload", args=[expediente.pk, legajo.pk])
        if state == "EN_ESPERA"
        else None
    )
    assert row["subir_archivo"] == expected_upload
    assert bool(row["eliminar"]) is (role == "coord" or state == "EN_ESPERA")
    assert bool(row["agregar_comentario"]) is nacion
    assert row["corregir_evaluacion"] is None  # PENDIENTE legajo
    assert data["expediente"]["estado_display"] == expediente.estado.display_name()


def test_all_legajos_are_projected_without_truncation(client):
    owner = _usuario("detail_many", "view_expediente")
    expediente = Expediente.objects.create(
        usuario_provincia=owner, estado=_estado("EN_ESPERA")
    )
    created = {_legajo(expediente).pk for _ in range(27)}
    ctx, data = _native_and_projected(client, owner, expediente)
    assert {row["id"] for row in data["legajos"]} == created
    assert [row["id"] for row in data["legajos"]] == [
        leg.pk for leg in ctx["legajos_enriquecidos"]
    ]
    assert data["legajos_total"] == 27


def test_historial_page_parity_keeps_other_params(client):
    owner = _usuario("detail_hist", "view_expediente")
    estado = _estado("EN_ESPERA")
    expediente = Expediente.objects.create(usuario_provincia=owner, estado=estado)
    for index in range(7):
        ExpedienteEstadoHistorial.objects.create(
            expediente=expediente,
            estado_anterior=estado,
            estado_nuevo=estado,
            observaciones=f"obs {index}",
        )
    ctx, data = _native_and_projected(
        client, owner, expediente, {"historial_page": "2", "preview_limit": "10"}
    )
    assert data["historial"]["page"] == ctx["historial_page_obj"].number == 2
    assert data["historial"]["num_pages"] == 2
    assert [item["id"] for item in data["historial"]["items"]] == [
        h.pk for h in ctx["historial_page_obj"].object_list
    ]
    _, clamped = _native_and_projected(
        client, owner, expediente, {"historial_page": "999"}
    )
    assert clamped["historial"]["page"] == 2  # Paginator.get_page clamps like native


def test_preview_limit_parity(client, monkeypatch):
    calls = []

    def preview(archivo, max_rows=None):
        calls.append(max_rows)
        rows = [{"apellido": f"A{i}", "nombre": None} for i in range(12)]
        return {
            "headers": ["apellido", "nombre"],
            "rows": rows[:max_rows] if max_rows else rows,
        }

    monkeypatch.setattr(
        "celiaquia.views.expediente.ImportacionService.preview_excel", preview
    )
    owner = _with_role(
        _usuario("detail_preview", "view_expediente"), "role_provinciaceliaquia"
    )
    expediente = Expediente.objects.create(
        usuario_provincia=owner,
        estado=_estado("CREADO"),
        excel_masivo="celiaquia/synthetic.xlsx",
    )
    ctx, data = _native_and_projected(client, owner, expediente, {"preview_limit": "5"})
    assert data["preview"]["limit"] == ctx["preview_limit_actual"] == "5"
    assert data["preview"]["rows"] == [[f"A{i}", ""] for i in range(5)]
    assert data["preview"]["procesar"] == reverse(
        "expediente_procesar", args=[expediente.pk]
    )
    assert [option["value"] for option in data["preview"]["options"]] == ctx[
        "preview_limit_opciones"
    ]
    _, unbounded = _native_and_projected(client, owner, expediente)
    assert unbounded["preview"]["limit"] == "all"
    assert len(unbounded["preview"]["rows"]) == 12
    assert calls == [5, 5, None, None]


def test_guard_precedes_json_and_static(client, monkeypatch):
    owner = _usuario("detail_guard_owner", "view_expediente")
    expediente = Expediente.objects.create(
        usuario_provincia=owner, estado=_estado("CREADO")
    )
    monkeypatch.setattr(
        "core.v2_frontend.frontend_v2",
        lambda *a, **k: pytest.fail("static upstream reached"),
    )
    assert client.get(_url(expediente), **ACCEPT).status_code in {302, 403}
    client.force_login(_usuario("detail_denied", "view_reporte_provincias"))
    assert client.get(_url(expediente), **ACCEPT).status_code == 403
    assert client.get(_url(expediente)).status_code == 403


@pytest.mark.parametrize(
    "enabled,marker,expected",
    [(False, True, "native"), (True, False, "native"), (True, True, "shell")],
)
def test_shell_needs_flag_and_its_marker(
    client, settings, monkeypatch, enabled, marker, expected
):
    owner = _usuario(f"detail_shell_{enabled}_{marker}", "view_expediente")
    expediente = Expediente.objects.create(
        usuario_provincia=owner, estado=_estado("CREADO")
    )
    settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",) if enabled else ()
    screen = "expediente-detalle" if marker else "expedientes"
    body = f'<meta name="sisoc-celiaquia-{screen}" content="v1">'.encode()
    monkeypatch.setattr(
        "core.v2_frontend.frontend_v2", lambda request, module: HttpResponse(body)
    )
    client.force_login(owner)
    response = client.get(_url(expediente), {"historial_page": "2"})
    assert response.status_code == 200
    assert (response.content == body) is (expected == "shell")
    if expected == "native":
        assert "celiaquia/expediente_detail.html" in response.template_name
    if not enabled:
        json_request = client.get(_url(expediente), **ACCEPT)
        assert "celiaquia/expediente_detail.html" in json_request.template_name


def test_pending_messages_are_projected_once(client):
    owner = _usuario("detail_messages", "view_expediente")
    expediente = Expediente.objects.create(
        usuario_provincia=owner, estado=_estado("CREADO")
    )
    client.force_login(owner)
    assert client.get(_url(expediente), **ACCEPT).json()["messages"] == []
    # Queue a message the way a native redirecting POST does, then follow it.
    request = RequestFactory().get("/")
    storage = CookieStorage(request)
    storage.add(messages.SUCCESS, "Expediente sintético actualizado.")
    carrier = HttpResponse()
    storage.update(carrier)
    client.cookies[CookieStorage.cookie_name] = carrier.cookies[
        CookieStorage.cookie_name
    ].value
    first = client.get(_url(expediente), **ACCEPT).json()["messages"]
    assert first == [{"level": "success", "text": "Expediente sintético actualizado."}]
    assert client.get(_url(expediente), **ACCEPT).json()["messages"] == []


def test_corregir_and_subsanacion_actions_follow_native_conditions(client):
    coord = _coord("detail_corregir")
    expediente = Expediente.objects.create(
        usuario_provincia=coord, estado=_estado("ASIGNADO")
    )
    aprobado = _legajo(expediente, revision_tecnico="APROBADO")
    _, data = _native_and_projected(client, coord, expediente)
    row = next(item for item in data["legajos"] if item["id"] == aprobado.pk)
    expected = reverse("legajo_corregir_evaluacion", args=[expediente.pk, aprobado.pk])
    assert row["actions"]["corregir_evaluacion"] == expected
    assert row["actions"]["revisar"] is None
    assert row["estado"] == "Aprobado"
    assert row["actions"]["confirmar_subsanacion"] is None
