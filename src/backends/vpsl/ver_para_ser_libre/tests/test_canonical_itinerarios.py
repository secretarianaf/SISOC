"""Canonical itinerary filters reuse native authorization, scope and pagination."""

import json
from datetime import date

import pytest
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse

from core.models import Provincia
from ver_para_ser_libre.tests.test_workflow import (
    crear_itinerario,
    crear_sede,
    hacer_usuario_provincial,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def itineraries():
    own = Provincia.objects.create(nombre="Buenos Aires")
    other = Provincia.objects.create(nombre="Cordoba")
    sede = crear_sede(cueanexo="T9B", localidad="Centro")
    items = [
        crear_itinerario(
            provincia=own,
            sedes=[sede],
            codigo=f"T9B-{i:02}",
            fecha_inicio=date(2026, 11, i + 1),
            fecha_fin=date(2026, 11, 30),
            localidades_tentativas="Centro",
            referente_nombre="Programa educativo",
            matricula_estimada=100,
        )
        for i in range(11)
    ]
    foreign = crear_itinerario(
        provincia=other,
        sedes=[sede],
        codigo="T9B-FOREIGN",
        fecha_inicio=date(2026, 11, 15),
        fecha_fin=date(2026, 11, 30),
        localidades_tentativas="Centro",
        referente_nombre="Programa educativo",
        matricula_estimada=100,
    )
    return own, other, items, foreign


def params(other):
    return {
        "busqueda": "Programa",
        "buscar_por": "referente",
        "estado": "borrador",
        "provincia": str(other.pk),
        "localidad": "Centro",
        "fecha_desde": "2026-11-01",
        "fecha_hasta": "2026-11-30",
        "page": "2",
        "filters": json.dumps(
            {
                "logic": "AND",
                "items": [{"field": "matricula_estimada", "op": "gt", "value": 50}],
            }
        ),
    }


def test_canonical_json_preserves_native_territory_before_all_filters(
    client, settings, itineraries
):
    own, other, items, foreign = itineraries
    url = reverse("vpsl_itinerario_list")
    assert client.get(url, HTTP_ACCEPT="application/json").status_code == 403
    user = get_user_model().objects.create_user(username="itinerary-reader")
    hacer_usuario_provincial(user, own)
    user.user_permissions.add(Permission.objects.get(codename="view_itinerariovpsl"))
    client.force_login(user)
    settings.REACT_VERTICALES_ACTIVAS = ()
    native = client.get(url, params(other))
    assert native.status_code == 200
    assert [item.pk for item in native.context["itinerarios"]] == [items[0].pk]
    settings.REACT_VERTICALES_ACTIVAS = ("vpsl",)
    response = client.get(url, params(other), HTTP_ACCEPT="application/json")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 11 and data["page_size"] == 10 and data["page"] == 2
    assert [item["id"] for item in data["results"]] == [items[0].pk]
    assert foreign.pk not in [item["id"] for item in data["results"]]
    assert data["provincia_restringida"]["id"] == own.pk
    assert "matricula_estimada" in [
        field["name"] for field in data["filters_config"]["fields"]
    ]
    assert data["provincias"] and data["estados"]
    assert response["Cache-Control"] == "private, no-store"
    assert {"accept", "cookie"} <= {
        v.strip().lower() for v in response["Vary"].split(",")
    }


@pytest.mark.parametrize(
    "permission",
    [None, "create_itinerarios_any_province_vpsl", "view_all_itinerarios_vpsl"],
)
def test_native_scope_cannot_be_broadened_by_province_or_advanced_or(
    client, itineraries, permission
):
    own, other, items, foreign = itineraries
    user = get_user_model().objects.create_user(username="scoped-reader")
    user.user_permissions.add(Permission.objects.get(codename="view_itinerariovpsl"))
    if permission:
        user.user_permissions.add(Permission.objects.get(codename=permission))
    foreign.creado_por = user
    foreign.save(update_fields=["creado_por"])
    client.force_login(user)
    query = {
        "filters": json.dumps(
            {
                "logic": "OR",
                "items": [
                    {"field": "provincia", "op": "eq", "value": "Buenos Aires"},
                    {"field": "provincia", "op": "eq", "value": "Cordoba"},
                ],
            }
        )
    }
    response = client.get(
        reverse("vpsl_itinerario_list"), query, HTTP_ACCEPT="application/json"
    )
    expected = (
        12 if permission == "view_all_itinerarios_vpsl" else 1 if permission else 0
    )
    assert response.json()["count"] == expected
    if permission == "create_itinerarios_any_province_vpsl":
        assert [row["id"] for row in response.json()["results"]] == [foreign.pk]


@pytest.mark.parametrize(
    "query,expected",
    [
        ({"busqueda": "T9B-00", "buscar_por": "codigo"}, 1),
        ({"busqueda": "Buenos Aires", "buscar_por": "provincia"}, 11),
        ({"busqueda": "Borrador", "buscar_por": "estado"}, 12),
        (
            {
                "localidad": "Centro",
                "fecha_desde": "2026-11-30",
                "fecha_hasta": "2026-11-01",
            },
            1,
        ),
        ({"fecha_desde": "2026-12-01"}, 0),
        ({"filters": "invalid"}, 12),
    ],
)
def test_simple_and_advanced_filters_match_native_rows_and_order(
    admin_client, settings, itineraries, query, expected
):
    settings.REACT_VERTICALES_ACTIVAS = ()
    url = reverse("vpsl_itinerario_list")
    native = admin_client.get(url, query)
    settings.REACT_VERTICALES_ACTIVAS = ("vpsl",)
    data = admin_client.get(url, query, HTTP_ACCEPT="application/json").json()
    assert data["count"] == expected == native.context["paginator"].count
    assert [row["id"] for row in data["results"]] == [
        item.pk for item in native.context["itinerarios"]
    ]
    # V2 continues accepting q; busqueda is deliberately not substituted for it.
    legacy = admin_client.get(reverse("vpsl_api_itinerarios"), {"q": "T9B-FOREIGN"})
    assert legacy.json()["count"] == 1


@pytest.mark.parametrize(
    "marker,enabled,react",
    [
        ('<meta name="sisoc-vpsl-canonical" content="v1">', True, False),
        ('<meta name="sisoc-vpsl-itinerarios" content="v1">', True, True),
        ('<meta name="sisoc-vpsl-itinerarios" content="v1">', False, False),
    ],
)
def test_itinerary_shell_marker_fallback_and_transport_isolation(
    admin_client, settings, monkeypatch, itineraries, marker, enabled, react
):
    settings.REACT_VERTICALES_ACTIVAS = ("vpsl",) if enabled else ()
    calls = []

    def shell(request, module):
        calls.append(request.META["QUERY_STRING"])
        return HttpResponse(marker + '<div id="itinerario-react"></div>')

    monkeypatch.setattr("core.v2_frontend.frontend_v2", shell)
    url = reverse("vpsl_itinerario_list")
    query = {"busqueda": "T9B", "page": "2"}
    html = admin_client.get(url, query)
    assert (b"itinerario-react" in html.content) == react
    assert calls == ([""] if enabled else [])
    if not enabled:
        # Flag off: the URL answers only the native HTML, never the projection.
        off = admin_client.get(url, query, HTTP_ACCEPT="application/json")
        assert off["Content-Type"].startswith("text/html")
        assert "Cache-Control" not in off
        settings.REACT_VERTICALES_ACTIVAS = ("vpsl",)
    before = list(calls)
    data = admin_client.get(url, query, HTTP_ACCEPT="application/json")
    assert data.status_code == 200 and data.json()["count"] == 12
    assert data.json()["page"] == 2 and calls == before
    for page in (0, 999, "invalid"):
        assert (
            admin_client.get(
                url, {"page": page}, HTTP_ACCEPT="application/json"
            ).status_code
            == 404
        )
    assert (
        admin_client.get(url, {"page": "last"}, HTTP_ACCEPT="application/json").json()[
            "page"
        ]
        == 2
    )
    head = admin_client.head(url, query)
    assert head.status_code == 200 and head.content == b""
    assert admin_client.post(url, {}, HTTP_ACCEPT="application/json").status_code == 405
