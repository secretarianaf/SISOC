"""HTTP contract for the core's session-only web context."""

from types import SimpleNamespace

import pytest
from django.contrib.admindocs.middleware import XViewMiddleware
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.models import Permission, User
from django.db import connection
from django.http import HttpResponse
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from users.models import Profile


@pytest.fixture
def web_user(db):
    user = User.objects.create_user(
        username="web_context",
        first_name="Usuario",
        last_name="Sintético",
        email="private@example.invalid",
    )
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.rol = "Pruebas"
    profile.save()
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="insumos",
            codename__in=["view_insumo", "add_insumo"],
        )
    )
    return user


@pytest.mark.parametrize("method", ["get", "head"])
def test_anonymous_context_is_private_401_without_redirect(method):
    response = getattr(APIClient(), method)("/api/web/session/")

    assert response.status_code == 401
    assert "Location" not in response
    assert response["WWW-Authenticate"] == "Session"
    assert "private" in response["Cache-Control"]
    assert "no-store" in response["Cache-Control"]
    assert "Cookie" in response["Vary"]
    if method == "get":
        assert response.json() == {"detail": "Inicie sesión para continuar."}
    else:
        assert response.content == b""


@pytest.mark.parametrize("method", ["get", "head"])
@pytest.mark.parametrize(
    "path",
    [
        "/insumos/",
        "/admin/",
        "/api/users/me/",
        "/api/web/session",
        "/api/web/session/extra/",
    ],
)
def test_admindocs_behavior_outside_exact_session_head_is_unchanged(method, path):
    from config.middlewares.admindocs import WebSessionXViewMiddleware

    request = getattr(RequestFactory(), method)(path)
    request.user = AnonymousUser()

    def view(_request):
        return HttpResponse("synthetic")

    original = XViewMiddleware(view).process_view(request, view, (), {})
    candidate = WebSessionXViewMiddleware(view).process_view(request, view, (), {})

    if original is None:
        assert candidate is None
    else:
        assert candidate.status_code == original.status_code
        assert dict(candidate.headers) == dict(original.headers)
        assert candidate.content == original.content


def test_ready_session_returns_minimal_private_context_without_db_writes(web_user):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(web_user)

    with CaptureQueriesContext(connection) as queries:
        response = client.get("/api/web/session/")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "user",
        "access",
        "navigation",
        "capabilities",
        "footer_version_label",
    }
    assert payload["user"] == {
        "username": "web_context",
        "display_name": "Usuario Sintético",
        "avatar_initial": "W",
        "role_label": "Pruebas",
    }
    assert payload["access"] == {"state": "ready", "required_action_url": None}
    assert payload["capabilities"] == {
        "insumos": {"can_view": True, "show_management": True, "show_categories": False}
    }
    assert [node["id"] for node in payload["navigation"]] == [
        "inicio",
        "legajos",
        "configuracion-comedores",
        "comunicados",
        "mi_cuenta",
    ]
    assert isinstance(payload["footer_version_label"], str)
    assert payload["footer_version_label"]
    assert "csrftoken" in response.cookies
    assert not any(
        row["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        for row in queries
    )


@pytest.mark.parametrize(
    "access,password,confirmation,state,url",
    [
        (False, True, True, "web_access_denied", None),
        (True, True, True, "password_change_required", "/password/first-change/"),
        (True, False, True, "profile_confirmation_required", "/mi-cuenta/confirmar/"),
        (True, False, False, "mandatory_survey_required", "/inicio/"),
    ],
)
def test_unmet_controls_hide_menu_and_all_business_capabilities(
    web_user, monkeypatch, access, password, confirmation, state, url
):
    profile = web_user.profile
    profile.acceso_web = access
    profile.must_change_password = password
    profile.needs_profile_confirmation = confirmation
    profile.save()
    monkeypatch.setattr(
        "usuarios.web_session.get_rondas_pendientes_para_request",
        lambda _request: [
            SimpleNamespace(encuesta=SimpleNamespace(es_obligatoria=True))
        ],
    )

    def unexpected_menu(_request):
        pytest.fail("Pending controls must not materialize business navigation.")

    monkeypatch.setattr("usuarios.web_context.build_web_navigation", unexpected_menu)
    client = APIClient()
    client.force_login(web_user)

    response = client.get("/api/web/session/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["access"] == {"state": state, "required_action_url": url}
    assert payload["navigation"] == []
    assert payload["capabilities"] == {
        "insumos": {
            "can_view": False,
            "show_management": False,
            "show_categories": False,
        }
    }
    assert (payload["user"] is None) is (state == "web_access_denied")
    profile.refresh_from_db()
    assert (
        profile.acceso_web,
        profile.must_change_password,
        profile.needs_profile_confirmation,
    ) == (access, password, confirmation)


def test_missing_profile_is_not_created_by_context_get(web_user):
    client = APIClient()
    client.force_login(web_user)
    Profile.objects.filter(user=web_user).delete()

    response = client.get("/api/web/session/")

    assert response.status_code == 200
    assert response.json()["access"]["state"] == "web_access_denied"
    assert response.json()["user"] is None
    assert not Profile.objects.filter(user=web_user).exists()


@pytest.mark.parametrize("staff", [False, True])
@pytest.mark.parametrize("address", ["127.0.0.1", "203.0.113.42"])
def test_authenticated_head_reaches_context_even_for_staff_or_internal_ip(
    web_user, staff, address
):
    web_user.is_staff = staff
    web_user.save()
    client = APIClient()
    client.force_login(web_user)

    response = client.head("/api/web/session/", REMOTE_ADDR=address)

    assert response.status_code == 200
    assert response.content == b""
    assert "X-View" not in response
    assert "no-store" in response["Cache-Control"]
    assert "csrftoken" in response.cookies


@pytest.mark.parametrize("method", ["get", "head"])
def test_token_without_cookie_cannot_authenticate_web_context(web_user, method):
    token = Token.objects.create(user=web_user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    response = getattr(client, method)("/api/web/session/")

    assert response.status_code == 401
    assert Token.objects.filter(pk=token.pk, user=web_user).exists()


def test_cookie_identity_wins_over_another_users_token(web_user):
    other = User.objects.create_user(username="other_synthetic")
    token = Token.objects.create(user=other)
    client = APIClient()
    client.force_login(web_user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    response = client.get("/api/web/session/")

    assert response.status_code == 200
    assert response.json()["user"]["username"] == "web_context"
    assert Token.objects.filter(pk=token.pk, user=other).exists()


def test_add_without_view_remains_visible_but_does_not_grant_view(web_user):
    web_user.user_permissions.remove(
        Permission.objects.get(
            content_type__app_label="insumos", codename="view_insumo"
        )
    )
    client = APIClient()
    client.force_login(web_user)

    response = client.get("/api/web/session/")

    assert response.json()["capabilities"]["insumos"] == {
        "can_view": False,
        "show_management": True,
        "show_categories": False,
    }


def test_dependency_failure_never_returns_ready_context(web_user, monkeypatch):
    def unavailable(_request):
        raise RuntimeError("Synthetic navigation unavailable")

    monkeypatch.setattr("usuarios.web_context.build_web_navigation", unavailable)
    client = APIClient()
    client.force_login(web_user)

    with pytest.raises(RuntimeError, match="Synthetic navigation unavailable"):
        client.get("/api/web/session/")


def test_inactive_session_is_rejected(web_user):
    client = APIClient()
    client.force_login(web_user)
    User.objects.filter(pk=web_user.pk).update(is_active=False)

    assert client.get("/api/web/session/").status_code == 401


def test_context_does_not_share_the_previous_users_identity(web_user):
    client = APIClient()
    client.force_login(web_user)
    assert client.get("/api/web/session/").json()["user"]["username"] == "web_context"
    other = User.objects.create_user(username="second_synthetic")
    profile = other.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    client.force_login(other)

    payload = client.get("/api/web/session/").json()

    assert payload["user"] == {
        "username": "second_synthetic",
        "display_name": "second_synthetic",
        "avatar_initial": "S",
        "role_label": "-",
    }
    assert payload["capabilities"]["insumos"] == {
        "can_view": False,
        "show_management": False,
        "show_categories": False,
    }


def test_unsupported_methods_do_not_mutate_even_with_valid_csrf(web_user):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(web_user)
    client.get("/api/web/session/")
    csrf = client.cookies["csrftoken"].value
    snapshot = Profile.objects.filter(user=web_user).values().get()

    for method in ("post", "put", "patch", "delete"):
        response = getattr(client, method)(
            "/api/web/session/", {}, format="json", HTTP_X_CSRFTOKEN=csrf
        )
        assert response.status_code == 405
        assert "no-store" in response["Cache-Control"]
    assert Profile.objects.filter(user=web_user).values().get() == snapshot


def test_actual_schema_describes_cookie_identity_and_private_output():
    from django.urls import include, path
    from drf_spectacular.generators import SchemaGenerator

    schema = SchemaGenerator(
        patterns=[path("api/web/", include("usuarios.web_api_urls"))]
    ).get_schema(request=None, public=True)

    operation = schema["paths"]["/api/web/session/"]["get"]
    assert operation["security"] == [{"cookieAuth": []}]
    assert schema["components"]["securitySchemes"]["cookieAuth"]["in"] == "cookie"
    assert {"200", "401"} <= set(operation["responses"])
    assert set(schema["components"]["schemas"]["WebUser"]["properties"]) == {
        "username",
        "display_name",
        "avatar_initial",
        "role_label",
    }
    assert schema["components"]["schemas"]["WebNavigationNode"]["properties"][
        "children"
    ]["items"] == {"$ref": "#/components/schemas/WebNavigationNode"}
