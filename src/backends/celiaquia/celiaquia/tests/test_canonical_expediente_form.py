"""Canonical alta/edición of Expedientes reuse the native form and views."""

import pytest
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone

from celiaquia.models import EstadoExpediente, Expediente
from celiaquia.tests.test_permisos_dashboard_reporte import _usuario

pytestmark = pytest.mark.django_db
NEW = "/celiaquia/expedientes/nuevo/"
ACCEPT = {"HTTP_ACCEPT": "application/json"}
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _edit(pk):
    return f"/celiaquia/expedientes/{pk}/editar/"


def _upload(name="carga.xlsx", content=b"excel-bytes"):
    return SimpleUploadedFile(name, content, content_type=XLSX)


@pytest.fixture
def enabled(settings, tmp_path):
    settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",)
    settings.MEDIA_ROOT = tmp_path
    EstadoExpediente.objects.get_or_create(nombre="CREADO")
    return settings


def _expediente(owner, **extra):
    state, _ = EstadoExpediente.objects.get_or_create(nombre="CREADO")
    expediente = Expediente.objects.create(
        usuario_provincia=owner,
        estado=state,
        numero_expediente="EX-ORIG",
        observaciones="original",
        **extra,
    )
    expediente.excel_masivo.save("original.xlsx", ContentFile(b"orig"), save=True)
    return expediente


def test_create_projection_exposes_native_fields_limits_and_urls(client, enabled):
    client.force_login(_usuario("form_new", "view_expediente"))
    assert reverse("expediente_create") == NEW
    response = client.get(NEW, **ACCEPT)
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == 1
    assert data["mode"] == "create"
    assert data["title"] == "Crear Expediente"
    assert data["expediente"] is None
    fields = data["fields"]
    assert fields["numero_expediente"] == {
        "label": "Número Expediente",
        "required": False,
        "max_length": 100,
        "value": "",
    }
    assert fields["observaciones"]["label"] == "Observaciones"
    assert fields["observaciones"]["value"] == ""
    excel = fields["excel_masivo"]
    assert excel["label"] == "Archivo Excel"
    assert excel["required"] is True
    assert excel["accept"] == ".xlsx"
    assert excel["max_bytes"] == 5 * 1024 * 1024
    assert excel["current"] is None
    assert data["urls"] == {
        "preview": reverse("expediente_preview_excel"),
        "plantilla": reverse("expediente_plantilla_excel"),
        "localidades": reverse("expediente_localidades_lookup"),
        "cancel": reverse("expediente_list"),
    }
    assert data["preview_max_limit"] == 5000
    assert isinstance(data["provincias"], list)
    assert response["Cache-Control"] == "private, no-store"


def test_valid_json_create_matches_native_create(client, enabled):
    user = _usuario("form_create", "view_expediente")
    client.force_login(user)
    response = client.post(
        NEW,
        {
            "numero_expediente": "EX-JSON",
            "observaciones": "nota",
            "excel_masivo": _upload(),
        },
        **ACCEPT,
    )
    assert response.status_code == 200
    expediente = Expediente.objects.get()
    assert response.json() == {
        "ok": True,
        "redirect": reverse("expediente_detail", args=[expediente.pk]),
    }
    assert expediente.numero_expediente == "EX-JSON"
    assert expediente.observaciones == "nota"
    assert expediente.usuario_provincia == user
    assert expediente.estado.nombre == "CREADO"
    assert expediente.excel_masivo_cargado_por == user
    assert expediente.excel_masivo.name.endswith(".xlsx")


@pytest.mark.parametrize(
    "payload,field",
    [
        ({}, "excel_masivo"),
        ({"excel_masivo": _upload("viejo.xls")}, "excel_masivo"),
        (
            {"excel_masivo": _upload(content=b"x" * (5 * 1024 * 1024 + 1))},
            "excel_masivo",
        ),
        (
            {"numero_expediente": "N" * 101, "excel_masivo": _upload()},
            "numero_expediente",
        ),
    ],
    ids=["missing", "xls", "too-big", "long-number"],
)
def test_invalid_json_create_returns_errors_and_creates_nothing(
    client, enabled, payload, field
):
    client.force_login(_usuario(f"form_bad_{field}_{len(payload)}", "view_expediente"))
    response = client.post(NEW, payload, **ACCEPT)
    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["errors"][field]
    assert all(isinstance(message, str) for message in body["errors"][field])
    assert Expediente.objects.count() == 0


def test_edit_projection_exposes_current_values_and_excel(client, enabled):
    owner = _usuario("form_edit_owner", "view_expediente")
    expediente = _expediente(owner)
    client.force_login(owner)
    assert reverse("expediente_update", args=[expediente.pk]) == _edit(expediente.pk)
    data = client.get(_edit(expediente.pk), **ACCEPT).json()
    assert data["mode"] == "edit"
    assert data["title"] == "Editar Expediente"
    assert data["expediente"] == {"id": expediente.pk, "numero": "EX-ORIG"}
    assert data["fields"]["numero_expediente"]["value"] == "EX-ORIG"
    assert data["fields"]["observaciones"]["value"] == "original"
    current = data["fields"]["excel_masivo"]["current"]
    assert current["name"].endswith("original.xlsx")
    assert current["url"] == expediente.excel_masivo.url
    assert data["urls"]["cancel"] == reverse("expediente_list")


def test_edit_replacing_excel_resets_processing_like_native(client, enabled):
    owner = _usuario("form_edit_proc", "view_expediente")
    editor = _usuario("form_edit_editor", "view_expediente")
    expediente = _expediente(
        owner,
        excel_masivo_procesado_por=owner,
        excel_masivo_procesado_en=timezone.now(),
    )
    client.force_login(editor)
    response = client.post(
        _edit(expediente.pk),
        {
            "numero_expediente": "EX-NEW",
            "observaciones": "nueva",
            "excel_masivo": _upload("nuevo.xlsx"),
        },
        **ACCEPT,
    )
    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "redirect": reverse("expediente_detail", args=[expediente.pk]),
    }
    expediente.refresh_from_db()
    assert expediente.numero_expediente == "EX-NEW"
    assert expediente.excel_masivo.name.endswith("nuevo.xlsx")
    assert expediente.excel_masivo_cargado_por == editor
    assert expediente.excel_masivo_procesado_por is None
    assert expediente.excel_masivo_procesado_en is None


def test_edit_without_new_file_keeps_excel_and_processing(client, enabled):
    owner = _usuario("form_edit_keep", "view_expediente")
    expediente = _expediente(
        owner,
        excel_masivo_procesado_por=owner,
        excel_masivo_procesado_en=timezone.now(),
    )
    original = expediente.excel_masivo.name
    client.force_login(owner)
    response = client.post(
        _edit(expediente.pk), {"numero_expediente": "EX-KEEP"}, **ACCEPT
    )
    assert response.status_code == 200
    expediente.refresh_from_db()
    assert expediente.numero_expediente == "EX-KEEP"
    assert expediente.excel_masivo.name == original
    assert expediente.excel_masivo_procesado_por == owner


def test_edit_rejects_xls_and_keeps_stored_values(client, enabled):
    owner = _usuario("form_edit_xls", "view_expediente")
    expediente = _expediente(owner)
    client.force_login(owner)
    response = client.post(
        _edit(expediente.pk),
        {"numero_expediente": "EX-BAD", "excel_masivo": _upload("viejo.xls")},
        **ACCEPT,
    )
    assert response.status_code == 400
    assert response.json()["errors"]["excel_masivo"]
    expediente.refresh_from_db()
    assert expediente.numero_expediente == "EX-ORIG"


def test_edit_missing_expediente_is_404(client, enabled):
    client.force_login(_usuario("form_edit_404", "view_expediente"))
    assert client.get(_edit(999999), **ACCEPT).status_code == 404
    assert client.post(_edit(999999), {}, **ACCEPT).status_code == 404


@pytest.mark.parametrize("method", ["get", "post"])
@pytest.mark.parametrize("path", [NEW, "/celiaquia/expedientes/1/editar/"])
def test_guard_precedes_json_and_static(client, enabled, monkeypatch, method, path):
    monkeypatch.setattr(
        "core.v2_frontend.frontend_v2",
        lambda *a, **k: pytest.fail("static upstream reached"),
    )
    call = getattr(client, method)
    assert call(path, **ACCEPT).status_code in {302, 403}
    client.force_login(
        _usuario(f"form_denied_{method}_{len(path)}", "view_reporte_provincias")
    )
    assert call(path, **ACCEPT).status_code == 403
    assert call(path).status_code == 403
    assert Expediente.objects.count() == 0


@pytest.mark.parametrize(
    "screen,path_of",
    [("expediente-nuevo", lambda e: NEW), ("expediente-editar", lambda e: _edit(e.pk))],
)
@pytest.mark.parametrize(
    "flag,build_marker,expected",
    [(False, True, "native"), (True, False, "native"), (True, True, "shell")],
)
def test_static_shell_needs_flag_and_screen_marker(
    client,
    settings,
    enabled,
    monkeypatch,
    screen,
    path_of,
    flag,
    build_marker,
    expected,
):
    owner = _usuario(f"form_shell_{screen}_{flag}_{build_marker}", "view_expediente")
    expediente = _expediente(owner)
    settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",) if flag else ()
    meta = screen if build_marker else "otra-pantalla"
    monkeypatch.setattr(
        "core.v2_frontend.frontend_v2",
        lambda *a, **k: HttpResponse(
            f'<meta name="sisoc-celiaquia-{meta}" content="v1">'.encode()
        ),
    )
    client.force_login(owner)
    response = client.get(path_of(expediente))
    assert response.status_code == 200
    is_shell = f"sisoc-celiaquia-{screen}".encode() in response.content
    assert is_shell == (expected == "shell")
    if expected == "native":
        assert b'id="expediente-form"' in response.content


def test_non_json_post_still_reaches_native_view(client, enabled):
    user = _usuario("form_native_post", "view_expediente")
    client.force_login(user)
    response = client.post(
        NEW, {"numero_expediente": "EX-HTML", "excel_masivo": _upload()}
    )
    expediente = Expediente.objects.get()
    assert response.status_code == 302
    assert response["Location"] == reverse("expediente_detail", args=[expediente.pk])
    invalid = client.post(NEW, {"excel_masivo": _upload("viejo.xls")})
    assert invalid.status_code == 200
    assert b'id="expediente-form"' in invalid.content
    assert Expediente.objects.count() == 1


def test_json_post_without_flag_is_native(client, settings, enabled):
    settings.REACT_VERTICALES_ACTIVAS = ()
    client.force_login(_usuario("form_flag_off", "view_expediente"))
    response = client.post(NEW, {"excel_masivo": _upload()}, **ACCEPT)
    assert response.status_code == 302
    assert Expediente.objects.count() == 1
