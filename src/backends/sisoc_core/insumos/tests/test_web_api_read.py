"""HTTP seams for the session-only INS-A read API."""

from datetime import datetime, timedelta, timezone

import pytest
from django.contrib.auth.models import Permission, User
from django.db import connection
from django.test.utils import CaptureQueriesContext
from drf_spectacular.generators import SchemaGenerator
from rest_framework.test import APIClient

from core.models import Programa
from insumos.models import Insumo, InsumoCategoria


@pytest.fixture
def read_user(db):
    user = User.objects.create_user(
        username="visual_reader", first_name="Persona Sintética"
    )
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="insumos",
            codename="view_insumo",
        )
    )
    return user


@pytest.fixture
def read_items(read_user):
    program = Programa.objects.create(nombre="Programa sintético")
    categories = [
        InsumoCategoria.objects.create(
            programa=program,
            nombre=name,
            orden=order,
            activo=active,
        )
        for name, order, active in (
            ("Manuales A", 1, True),
            ("Manuales B", 2, True),
            ("Inactiva", 3, False),
        )
    ]
    items = {}
    for number in range(1, 26):
        category = (
            categories[0]
            if number <= 21
            else (
                categories[1]
                if number == 22
                else categories[2] if number == 23 else None
            )
        )
        item = Insumo.objects.create(
            programa=program,
            categoria=category,
            titulo=f"Manual {number:02}",
            descripcion="búsqueda especial" if number == 2 else "Texto sintético",
            archivo=f"insumos/private/path/manual-{number}.pdf",
            activo=number != 3,
            usuario_creacion=None if number == 24 else read_user,
        )
        stamp = datetime(2026, 10, 27, 3, tzinfo=timezone.utc) + timedelta(
            minutes=number
        )
        Insumo.objects.filter(pk=item.pk).update(fecha_creacion=stamp)
        items[number] = item
    return categories, items


@pytest.mark.parametrize("path", ["/api/web/insumos/", "/api/web/insumos/options/"])
@pytest.mark.parametrize("method", ["get", "head"])
def test_read_api_requires_cookie_session_without_redirect(path, method):
    response = getattr(APIClient(), method)(path)
    assert response.status_code == 401
    assert "Location" not in response
    assert response["WWW-Authenticate"] == "Session"
    assert "private" in response["Cache-Control"]
    assert "no-store" in response["Cache-Control"]
    assert "Cookie" in response["Vary"]
    if method == "head":
        assert response.content == b""


def test_read_api_does_not_accept_token_only_authentication(read_user):
    from rest_framework.authtoken.models import Token

    token = Token.objects.create(user=read_user)

    response = APIClient().get(
        "/api/web/insumos/", HTTP_AUTHORIZATION=f"Token {token.key}"
    )

    assert response.status_code == 401
    assert response["WWW-Authenticate"] == "Session"


def test_inactive_user_session_cannot_access_read_api(read_user):
    read_user.is_active = False
    read_user.save(update_fields=["is_active"])
    client = APIClient()
    client.force_login(read_user)

    response = client.get("/api/web/insumos/")

    assert response.status_code == 401
    assert response["WWW-Authenticate"] == "Session"


def test_missing_profile_is_denied_without_creating_profile(read_user):
    client = APIClient()
    client.force_login(read_user)
    read_user.profile.delete()
    read_user.refresh_from_db()

    response = client.get("/api/web/insumos/")

    assert response.status_code == 403
    assert response.json()["state"] == "web_access_denied"
    assert response.json()["required_action_url"] is None
    assert not hasattr(read_user, "profile")


def test_pending_access_precedes_view_permission_check(read_user):
    profile = read_user.profile
    profile.acceso_web = False
    profile.save(update_fields=["acceso_web"])
    read_user.user_permissions.clear()
    client = APIClient()
    client.force_login(read_user)

    response = client.get("/api/web/insumos/")

    assert response.status_code == 403
    assert response.json()["state"] == "web_access_denied"


def test_read_projection_preserves_legacy_order_page_and_visible_fields(
    read_user, read_items
):
    client = APIClient()
    client.force_login(read_user)
    with CaptureQueriesContext(connection) as queries:
        response = client.get("/api/web/insumos/")
    assert response.status_code == 200
    payload = response.json()
    assert (
        payload["count"],
        payload["page"],
        payload["page_size"],
        payload["pages"],
    ) == (25, 1, 20, 2)
    items = read_items[1]
    expected = [
        25,
        24,
        21,
        20,
        19,
        18,
        17,
        16,
        15,
        14,
        13,
        12,
        11,
        10,
        9,
        8,
        7,
        6,
        5,
        4,
    ]
    assert [row["id"] for row in payload["results"]] == [items[n].pk for n in expected]
    assert payload["results"][0] == {
        "id": items[25].pk,
        "titulo": "Manual 25",
        "activo": True,
        "categoria": "Sin categoría",
        "fecha_carga": "27/10/2026 00:25",
        "cargado_por": "Persona Sintética",
        "download_url": f"/insumos/{items[25].pk}/descargar",
    }
    assert payload["results"][1]["cargado_por"] == "-"
    assert payload["filters"] == {"busqueda": "", "categoria": ""}
    assert all(
        not query["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        for query in queries
    )
    assert "private/path" not in response.content.decode()


@pytest.mark.parametrize("path", ["/api/web/insumos/", "/api/web/insumos/options/"])
def test_add_permission_never_grants_read_access(read_user, path):
    read_user.user_permissions.clear()
    read_user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="insumos",
            codename="add_insumo",
        )
    )
    client = APIClient()
    client.force_login(read_user)
    with CaptureQueriesContext(connection) as queries:
        response = client.get(path)
    assert response.status_code == 403
    assert not any('FROM "insumos_insumo"' in query["sql"] for query in queries)


@pytest.mark.parametrize(
    "flag,state,url",
    [
        ("acceso_web", "web_access_denied", None),
        ("must_change_password", "password_change_required", "/password/first-change/"),
        (
            "needs_profile_confirmation",
            "profile_confirmation_required",
            "/mi-cuenta/confirmar/",
        ),
    ],
)
def test_pending_prerequisite_rejects_before_business_query(
    read_user, flag, state, url
):
    profile = read_user.profile
    setattr(profile, flag, flag != "acceso_web")
    profile.save()
    client = APIClient()
    client.force_login(read_user)
    with CaptureQueriesContext(connection) as queries:
        response = client.get("/api/web/insumos/")
    assert response.status_code == 403
    assert response.json()["state"] == state
    assert response.json()["required_action_url"] == url
    assert not any('FROM "insumos_insumo"' in query["sql"] for query in queries)


def test_list_filters_trim_search_and_preserve_selected_values(read_user, read_items):
    client = APIClient()
    client.force_login(read_user)

    response = client.get(
        "/api/web/insumos/", {"busqueda": " búsqueda especial ", "categoria": "1"}
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert [row["id"] for row in payload["results"]] == [read_items[1][2].pk]
    assert payload["filters"] == {"busqueda": "búsqueda especial", "categoria": "1"}


@pytest.mark.parametrize(
    ("category", "expected_numbers"),
    [
        ("sin", [25, 24]),
        ("1", [21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2]),
    ],
)
def test_category_filter_matches_legacy_unassigned_and_numeric_semantics(
    read_user, read_items, category, expected_numbers
):
    client = APIClient()
    client.force_login(read_user)

    response = client.get("/api/web/insumos/", {"categoria": category})

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == (2 if category == "sin" else 21)
    assert [row["id"] for row in payload["results"]] == [
        read_items[1][number].pk for number in expected_numbers
    ]
    assert payload["filters"]["categoria"] == category


def test_list_pagination_supports_second_last_and_legacy_invalid_page_behavior(
    read_user, read_items
):
    client = APIClient()
    client.force_login(read_user)

    second = client.get("/api/web/insumos/", {"page": "2"})
    last = client.get("/api/web/insumos/", {"page": "last"})
    invalid = client.get("/api/web/insumos/", {"page": "not-a-page"})
    missing = client.get("/api/web/insumos/", {"page": "99"})

    assert second.status_code == 200
    assert second.json()["page"] == 2
    expected = [3, 2, 1, 22, 23]
    assert [row["id"] for row in second.json()["results"]] == [
        read_items[1][number].pk for number in expected
    ]
    assert last.status_code == 200
    assert last.json() == second.json()
    assert invalid.status_code == 404
    assert missing.status_code == 404


def test_non_numeric_category_filter_is_ignored_like_legacy(read_user, read_items):
    client = APIClient()
    client.force_login(read_user)

    response = client.get("/api/web/insumos/", {"categoria": "no-es-un-id"})

    assert response.status_code == 200
    assert response.json()["count"] == 25
    assert response.json()["filters"]["categoria"] == "no-es-un-id"
    assert [row["id"] for row in response.json()["results"]] == [
        read_items[1][number].pk for number in [25, 24, *range(21, 3, -1)]
    ]


def test_options_returns_only_active_categories_in_legacy_order(read_user, read_items):
    client = APIClient()
    client.force_login(read_user)

    response = client.get("/api/web/insumos/options/")

    assert response.status_code == 200
    assert response.json() == {
        "categories": [
            {"id": read_items[0][0].pk, "nombre": "Manuales A"},
            {"id": read_items[0][1].pk, "nombre": "Manuales B"},
        ]
    }


@pytest.mark.parametrize("path", ["/api/web/insumos/", "/api/web/insumos/options/"])
def test_authenticated_head_has_get_status_headers_and_no_body(
    read_user, read_items, path
):
    read_user.is_staff = True
    read_user.save(update_fields=["is_staff"])
    client = APIClient()
    client.force_login(read_user)

    get_response = client.get(path)
    head_response = client.head(path)

    assert head_response.status_code == get_response.status_code == 200
    assert head_response.content == b""
    for header in ("Content-Type", "Cache-Control", "Vary"):
        assert head_response[header] == get_response[header]


@pytest.mark.parametrize("path", ["/api/web/insumos/", "/api/web/insumos/options/"])
@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_unsupported_methods_return_405_without_domain_writes(
    read_user, read_items, path, method
):
    from django.test import Client

    client = Client(enforce_csrf_checks=True)
    client.force_login(read_user)
    session_response = client.get("/api/web/session/")
    csrf_token = session_response.cookies["csrftoken"].value

    with CaptureQueriesContext(connection) as queries:
        response = getattr(client, method)(path, HTTP_X_CSRFTOKEN=csrf_token)

    assert response.status_code == 405
    assert not any(
        query["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        for query in queries
    )


def test_unsupported_post_without_csrf_is_rejected_without_domain_writes(
    read_user, read_items
):
    from django.test import Client

    client = Client(enforce_csrf_checks=True)
    client.force_login(read_user)

    with CaptureQueriesContext(connection) as queries:
        response = client.post("/api/web/insumos/")

    assert response.status_code == 403
    assert not any(
        query["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        for query in queries
    )


def test_access_dependency_failure_does_not_grant_ready_or_read_items(
    read_user, read_items, monkeypatch
):
    def unavailable(_request):
        raise RuntimeError("synthetic dependency failure")

    monkeypatch.setattr(
        "usuarios.web_session.get_rondas_pendientes_para_request", unavailable
    )
    client = APIClient()
    client.raise_request_exception = False
    client.force_login(read_user)

    with CaptureQueriesContext(connection) as queries:
        response = client.get("/api/web/insumos/")

    assert response.status_code == 500
    assert not any('FROM "insumos_insumo"' in query["sql"] for query in queries)


def test_openapi_documents_read_filters_typed_dtos_and_cookie_only_auth():
    schema = SchemaGenerator().get_schema(request=None, public=True)
    operation = schema["paths"]["/api/web/insumos/"]["get"]
    options_operation = schema["paths"]["/api/web/insumos/options/"]["get"]
    page_schema = schema["components"]["schemas"]["InsumoPage"]
    options_schema = schema["components"]["schemas"]["InsumosOptions"]

    assert {parameter["name"] for parameter in operation["parameters"]} == {
        "busqueda",
        "categoria",
        "page",
    }
    assert operation["security"] == [{"cookieAuth": []}]
    assert options_operation["security"] == [{"cookieAuth": []}]
    assert set(page_schema["properties"]) == {
        "count",
        "page",
        "page_size",
        "pages",
        "filters",
        "results",
    }
    assert set(options_schema["properties"]) == {"categories"}
