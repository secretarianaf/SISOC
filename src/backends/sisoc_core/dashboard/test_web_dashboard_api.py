"""D01: session JSON transport of the dashboards and embedded boards over the native views."""

import re
import secrets
from urllib.parse import urlencode

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client
from django.utils.html import strip_tags

from dashboard.models import Dashboard, Tablero

pytestmark = pytest.mark.django_db
DASH = "/api/web/dashboard/centro-de-familia/"
FORM = "application/x-www-form-urlencoded"


def make_actor(username, codenames=()):
    secret = secrets.token_urlsafe(24)
    user = User.objects.create_user(username=username, password=secret)
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="dashboard", codename__in=list(codenames)
        )
    )
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.dni = f"{secrets.randbelow(10**7) + 10**7}"
    profile.save()
    client = Client(enforce_csrf_checks=True, REMOTE_ADDR="203.0.113.42")
    assert client.get("/api/web/login/").status_code == 200
    response = client.post(
        "/api/web/login/",
        urlencode({"username": username, "password": secret}),
        content_type=FORM,
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
    )
    assert response.status_code == 200
    return user, client


@pytest.fixture(autouse=True)
def remote_source(monkeypatch):
    """The Comedores refresh is a remote call: each test chooses its outcome."""
    state = {"ok": True}
    monkeypatch.setattr(
        "dashboard.views.actualizar_metricas_comedores", lambda request: state["ok"]
    )
    return state


def native_text(client, path):
    html = client.get(path).content.decode()
    return re.sub(r"\s+", " ", strip_tags(html)).strip()


def seed_metrics():
    for key, value in (
        ("cantidad_comedores_activos", 1234),
        ("cantidad_relevamientos_activos", 56),
        ("presupuesto_desayuno", 7000),
        ("presupuesto_merienda", 8000),
        ("presupuesto_comida", 9000),
    ):
        Dashboard.objects.create(llave=key, cantidad=value)


# --- the dashboard ----------------------------------------------------------


def test_anonymous_is_401_and_head_does_not_leak_admindocs():
    assert Client().get(DASH).status_code == 401
    response = Client(REMOTE_ADDR="10.0.0.5").head(DASH)
    assert response.status_code == 401 and "X-View" not in response


def test_viewer_gets_the_indicators_the_native_page_prints():
    seed_metrics()
    _, client = make_actor("ve_dashboard", ["view_dashboard"])
    response = client.get(DASH)
    assert response.status_code == 200 and "no-store" in response["Cache-Control"]
    body = response.json()
    assert body["can_view"] is True and body["metricas_desactualizadas"] is False
    assert body["metricas"] == {
        "cantidad_comedores_activos": "1234",
        "cantidad_relevamientos_activos": "56",
        "presupuesto_desayuno": "7000",
        "presupuesto_merienda": "8000",
        "presupuesto_comida": "9000",
    }
    text = native_text(client, "/dashboard/centro-de-familia")
    for fragment in (
        "1234 Comedores Activos",
        "56 Relevamientos Activos",
        "Presupuesto Merienda $8000",
    ):
        assert fragment in text


def test_user_without_the_permission_gets_no_numbers():
    seed_metrics()
    _, client = make_actor("sin_dashboard")
    body = client.get(DASH).json()
    assert body == {
        "can_view": False,
        "metricas_desactualizadas": False,
        "metricas_disponibles": True,
        "metricas": None,
        "messages": [],
    }
    assert "1234" not in client.get(DASH).content.decode()


def test_remote_failure_keeps_the_last_values_and_says_so(remote_source):
    seed_metrics()
    remote_source["ok"] = False
    _, client = make_actor("ve_dashboard_2", ["view_dashboard"])
    body = client.get(DASH).json()
    assert body["metricas_desactualizadas"] is True
    assert body["metricas_disponibles"] is True
    assert body["metricas"]["cantidad_comedores_activos"] == "1234"
    text = native_text(client, "/dashboard/centro-de-familia")
    assert "No se pudieron actualizar los indicadores de Comedores. Se muestran" in text


def test_remote_failure_without_data_is_not_zero(remote_source):
    remote_source["ok"] = False
    _, client = make_actor("ve_dashboard_3", ["view_dashboard"])
    body = client.get(DASH).json()
    assert body["metricas_disponibles"] is False
    assert set(body["metricas"].values()) == {"Sin información"}
    text = native_text(client, "/dashboard/centro-de-familia")
    assert "Todavía no hay información disponible." in text
    assert Dashboard.objects.count() == 0


def test_reading_writes_nothing_and_post_is_not_allowed():
    seed_metrics()
    _, client = make_actor("ve_dashboard_4", ["view_dashboard"])
    before = list(Dashboard.objects.order_by("pk").values_list("pk", "cantidad"))
    assert client.get(DASH).status_code == 200
    response = client.post(DASH, {}, HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
    assert response.status_code == 405
    assert before == list(
        Dashboard.objects.order_by("pk").values_list("pk", "cantidad")
    )


# --- embedded boards -------------------------------------------------------------


def make_board(**fields):
    defaults = {
        "nombre": "Prueba",
        "slug": "prueba",
        "activo": True,
        "permisos": ["dashboard.view_dashboard"],
    }
    defaults.update(fields)
    return Tablero.objects.create(**defaults)


def test_board_projects_embed_and_construction_states():
    _, client = make_actor("ve_tablero", ["view_dashboard"])
    make_board(url="https://app.powerbi.com/view?r=abc")
    body = client.get("/api/web/dashboard/prueba/").json()
    assert body["titulo"] == "Tablero Prueba" and body["nombre"] == "Prueba"
    assert body["url"] == body["embed_url"] == "https://app.powerbi.com/view?r=abc"
    assert body["looker_compartible"] is False and body["mensaje_construccion"] == ""
    make_board(
        slug="looker",
        nombre="Looker",
        url=(
            "https://lookerstudio.google.com/u/0/reporting/"
            "7feb7647-eadb-4fd8-910d-11a794227234"
        ),
    )
    looker = client.get("/api/web/dashboard/looker/").json()
    assert looker["looker_compartible"] is True
    assert "/embed/reporting/" in looker["embed_url"]
    make_board(slug="obra", nombre="Obra")
    obra = client.get("/api/web/dashboard/obra/").json()
    assert obra["url"] == ""
    assert obra["mensaje_construccion"] == (
        "El tablero de Obra estará disponible próximamente."
    )
    assert "Tablero en confección" in native_text(client, "/dashboard/obra/")


def test_board_access_follows_the_native_view():
    make_board()
    _, nobody = make_actor("sin_tablero")
    assert nobody.get("/api/web/dashboard/prueba/").status_code == 403
    _, viewer = make_actor("ve_tablero_2", ["view_dashboard"])
    assert viewer.get("/api/web/dashboard/prueba/").status_code == 200
    assert viewer.get("/api/web/dashboard/inexistente/").status_code == 404
    make_board(slug="apagado", nombre="Apagado", activo=False)
    assert viewer.get("/api/web/dashboard/apagado/").status_code == 404
    assert Client().get("/api/web/dashboard/prueba/").status_code == 401


def test_board_with_its_own_screen_answers_the_native_redirect():
    make_board(slug="propio", nombre="Propio", ruta_interna="/celiaquia/tablero/")
    _, viewer = make_actor("ve_tablero_3", ["view_dashboard"])
    body = viewer.get("/api/web/dashboard/propio/").json()
    assert body == {"redirect": "/celiaquia/tablero/"}
