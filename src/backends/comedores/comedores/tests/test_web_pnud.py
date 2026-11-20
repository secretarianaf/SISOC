"""Web API (G1 v1) of the global PNUD activity catalog: ``/api/web/comedores/actividades-pnud/``.

Every endpoint runs the native ``views.actividades_pnud`` view and its
permission mixin. Runtime tests switch to ``SISOC_BACKEND="comedores"``.
"""

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings
from django.utils import timezone

from core import web_gate
from pwa.models import CatalogoActividadPWA

ROOT = "/api/web/comedores/actividades-pnud/"
LISTA = "/comedores/configuracion/actividades-pnud/"

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _permiso(code):
    app, codename = code.split(".")
    encontrado = Permission.objects.filter(
        content_type__app_label=app, codename=codename
    ).first()
    if encontrado:
        return encontrado
    return Permission.objects.create(
        content_type=ContentType.objects.get_for_model(get_user_model()),
        codename=codename,
        name=codename,
    )


def _usuario(nombre, *codes):
    usuario = _ready(get_user_model().objects.create_user(nombre))
    for code in codes:
        usuario.user_permissions.add(_permiso(code))
    return get_user_model().objects.get(pk=usuario.pk)


def _cliente(usuario):
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="gestor")
def gestor_fixture():
    return _usuario("pnud_gestion", "pwa.manage_catalogoactividadpwa")


@pytest.fixture(name="web")
def web_fixture(gestor):
    return _cliente(gestor)


@pytest.fixture(name="catalogo")
def catalogo_fixture():
    CatalogoActividadPWA.objects.all().delete()
    return [
        CatalogoActividadPWA.objects.create(categoria=c, actividad=a, activo=v)
        for c, a, v in (
            ("Deportes", "Futbol", True),
            ("Cultura", "Teatro", True),
            ("Cultura", "Murga", False),
            ("Deportes", "Ajedrez", True),
        )
    ]


def _nombres(data):
    return [(a["categoria"], a["actividad"]) for a in data["results"]]


# --- List -------------------------------------------------------------------


def test_list_defaults_to_active_in_native_order(web, catalogo):
    data = web.get(ROOT).json()

    assert _nombres(data) == [
        ("Cultura", "Teatro"),
        ("Deportes", "Ajedrez"),
        ("Deportes", "Futbol"),
    ]
    assert data["estado"] == "activa"
    assert data["q"] == ""
    assert data["can_manage"] is True
    assert data["results"][0] == {
        "id": catalogo[1].pk,
        "categoria": "Cultura",
        "actividad": "Teatro",
        "activo": True,
    }
    nativo = web.get(LISTA).context["actividades"]
    assert [a["id"] for a in data["results"]] == [a.pk for a in nativo]


def test_list_filters_match_the_native_view(web, catalogo):
    casos = [
        {"estado": "inactiva"},
        {"estado": "todas", "q": "cult"},
        {"estado": "otro"},
        {"q": "  fut  "},
    ]
    for params in casos:
        api = [a["id"] for a in web.get(ROOT, params).json()["results"]]
        nativo = [a.pk for a in web.get(LISTA, params).context["actividades"]]
        assert api == nativo, params
    data = web.get(ROOT, {"estado": "todas", "q": " Cultura "}).json()
    assert (data["estado"], data["q"]) == ("todas", "Cultura")
    assert data["page"]["query_without_page"] == "estado=todas&q=%20Cultura%20&"


def test_list_pages_of_fifty_and_invalid_page_is_404(web, catalogo):
    for n in range(50):
        CatalogoActividadPWA.objects.create(categoria="Z", actividad=f"A{n:02d}")

    primera = web.get(ROOT).json()
    segunda = web.get(ROOT, {"page": "2"}).json()

    assert len(primera["results"]) == 50
    assert len(segunda["results"]) == 3
    assert primera["page"]["count"] == 53
    assert web.get(ROOT, {"page": "9"}).status_code == 404


def test_viewer_reads_without_manage_actions(catalogo):
    data = (
        _cliente(_usuario("pnud_ver", "pwa.view_catalogoactividadpwa")).get(ROOT).json()
    )

    assert data["can_manage"] is False
    assert len(data["results"]) == 3


# --- Form -------------------------------------------------------------------


def test_create_form_offers_distinct_categories(web, catalogo):
    data = web.get(ROOT + "crear/").json()

    assert data["editar"] is False
    assert data["values"] == {
        "categoria": "",
        "categoria_modo": "existente",
        "categoria_existente": "",
        "categoria_nueva": "",
        "actividad": "",
        "activo": True,
    }
    assert data["categorias"] == [
        {"value": "", "label": "Selecciona una categoria"},
        {"value": "Cultura", "label": "Cultura"},
        {"value": "Deportes", "label": "Deportes"},
    ]
    assert data["actividad_max_length"] == 180
    assert data["list_url"] == LISTA


def test_create_with_new_category_strips_values(web, catalogo):
    respuesta = web.post(
        ROOT + "crear/",
        {
            "categoria_modo": "nueva",
            "categoria_nueva": "  Salud  ",
            "categoria_existente": "",
            "actividad": "  Charla  ",
            "activo": "on",
        },
    )

    assert respuesta.json() == {"ok": True, "redirect": LISTA}
    creada = CatalogoActividadPWA.objects.get(actividad="Charla")
    assert (creada.categoria, creada.activo) == ("Salud", True)
    assert web.get(ROOT).json()["messages"] == [
        {"message": "Actividad PNUD creada correctamente.", "level": "success"}
    ]


def test_create_with_existing_category_and_inactive(web, catalogo):
    web.post(
        ROOT + "crear/",
        {
            "categoria_modo": "existente",
            "categoria_existente": "Cultura",
            "actividad": "Coro",
        },
    )

    creada = CatalogoActividadPWA.objects.get(actividad="Coro")
    assert (creada.categoria, creada.activo) == ("Cultura", False)


def test_invalid_form_returns_the_native_errors(web, catalogo):
    datos = {"categoria_modo": "nueva", "categoria_nueva": " ", "actividad": "  "}

    respuesta = web.post(ROOT + "crear/", datos)

    assert respuesta.status_code == 400
    data = respuesta.json()
    nativo = web.post(LISTA + "crear/", datos).context["form"].errors
    assert data["errors"] == nativo.get_json_data()
    assert data["errors"]["actividad"][0]["message"] == "Este campo es requerido."
    assert data["values"]["categoria_modo"] == "nueva"
    sin_categoria = web.post(ROOT + "crear/", {"actividad": "X"}).json()
    assert sin_categoria["errors"]["categoria_existente"][0]["message"] == (
        "La categoria es obligatoria."
    )
    assert CatalogoActividadPWA.objects.count() == 4


def test_edit_shows_the_current_category_and_saves(web, catalogo):
    murga = catalogo[2]

    data = web.get(f"{ROOT}{murga.pk}/editar/").json()

    assert data["editar"] is True
    assert data["values"]["categoria_existente"] == "Cultura"
    assert data["values"]["categoria"] == "Cultura"
    assert data["values"]["activo"] is False
    respuesta = web.post(
        f"{ROOT}{murga.pk}/editar/",
        {
            "categoria_modo": "existente",
            "categoria_existente": "Deportes",
            "actividad": "Murga",
            "activo": "on",
        },
    )
    assert respuesta.json() == {"ok": True, "redirect": LISTA}
    murga.refresh_from_db()
    assert (murga.categoria, murga.activo) == ("Deportes", True)
    assert web.get(ROOT).json()["messages"][0]["message"] == (
        "Actividad PNUD actualizada correctamente."
    )
    assert web.get(f"{ROOT}999999/editar/").status_code == 404


# --- Deactivation -----------------------------------------------------------


def test_deactivation_marks_inactive_and_keeps_the_row(web, catalogo):
    futbol = catalogo[0]
    antes = futbol.fecha_actualizacion

    assert web.get(f"{ROOT}{futbol.pk}/baja/").json() == {
        "categoria": "Deportes",
        "actividad": "Futbol",
        "cancel_url": LISTA,
    }
    respuesta = web.post(f"{ROOT}{futbol.pk}/baja/")

    assert respuesta.json() == {"ok": True, "redirect": LISTA}
    futbol.refresh_from_db()
    assert futbol.activo is False
    assert futbol.fecha_actualizacion > antes
    assert futbol.fecha_actualizacion <= timezone.now()
    assert web.get(ROOT).json()["messages"] == [
        {"message": "Actividad PNUD dada de baja correctamente.", "level": "success"}
    ]
    web.post(f"{ROOT}{futbol.pk}/baja/")
    assert web.get(ROOT).json()["messages"] == [
        {"message": "La actividad PNUD ya se encontraba inactiva.", "level": "info"}
    ]
    assert CatalogoActividadPWA.objects.count() == 4
    assert web.post(f"{ROOT}999999/baja/").status_code == 404


# --- Access -----------------------------------------------------------------


def test_access_matches_the_native_mixin(catalogo):
    pk = catalogo[0].pk
    lectura = [ROOT]
    escritura = [ROOT + "crear/", f"{ROOT}{pk}/editar/", f"{ROOT}{pk}/baja/"]
    casos = {
        "admin": (_usuario("pnud_admin", "auth.role_admin"), True, True),
        "manage": (
            _usuario("pnud_manage", "pwa.manage_catalogoactividadpwa"),
            True,
            True,
        ),
        "view": (_usuario("pnud_view", "pwa.view_catalogoactividadpwa"), True, False),
        "none": (_usuario("pnud_none"), False, False),
    }
    for nombre, (usuario, lee, escribe) in casos.items():
        client = _cliente(usuario)
        for url in lectura:
            assert (client.get(url).status_code == 200) is lee, (nombre, url)
        for url in escritura:
            assert (client.get(url).status_code == 200) is escribe, (nombre, url)
        assert (client.get(LISTA).status_code == 200) is lee, nombre
    viewer = _cliente(casos["view"][0])
    assert viewer.post(f"{ROOT}{pk}/baja/").status_code == 403
    assert CatalogoActividadPWA.objects.get(pk=pk).activo is True


def test_anonymous_gets_401_and_reads_only_answer_get(client, web):
    assert client.get(ROOT).status_code == 401
    assert web.post(ROOT).status_code == 405


def test_admindocs_head_does_not_bypass_the_web_api(client, catalogo):
    client.force_login(
        _ready(get_user_model().objects.create_user("st", is_staff=True))
    )

    for url in (ROOT, ROOT + "crear/", f"{ROOT}{catalogo[0].pk}/baja/"):
        respuesta = client.head(url)
        assert respuesta.status_code == 403, url
        assert "X-View" not in respuesta


def test_writes_require_the_csrf_token(gestor, catalogo):
    client = Client(enforce_csrf_checks=True)
    client.force_login(gestor)

    assert client.post(f"{ROOT}{catalogo[0].pk}/baja/").status_code == 403
    assert CatalogoActividadPWA.objects.get(pk=catalogo[0].pk).activo is True


# --- Split runtime ----------------------------------------------------------


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="comedores",
        ROOT_URLCONF="comedores_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, *, target, method):
    return web_gate.sign(
        audience="comedores",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method=method,
        target=target,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_deactivates_only_with_a_signed_post(web, gestor, catalogo):
    target = f"{ROOT}{catalogo[0].pk}/baja/"

    sin_firma = web.post(target, RAW_URI=target)
    firmado = web.post(
        target,
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(gestor, web, target=target, method="POST"),
    )

    assert sin_firma.status_code == 403
    assert firmado.json() == {"ok": True, "redirect": LISTA}
    assert CatalogoActividadPWA.objects.get(pk=catalogo[0].pk).activo is False


@pytest.mark.usefixtures("runtime")
def test_runtime_still_applies_the_native_mixin(client, catalogo):
    viewer = _usuario("pnud_viewer_rt", "pwa.view_catalogoactividadpwa")
    client.force_login(viewer)
    target = ROOT + "crear/"

    respuesta = client.get(
        target,
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(viewer, client, target=target, method="GET"),
    )

    assert respuesta.status_code == 403
    assert respuesta.json() != {"detail": web_gate.DETAIL_REJECTED}
