"""Canonical Sedes transport must agree with the native list and keep V2 intact."""

import json
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.http import HttpResponse
from django.urls import reverse
from ver_para_ser_libre.models import SedeVPSL

pytestmark = pytest.mark.django_db


@pytest.fixture
def sedes():
    def create(number, **extra):
        return SedeVPSL.objects.create(
            nombre=f"Escuela {number:02}",
            cueanexo=f"CUE-{number}",
            jurisdiccion="Buenos Aires",
            localidad="Centro",
            domicilio="Calle educativa",
            checklist_aprobado=True,
            **extra,
        )

    matches = [create(i) for i in range(16)]
    SedeVPSL.objects.create(
        nombre="Excluir checklist",
        localidad="Centro",
        jurisdiccion="Buenos Aires",
        domicilio="Calle educativa",
        checklist_aprobado=False,
    )
    SedeVPSL.objects.create(
        nombre="Excluir localidad",
        localidad="Sur",
        jurisdiccion="Buenos Aires",
        domicilio="Calle educativa",
        checklist_aprobado=True,
    )
    return matches


def query():
    return {
        "busqueda": "educativa",
        "page": "2",
        "filters": json.dumps(
            {
                "logic": "AND",
                "items": [
                    {"field": "localidad", "op": "eq", "value": "Centro"},
                    {"field": "checklist_aprobado", "op": "eq", "value": "true"},
                ],
            }
        ),
    }


def test_canonical_sedes_json_reuses_native_filters_page_and_permission(
    client, settings, sedes
):
    url = reverse("vpsl_sede_list")
    assert client.get(url, query(), HTTP_ACCEPT="application/json").status_code == 403
    user = get_user_model().objects.create_user(username="sedes-reader")
    user.user_permissions.add(Permission.objects.get(codename="view_sedevpsl"))
    client.force_login(user)
    settings.REACT_VERTICALES_ACTIVAS = ()
    native = client.get(url, query())
    assert [item.pk for item in native.context["sedes"]] == [sedes[-1].pk]
    settings.REACT_VERTICALES_ACTIVAS = ("vpsl",)
    response = client.get(url, query(), HTTP_ACCEPT="application/json")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 16
    assert data["page"] == 2 and data["pages"] == 2 and data["page_size"] == 15
    assert [item["id"] for item in data["results"]] == [sedes[-1].pk]
    assert "checklist_aprobado" in [
        field["name"] for field in data["filters_config"]["fields"]
    ]
    assert (
        "private" in response["Cache-Control"]
        and "no-store" in response["Cache-Control"]
    )
    assert {"accept", "cookie"} <= {
        value.strip().lower() for value in response["Vary"].split(",")
    }
    assert (
        client.get(url, {"page": 999}, HTTP_ACCEPT="application/json").status_code
        == 404
    )
    last = client.get(url, {**query(), "page": "last"}, HTTP_ACCEPT="application/json")
    assert last.status_code == 200 and last.json()["page"] == 2


@pytest.mark.parametrize(
    "marker,enabled,react",
    [
        ('<meta name="sisoc-vpsl-canonical" content="v1">', True, False),
        (
            '<meta name="sisoc-vpsl-canonical" content="v1"><meta name="sisoc-vpsl-sedes" content="v1">',
            True,
            True,
        ),
        (
            '<meta name="sisoc-vpsl-canonical" content="v1"><meta name="sisoc-vpsl-sedes" content="v1">',
            False,
            False,
        ),
    ],
)
def test_filtered_navigation_requires_compatible_build_and_keeps_rollback(
    admin_client, settings, monkeypatch, sedes, marker, enabled, react
):
    settings.REACT_VERTICALES_ACTIVAS = ("vpsl",) if enabled else ()
    requests = []

    def shell(request, module):
        requests.append(request.META["QUERY_STRING"])
        return HttpResponse(marker + '<div id="vpsl-react"></div>')

    monkeypatch.setattr("core.v2_frontend.frontend_v2", shell)
    url = reverse("vpsl_sede_list")
    response = admin_client.get(url, query())
    assert response.status_code == 200
    assert (b'id="vpsl-react"' in response.content) == react
    assert ("accept" in response.get("Vary", "").lower()) == enabled
    assert requests == ([""] if enabled else [])
    assert admin_client.get(url, {"page": "999"}).status_code == 404
    assert admin_client.get(url, {"page": "invalid"}).status_code == 404
    head = admin_client.head(url, query())
    assert head.status_code == 200 and head.content == b""
    if not enabled:
        # Flag off: the URL answers only the native HTML, never the projection.
        off = admin_client.get(url, query(), HTTP_ACCEPT="application/json")
        assert off["Content-Type"].startswith("text/html")
        assert "Cache-Control" not in off
        settings.REACT_VERTICALES_ACTIVAS = ("vpsl",)
    before_json_requests = list(requests)
    data = admin_client.get(url, query(), HTTP_ACCEPT="application/json").json()
    assert data["count"] == 16 and data["page"] == 2
    # Independent regression probe: JSON never forwards to the static upstream.
    assert requests == before_json_requests
    # The V2 transport intentionally retains q and its old field selection.
    legacy = admin_client.get(reverse("vpsl_api_sedes"), {"q": "educativa"})
    assert legacy.status_code == 200 and legacy.json()["count"] == 0


def test_advanced_groups_invalid_filters_and_denial_have_native_parity(
    client, admin_client, sedes
):
    url = reverse("vpsl_sede_list")
    before = list(SedeVPSL.objects.values())
    user = get_user_model().objects.create_user(username="sedes-denied")
    client.force_login(user)
    assert client.get(url, HTTP_ACCEPT="application/json").status_code == 403
    assert (
        client.post(
            url, {"nombre": "No autorizado"}, HTTP_ACCEPT="application/json"
        ).status_code
        == 403
    )
    for payload in (
        "invalid",
        '{"items":[{"field":"not_a_field","op":"eq","value":"x"}]}',
        json.dumps(
            {
                "logic": "AND",
                "items": [
                    {"field": "localidad", "op": "eq", "value": "Centro"},
                    {"field": "localidad", "op": "eq", "value": "Sur"},
                    {"field": "checklist_aprobado", "op": "eq", "value": "false"},
                ],
            }
        ),
    ):
        params = {"filters": payload}
        native = admin_client.get(url, params)
        response = admin_client.get(url, params, HTTP_ACCEPT="application/json")
        assert response.status_code == 200
        assert [item.pk for item in native.context["sedes"]] == [
            item["id"] for item in response.json()["results"]
        ]
        assert native.context["paginator"].count == response.json()["count"]
    assert list(SedeVPSL.objects.values()) == before
