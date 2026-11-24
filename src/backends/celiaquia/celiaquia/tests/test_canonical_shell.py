"""Generic canonical shell: per-screen marker, guard first, native fallback."""

import pytest
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory

from celiaquia.canonical_shell import canonical_screen
from celiaquia.tests.test_permisos_dashboard_reporte import _usuario

pytestmark = pytest.mark.django_db
PATH = "/celiaquia/cupos/"


def _native(request, *args, **kwargs):
    return HttpResponse(b"native")


def _shell(markers):
    body = "".join(f'<meta name="sisoc-celiaquia-{m}" content="v1">' for m in markers)
    return lambda request, module: HttpResponse(body.encode())


@pytest.mark.parametrize(
    "enabled,markers,expected",
    [
        (False, ["cupos"], "native"),
        (True, ["expedientes"], "native"),
        (True, ["cupos"], "shell"),
    ],
)
def test_screen_requires_flag_and_its_own_marker(
    client, settings, monkeypatch, enabled, markers, expected
):
    settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",) if enabled else ()
    monkeypatch.setattr("core.v2_frontend.frontend_v2", _shell(markers))
    client.force_login(_usuario("shell_cupos", "view_cupo_dashboard"))
    response = client.get(PATH, {"private": "1"})
    assert response.status_code == 200
    assert (b"sisoc-celiaquia-cupos" in response.content) == (expected == "shell")
    if enabled:
        assert response["Cache-Control"] == "private, no-store"
    else:
        assert "Cache-Control" not in response


def test_flag_off_keeps_native_headers(client, settings):
    settings.REACT_VERTICALES_ACTIVAS = ()
    client.force_login(_usuario("off_hdr", "view_cupo_dashboard"))
    response = client.get(PATH)
    assert response.status_code == 200
    assert "Cache-Control" not in response
    assert "Accept" not in response.get("Vary", "")


def test_url_guard_runs_before_shell(client, settings, monkeypatch):
    settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",)
    monkeypatch.setattr(
        "core.v2_frontend.frontend_v2",
        lambda *a, **k: pytest.fail("static upstream reached"),
    )
    client.force_login(_usuario("shell_denied", "view_expediente"))
    assert client.get(PATH).status_code == 403


def test_projection_and_submit_hooks_only_for_json_when_enabled(settings, monkeypatch):
    factory = RequestFactory()
    monkeypatch.setattr("core.v2_frontend.frontend_v2", _shell([]))
    view = canonical_screen(
        _native,
        "demo",
        projection=lambda request: JsonResponse({"kind": "projection"}),
        submit=lambda request: JsonResponse({"kind": "submit"}),
    )

    def call(method, accept, enabled=True):
        settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",) if enabled else ()
        request = getattr(factory, method)(PATH, HTTP_ACCEPT=accept)
        request.user = _usuario(f"hooks_{method}_{enabled}_{len(accept)}")
        return view(request).content

    assert b"projection" in call("get", "application/json")
    assert call("get", "text/html") == b"native"  # no compatible build
    assert b"submit" in call("post", "application/json")
    assert call("post", "text/html") == b"native"
    assert call("post", "application/json", enabled=False) == b"native"
    assert call("get", "application/json", enabled=False) == b"native"
