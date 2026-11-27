"""D01: session JSON transport of the dashboards and embedded boards over the native views."""

import re
import secrets
from urllib.parse import urlencode

import pytest
from django.contrib.auth.models import Permission, User
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils.html import strip_tags

from core.models import Provincia
from dashboard.models import AudienciaTableros, ConcesionTablero, Dashboard, Tablero

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


EMBED_EJEMPLO = "https://example.com/tablero"


@pytest.mark.parametrize("ruta", ["dashboard_tablero", "dashboard_web_tablero"])
@pytest.mark.parametrize(
    "destino_nuevo",
    [
        {"ruta_interna": "/destino-sin-concesion/"},
        {"url": "https://example.com/tablero-editado"},
    ],
    ids=["ruta-interna", "embed-editado"],
)
def test_respuesta_del_tablero_usa_la_ficha_autorizada(
    monkeypatch, ruta, destino_nuevo
):
    usuario, client = make_actor("viewer")
    tablero = Tablero.objects.create(nombre="Ejemplo", slug="embed", url=EMBED_EJEMPLO)
    ConcesionTablero.objects.create(tablero=tablero, usuario=usuario, tipo="nacional")
    autorizar = Tablero.usuario_puede_ver
    modificada = False

    def autorizar_y_editar(ficha, user, **kwargs):
        nonlocal modificada
        permitido = autorizar(ficha, user, **kwargs)
        if ficha.pk == tablero.pk and permitido and not modificada:
            Tablero.objects.filter(pk=ficha.pk).update(**destino_nuevo)
            modificada = True
        return permitido

    monkeypatch.setattr(Tablero, "usuario_puede_ver", autorizar_y_editar)
    url = reverse(ruta, args=[tablero.slug])
    respuesta = client.get(url)
    assert modificada
    assert respuesta.status_code == 200
    if ruta == "dashboard_web_tablero":
        assert respuesta.json()["embed_url"] == EMBED_EJEMPLO
    else:
        assert f'src="{EMBED_EJEMPLO}"' in respuesta.content.decode()

    siguiente = client.get(url)
    if "ruta_interna" in destino_nuevo:
        assert siguiente.status_code == 403
    elif ruta == "dashboard_web_tablero":
        assert siguiente.json()["embed_url"] == destino_nuevo["url"]
    else:
        assert f'src="{destino_nuevo["url"]}"' in siguiente.content.decode()


def comprobar_acceso_embed(client, tablero, estado, *, en_menu=False):
    url_html = reverse("dashboard_tablero", args=[tablero.slug])
    url_api = reverse("dashboard_web_tablero", args=[tablero.slug])
    html = client.get(url_html)
    api = client.get(url_api)
    assert html.status_code == estado
    assert api.status_code == estado
    if estado == 200:
        assert EMBED_EJEMPLO in html.content.decode()
        assert api.json()["embed_url"] == EMBED_EJEMPLO
    else:
        assert EMBED_EJEMPLO not in html.content.decode()
        assert EMBED_EJEMPLO not in api.content.decode()
        for url in (url_html, url_api):
            head = client.head(url)
            assert head.status_code == estado
            assert "X-View" not in head
    assert (
        f'href="{url_html}"'
        in client.get("/dashboard/centro-de-familia").content.decode()
    ) == en_menu


@pytest.mark.parametrize(
    "por_audiencia", [False, True], ids=["individual", "audiencia"]
)
def test_embed_nacional_por_tablero_se_revoca_en_html_api_y_menu(por_audiencia):
    usuario, client = make_actor("viewer")
    tablero = Tablero.objects.create(nombre="Ejemplo", slug="embed", url=EMBED_EJEMPLO)
    otro = Tablero.objects.create(nombre="Otro", slug="otro", url=EMBED_EJEMPLO)
    if por_audiencia:
        audiencia = AudienciaTableros.objects.create(nombre="Audiencia")
        membresia = audiencia.agregar_miembro(usuario)
        sujeto = {"audiencia": audiencia}
    else:
        sujeto = {"usuario": usuario}
    concesion = ConcesionTablero.objects.create(
        tablero=tablero, tipo="nacional", **sujeto
    )
    comprobar_acceso_embed(client, tablero, 200, en_menu=True)
    comprobar_acceso_embed(client, otro, 403)

    tablero.visible_menu = False
    tablero.save(update_fields=["visible_menu"])
    comprobar_acceso_embed(client, tablero, 200)
    tablero.activo = False
    tablero.save(update_fields=["activo"])
    comprobar_acceso_embed(client, tablero, 404)
    tablero.activo = tablero.visible_menu = True
    tablero.save(update_fields=["activo", "visible_menu"])

    if por_audiencia:
        membresia.delete()
    else:
        concesion.delete()
    comprobar_acceso_embed(client, tablero, 403)


@pytest.mark.parametrize("tipo", ["provincia", "cdi"])
def test_embed_activo_no_abre_con_alcance_territorial_solo(tipo):
    usuario, client = make_actor("viewer")
    tablero = Tablero.objects.create(nombre="Ejemplo", slug="embed", url=EMBED_EJEMPLO)
    territorio = (
        {"provincia": Provincia.objects.create(nombre="Salta")}
        if tipo == "provincia"
        else {"cdi_id": 42}
    )
    ConcesionTablero.objects.create(
        tablero=tablero, usuario=usuario, tipo=tipo, **territorio
    )
    comprobar_acceso_embed(client, tablero, 403)


def test_embed_conserva_permiso_legacy_al_revocar_la_concesion_nacional():
    usuario, client = make_actor("viewer", ["view_dashboard"])
    tablero = Tablero.objects.create(
        nombre="Ejemplo",
        slug="embed",
        url=EMBED_EJEMPLO,
        permisos=["dashboard.view_dashboard"],
    )
    concesion = ConcesionTablero.objects.create(
        tablero=tablero, usuario=usuario, tipo="nacional"
    )
    comprobar_acceso_embed(client, tablero, 200, en_menu=True)
    concesion.delete()
    comprobar_acceso_embed(client, tablero, 200, en_menu=True)


@pytest.mark.parametrize("ruta", ["/ruta-sin-politica/", ""])
def test_nacional_no_habilita_redirect_arbitrario_ni_ficha_sin_embed(ruta):
    usuario, client = make_actor("viewer")
    tablero = Tablero.objects.create(
        nombre="Ejemplo",
        slug="embed",
        url=EMBED_EJEMPLO if ruta else "",
        ruta_interna=ruta,
    )
    ConcesionTablero.objects.create(tablero=tablero, usuario=usuario, tipo="nacional")
    comprobar_acceso_embed(client, tablero, 403)


def test_sidebar_resuelve_concesiones_nacionales_en_lote_y_respeta_revocacion():
    usuario, client = make_actor("viewer")
    audiencia = AudienciaTableros.objects.create(nombre="Audiencia")
    membresia = audiencia.agregar_miembro(usuario)
    tableros = [
        Tablero.objects.create(
            nombre=f"Tablero {i}", slug=f"embed-{i}", url=EMBED_EJEMPLO
        )
        for i in range(12)
    ]
    for tablero in tableros[:2]:
        ConcesionTablero.objects.create(
            tablero=tablero, audiencia=audiencia, tipo="nacional"
        )
    individual = ConcesionTablero.objects.create(
        tablero=tableros[0], usuario=usuario, tipo="nacional"
    )
    enlaces = [f'href="{tablero.get_absolute_url()}"' for tablero in tableros]

    def comprobar_menu(concesiones_efectivas):
        with CaptureQueriesContext(connection) as consultas:
            sidebar = client.get("/dashboard/centro-de-familia").content.decode()
        assert [
            i for i, enlace in enumerate(enlaces) if enlace in sidebar
        ] == concesiones_efectivas
        assert (
            sum(
                "dashboard_concesiontablero" in consulta["sql"].lower()
                for consulta in consultas.captured_queries
            )
            == 1
        )

    comprobar_menu([0, 1])
    membresia.delete()
    comprobar_menu([0])
    individual.delete()
    comprobar_menu([])


# --- the dashboard ----------------------------------------------------------


def test_anonymous_is_401_and_head_does_not_leak_admindocs():
    assert Client().get(DASH).status_code == 401
    response = Client(REMOTE_ADDR="10.0.0.5").head(DASH)
    assert response.status_code == 401 and "X-View" not in response


@pytest.mark.parametrize(
    ("actor", "permisos", "estado"),
    [
        ("anonimo", (), 302),
        ("staff_sin_permiso", (), 200),
        ("staff_autorizado", ("view_dashboard",), 200),
    ],
)
def test_head_portada_html_pasa_por_la_vista_sin_publicar_metadata(
    actor, permisos, estado
):
    ruta = "/dashboard/centro-de-familia"
    make_board(slug="informe-centro-de-familia", url=EMBED_EJEMPLO)
    if actor == "anonimo":
        client = Client(REMOTE_ADDR="127.0.0.1")
    else:
        usuario, client = make_actor(actor, permisos)
        usuario.is_staff = True
        usuario.save(update_fields=["is_staff"])

    get = client.get(ruta)
    assert get.status_code == estado
    assert "X-View" not in get
    assert (EMBED_EJEMPLO in get.content.decode()) == bool(permisos)

    head = client.head(ruta)
    assert "X-View" not in head
    assert head.status_code == estado
    assert head.content == b""
    if estado == 302:
        assert head["Location"] == get["Location"]
    else:
        assert "no-store" in head["Cache-Control"]


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
        "embed_centro_de_familia": None,
        "embed_comedores": None,
        "messages": [],
    }
    assert "1234" not in client.get(DASH).content.decode()


@pytest.mark.parametrize("por_audiencia", [False, True])
def test_portada_autoriza_cada_embed_sin_otorgar_metricas(por_audiencia):
    seed_metrics()
    usuario, client = make_actor("portada_nacional")
    cdf = make_board(slug="informe-centro-de-familia", url=EMBED_EJEMPLO)
    otro = make_board(slug="informe-comedores", url="https://example.com/comedores")
    if por_audiencia:
        audiencia = AudienciaTableros.objects.create(nombre="Familias")
        audiencia.agregar_miembro(usuario)
        sujeto = {"audiencia": audiencia}
    else:
        sujeto = {"usuario": usuario}
    grant = ConcesionTablero.objects.create(tablero=cdf, tipo="nacional", **sujeto)
    ConcesionTablero.objects.create(
        tablero=otro,
        tipo="provincia",
        usuario=usuario,
        provincia=Provincia.objects.create(nombre="Salta"),
    )

    response = client.get(DASH)
    assert response.status_code == 200 and "no-store" in response["Cache-Control"]
    body = response.json()
    assert body["embed_centro_de_familia"] == EMBED_EJEMPLO
    assert body["embed_comedores"] is None
    assert body["metricas"] is None
    assert otro.url not in response.content.decode()
    head = client.head(DASH)
    assert head.status_code == 200 and "X-View" not in head
    pagina = client.get(reverse("dashboard"))
    assert "no-store" in pagina["Cache-Control"]
    html = pagina.content.decode()
    assert f'src="{EMBED_EJEMPLO}"' in html
    assert otro.url not in html
    assert "1234 Comedores Activos" not in re.sub(r"\s+", " ", strip_tags(html))
    for ruta in ("dashboard_tablero", "dashboard_web_tablero"):
        assert client.get(reverse(ruta, kwargs={"slug": cdf.slug})).status_code == 200
        assert client.get(reverse(ruta, kwargs={"slug": otro.slug})).status_code == 403

    grant.delete()
    assert client.get(DASH).json()["embed_centro_de_familia"] is None
    assert EMBED_EJEMPLO not in client.get(reverse("dashboard")).content.decode()


def test_portada_conserva_permiso_legacy_y_cierra_si_ficha_falta_o_esta_inactiva():
    seed_metrics()
    _, client = make_actor("portada_legacy", ["view_dashboard"])
    cdf = make_board(slug="informe-centro-de-familia", url=EMBED_EJEMPLO)
    comedores = make_board(
        slug="informe-comedores", url="https://example.com/comedores"
    )
    response = client.get(DASH).json()
    assert response["embed_centro_de_familia"] == cdf.url
    assert response["embed_comedores"] == comedores.url
    assert response["metricas"]["cantidad_comedores_activos"] == "1234"
    html = client.get(reverse("dashboard")).content.decode()
    assert f'src="{cdf.url}"' in html and f'src="{comedores.url}"' in html

    comedores.activo = False
    comedores.save(update_fields=["activo"])
    response = client.get(DASH).json()
    assert response["embed_centro_de_familia"] == cdf.url
    assert response["embed_comedores"] is None
    assert comedores.url not in client.get(reverse("dashboard")).content.decode()

    cdf.delete()
    assert client.get(DASH).json()["embed_centro_de_familia"] is None
    html = client.get(reverse("dashboard")).content.decode()
    assert "<iframe" not in html
    assert "1234 Comedores Activos" in re.sub(r"\s+", " ", strip_tags(html))


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
