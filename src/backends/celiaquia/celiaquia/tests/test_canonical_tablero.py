"""Canonical Tablero projects the native aggregated data behind the URL guard."""

import json

import pytest
from django.http import HttpResponse
from django.urls import reverse

# `datos` is a pytest fixture reused from the native tablero tests.
from celiaquia.tests.test_tablero_celiaquia import (  # noqa: F401
    _permiso,
    _usuario,
    datos,
)

pytestmark = pytest.mark.django_db
URL = "/celiaquia/tablero/"
ACCEPT = {"HTTP_ACCEPT": "application/json"}


@pytest.fixture
def enabled(settings):
    settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",)


def test_projection_matches_native_context(client, enabled, datos):  # noqa: F811
    client.force_login(_usuario("canonical_tablero"))
    native = client.get(URL, HTTP_ACCEPT="text/html")

    response = client.get(URL, **ACCEPT)

    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    assert {"Accept", "Cookie"} <= set(response["Vary"].split(", "))
    data = response.json()
    assert data["version"] == 1
    # Same aggregated payload the native json_script receives.
    assert data["datos"] == json.loads(json.dumps(native.context["tablero_datos"]))
    assert data["url_expediente"] == ""
    assert data["messages"] == []
    content = response.content.decode()
    assert "Apellido Ficticio" not in content
    assert "Juana Ficticia" not in content


def test_expediente_link_only_with_view_expediente(client, enabled, db):
    usuario = _usuario("canonical_tablero_exp")
    usuario.user_permissions.add(_permiso("view_expediente"))
    client.force_login(usuario)
    data = client.get(URL, **ACCEPT).json()
    assert data["url_expediente"] == reverse("expediente_detail", args=[0])


def test_guard_precedes_json_and_static(client, enabled, monkeypatch, db):
    monkeypatch.setattr(
        "core.v2_frontend.frontend_v2",
        lambda *a, **k: pytest.fail("unauthorized request reached static upstream"),
    )
    assert client.get(URL, **ACCEPT).status_code == 403
    assert client.get(URL).status_code == 403
    client.force_login(_usuario("canonical_tablero_denied", con_permiso=False))
    assert client.get(URL, **ACCEPT).status_code == 403
    assert client.get(URL).status_code == 403


def test_shell_with_marker(client, enabled, monkeypatch, db):
    monkeypatch.setattr(
        "core.v2_frontend.frontend_v2",
        lambda *a, **k: HttpResponse(
            '<meta name="sisoc-celiaquia-tablero" content="v1">'
        ),
    )
    client.force_login(_usuario("canonical_tablero_shell"))
    response = client.get(URL)
    assert response.status_code == 200
    assert b"sisoc-celiaquia-tablero" in response.content


@pytest.mark.parametrize("enabled_flag,marker", [(False, "tablero"), (True, "cupos")])
def test_native_fallback_without_flag_or_marker(
    client, settings, monkeypatch, db, enabled_flag, marker
):
    settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",) if enabled_flag else ()
    monkeypatch.setattr(
        "core.v2_frontend.frontend_v2",
        lambda *a, **k: HttpResponse(
            f'<meta name="sisoc-celiaquia-{marker}" content="v1">'
        ),
    )
    client.force_login(_usuario("canonical_tablero_fallback"))
    response = client.get(URL)
    assert response.status_code == 200
    assert 'id="cel-tablero-datos"' in response.content.decode()
    if not enabled_flag:
        assert 'id="cel-tablero-datos"' in client.get(URL, **ACCEPT).content.decode()
