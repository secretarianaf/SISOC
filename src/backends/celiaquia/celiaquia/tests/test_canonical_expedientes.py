"""The canonical list projects the native scope and filters, not the V2 list."""

import json

import pytest
from django.http import HttpResponse
from django.urls import resolve, reverse

from celiaquia.models import EstadoExpediente, Expediente
from celiaquia.tests.test_permisos_dashboard_reporte import _usuario

pytestmark = pytest.mark.django_db
PATH = "/celiaquia/expedientes/"
ACCEPT = {"HTTP_ACCEPT": "application/json"}


def test_native_scope_filters_and_actions_are_projected(client, settings):
    settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",)
    owner = _usuario("canonical_owner", "view_expediente")
    other = _usuario("canonical_other", "view_expediente")
    state, _ = EstadoExpediente.objects.get_or_create(nombre="CREADO")
    own = Expediente.objects.create(
        usuario_provincia=owner, estado=state, numero_expediente="EX-ONE"
    )
    Expediente.objects.create(
        usuario_provincia=other, estado=state, numero_expediente="EX-OTHER"
    )
    client.force_login(owner)
    assert reverse("expediente_list") == PATH
    assert resolve(PATH, urlconf="celiaquia_runtime.urls").url_name == "expediente_list"
    response = client.get(
        PATH,
        {
            "q": "EX-",
            "filters": json.dumps(
                {
                    "logic": "AND",
                    "items": [{"field": "id", "op": "eq", "value": str(own.pk)}],
                }
            ),
        },
        **ACCEPT,
    )
    assert response.status_code == 200
    data = response.json()
    assert [row["id"] for row in data["rows"]] == [own.pk]
    assert data["rows"][0]["urls"]["detail"] == reverse(
        "expediente_detail", args=[own.pk]
    )
    assert data["create_url"] is None
    assert not data["rows"][0]["actions"]
    assert "tecnico" not in [f["name"] for f in data["filters"]["fields"]]
    assert response["Cache-Control"] == "private, no-store"
    assert {"Accept", "Cookie"} <= set(response["Vary"].split(", "))
    assert client.get(PATH, {"q": "EX-OTHER"}, **ACCEPT).json()["rows"] == []


def test_guard_precedes_json_and_static(client, settings, monkeypatch):
    settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",)

    def forbidden(*args, **kwargs):
        pytest.fail("unauthorized request reached static upstream")

    monkeypatch.setattr("core.v2_frontend.frontend_v2", forbidden)
    assert client.get(PATH, **ACCEPT).status_code == 403
    client.force_login(_usuario("canonical_denied", "view_reporte_provincias"))
    assert client.get(PATH, **ACCEPT).status_code == 403
    assert client.get(PATH).status_code == 403


@pytest.mark.parametrize("enabled,compatible", [(False, True), (True, False)])
def test_native_fallback_for_disabled_or_old_build(
    client, settings, monkeypatch, enabled, compatible
):
    client.force_login(_usuario("canonical_fallback", "view_expediente"))
    settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",) if enabled else ()
    calls = []

    def upstream(*args, **kwargs):
        calls.append(1)
        return HttpResponse('<meta name="sisoc-celiaquia-report" content="v1">')

    monkeypatch.setattr("core.v2_frontend.frontend_v2", upstream)
    response = client.get(PATH, {"q": "synthetic"})
    assert response.status_code == 200
    assert "celiaquia/expediente_list.html" in response.template_name
    assert ("Cache-Control" in response) == enabled
    assert calls == ([1] if enabled else [])


def test_shell_strips_query_keeps_marker_and_has_no_body_for_head(
    client, settings, monkeypatch
):
    client.force_login(_usuario("canonical_shell", "view_expediente"))
    settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",)
    calls = []
    shell = (
        b'<meta name="sisoc-celiaquia-expedientes" content="v1"><div id="root"></div>'
    )

    def upstream(request, module):
        calls.append((request.META["QUERY_STRING"], module))
        return HttpResponse(shell)

    monkeypatch.setattr("core.v2_frontend.frontend_v2", upstream)
    response = client.get(PATH, {"q": "private-filter"})
    assert response.content == shell
    assert "csrftoken" in response.cookies
    assert calls == [("", "celiaquia")]
    # XViewMiddleware answers HEAD for INTERNAL_IPS; use an external address.
    assert client.head(PATH, REMOTE_ADDR="203.0.113.15").content == b""
    assert client.post(PATH, {}).status_code == 405
