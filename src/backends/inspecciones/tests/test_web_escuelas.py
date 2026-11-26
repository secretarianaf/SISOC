"""Web API (G1 v1) of the Escuelas tab (IN05): ``/api/web/inspecciones/escuelas/``.

The panel runs ``EscuelasView``; the form routes run ``EscuelaCrearView`` and
``EscuelaEditarView`` (modal with ``X-Requested-With``, or page). Monolith tests
use ``config.settings_all``; runtime tests switch to the inspecciones URLconf.
"""

import types

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from config.urls_all import urlpatterns as monolith_patterns
from core import web_gate
from inspecciones.models import Escuela
from inspecciones.web_preview import actas_preview_patterns

API = "/api/web/inspecciones/escuelas/"
NUEVA = API + "nueva/"
LOCALIDADES = "/api/web/inspecciones/localidades/"
XHR = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}
WRITES = ("INSERT", "UPDATE", "DELETE")

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


@pytest.fixture(name="gestor_web")
def gestor_web_fixture(gestor):
    gestor.first_name, gestor.last_name = "Gestora", "Panel"
    gestor.save()
    return _ready(gestor)


@pytest.fixture(name="web")
def web_fixture(gestor_web):
    client = Client()
    client.force_login(gestor_web)
    return client


def _datos(geografia, **cambios):
    return {
        "provincia": geografia["bsas"].pk,
        "localidad": geografia["san_justo"].pk,
        "cueanexo": "060123400",
        "nombre": "  EP   N° 12 ",
        "domicilio": "Av.  Perón 3245",
        "cp": "b1754 abc",
        "telefono": "011 4651-2233",
        "mail": "ep12@abc.gob.ar; otra@abc.gob.ar",
        **cambios,
    }


def _editar(escuela):
    return f"{API}{escuela.pk}/editar/"


def _toasts(web):
    return [m["message"] for m in web.get(API).json()["messages"]]


def _catalogo():
    return list(Escuela.objects.order_by("pk").values())


@pytest.fixture(name="escuelas")
def escuelas_fixture(geografia):
    vinculada = Escuela.objects.create(
        codigo="060123400",
        cue="060123400",
        nombre="EP 12",
        provincia=geografia["bsas"],
        localidad_vinculada=geografia["san_justo"],
        localidad="San Justo",
        distrito="La Matanza",
        cp="B1754ABC",
    )
    revisar = Escuela.objects.create(
        codigo="020000900",
        cue="020000900",
        nombre="Escuela a revisar",
        provincia=geografia["bsas"],
        localidad="San José",
        localidad_original="San Jose",
        mail="roto@",
        a_revisar=True,
        motivos_revision=["localidad_repetida", "mail_invalido"],
    )
    return vinculada, revisar


# --- Panel ---------------------------------------------------------------------


def test_panel_projects_the_native_tab(web, escuelas):
    vinculada, revisar = escuelas
    respuesta = web.get(API)

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    nativo = web.get(reverse("inspecciones_panel")).context
    assert data["layout"]["breadcrumb"] == [
        {"text": "Inicio", "url": reverse("inicio")},
        {"text": "Inspecciones escolares", "url": None},
    ]
    assert [tab["id"] for tab in data["tabs"]][-3:] == [
        "escuelas",
        "asignaciones",
        "actas",
    ]
    totales = nativo["totales_panel"]
    assert data["totales"]["escuelas"] == totales["escuelas"] == 2
    assert data["totales"]["escuelas_a_revisar"] == 1
    assert data["totales"]["jornada"] == totales["jornada"].strftime("%d/%m")
    assert [fila["id"] for fila in data["results"]] == [
        e.pk for e in nativo["escuelas"]
    ]
    filas = {fila["id"]: fila for fila in data["results"]}
    assert filas[vinculada.pk]["localidad"] == {
        "vinculada": True,
        "texto": "San Justo",
        "distrito": "La Matanza",
        "aviso": "",
    }
    assert filas[revisar.pk]["localidad"] == {
        "vinculada": False,
        "texto": "San Jose",
        "distrito": "",
        "aviso": "localidad repetida",
    }
    assert filas[revisar.pk]["mail"] == "roto@"
    assert filas[revisar.pk]["mail_invalido"] is True
    assert filas[revisar.pk]["cp"] == "—"
    assert filas[vinculada.pk]["form_url"] == _editar(vinculada)
    assert data["a_revisar"] == {"activo": False, "contador": 1, "url": "?a_revisar=1"}
    assert data["urls"] == {
        "nueva": NUEVA,
        "importar": reverse("inspecciones_importar_escuelas"),
    }
    assert data["editar_url"] is None
    assert data["filters"] == {"q": "", "provincia": "", "localidad": None}


def test_panel_filters_match_the_native_list(web, escuelas, geografia):
    vinculada, _ = escuelas
    bsas, san_justo = geografia["bsas"].pk, geografia["san_justo"].pk
    for params in (
        {"q": "revisar"},
        {"q": "060123"},
        {"provincia": bsas},
        {"provincia": bsas, "localidad": san_justo},
        {"localidad": san_justo},
        {"a_revisar": "1", "q": "Escuela"},
        {"provincia": "x"},
    ):
        data = web.get(API, params).json()
        nativo = web.get(reverse("inspecciones_panel"), params).context
        assert [f["id"] for f in data["results"]] == [
            e.pk for e in nativo["escuelas"]
        ], params
        assert data["a_revisar"]["contador"] == nativo["contador_a_revisar"], params
    data = web.get(API, {"provincia": bsas, "localidad": san_justo}).json()
    assert data["filters"]["localidad"] == {
        "id": san_justo,
        "text": "San Justo · La Matanza",
    }
    activo = web.get(API, {"a_revisar": "1", "q": "x"}).json()["a_revisar"]
    assert activo == {"activo": True, "contador": 1, "url": "?q=x"}
    inactivo = web.get(API, {"q": "x"}).json()["a_revisar"]
    assert inactivo["url"] == "?q=x&a_revisar=1"
    assert web.get(API, {"editar": vinculada.pk}).json()["editar_url"] == _editar(
        vinculada
    )


def test_panel_invalid_page_is_404_reads_never_write_and_only_get(web, escuelas):
    del escuelas
    assert web.get(API, {"page": "9"}).status_code == 404
    with CaptureQueriesContext(connection) as consultas:
        assert web.get(API).status_code == 200
        assert web.get(NUEVA).status_code == 200
    assert not [
        q["sql"] for q in consultas.captured_queries if q["sql"].startswith(WRITES)
    ]
    for metodo in ("post", "put", "patch", "delete"):
        assert getattr(web, metodo)(API).status_code == 405, metodo


def test_locality_search_matches_the_native_select2_endpoint(web, geografia):
    for params in (
        {"provincia": geografia["bsas"].pk, "q": ""},
        {"provincia": geografia["bsas"].pk, "q": "jos"},
        {"provincia": "x", "q": "jos"},
        {"q": "San"},
    ):
        native = web.get(reverse("inspecciones_ajax_localidades"), params).json()
        assert web.get(LOCALIDADES, params).json() == native, params
    assert web.post(LOCALIDADES).status_code == 405


# --- Form: data ----------------------------------------------------------------


def test_new_form_is_empty_and_edit_form_brings_the_school(web, escuelas, geografia):
    vinculada, revisar = escuelas
    nueva = web.get(NUEVA, **XHR).json()
    assert nueva["editar"] is False
    assert nueva["aviso"] is None
    assert {k: v["value"] for k, v in nueva["fields"].items()} == dict.fromkeys(
        nueva["fields"], ""
    )
    assert nueva["layout"]["breadcrumb"][-1] == {"text": "Nueva escuela", "url": None}
    assert nueva["options"]["provincias"][0] == {
        "id": geografia["bsas"].pk,
        "nombre": "Buenos Aires",
    }

    editar = web.get(_editar(vinculada), **XHR).json()
    assert editar["editar"] is True
    assert editar["fields"]["cueanexo"]["value"] == "060123400"
    assert editar["fields"]["provincia"]["value"] == str(geografia["bsas"].pk)
    assert editar["localidad_inicial"] == {
        "id": geografia["san_justo"].pk,
        "text": "San Justo · La Matanza",
    }
    aviso = web.get(_editar(revisar), **XHR).json()["aviso"]
    assert aviso == {
        "motivos": "; ".join(revisar.motivos_revision_display),
        "localidad_original": "San Jose",
    }
    assert web.get(f"{API}999999/editar/").status_code == 404


# --- Form: modal (X-Requested-With) ----------------------------------------------


def test_modal_create_saves_normalized_data_and_queues_the_message(web, geografia):
    respuesta = web.post(NUEVA, _datos(geografia), **XHR)

    assert respuesta.status_code == 200
    escuela = Escuela.objects.get()
    mensaje = f"Se agregó la escuela EP N° 12 ({escuela.cueanexo})."
    assert respuesta.json() == {"ok": True, "mensaje": mensaje, "otra": False}
    assert (escuela.cue, escuela.nombre, escuela.domicilio, escuela.cp) == (
        "060123400",
        "EP N° 12",
        "Av. Perón 3245",
        "B1754ABC",
    )
    assert escuela.localidad_vinculada == geografia["san_justo"]
    assert _toasts(web) == [mensaje]


def test_modal_create_and_another_does_not_queue_a_message(web, geografia):
    respuesta = web.post(NUEVA, {**_datos(geografia), "otra": "1"}, **XHR)

    assert respuesta.json()["otra"] is True
    assert Escuela.objects.count() == 1
    assert _toasts(web) == []


@pytest.mark.parametrize(
    "cambios, campo, error",
    [
        (
            {"cueanexo": "06012340"},
            "cueanexo",
            "El Cueanexo lleva exactamente 9 dígitos (con los ceros iniciales).",
        ),
        (
            {"mail": "ep12@abc.gob.ar; roto@"},
            "mail",
            "Ingresá un mail válido (si son varios, separalos con ; o ,).",
        ),
        ({"cp": "1754-B"}, "cp", "C. P. inválido: por ejemplo 1754 o B1754ABC."),
        ({"nombre": ""}, "nombre", "Este campo es requerido."),
        ({"localidad": "999999"}, "localidad", "Elegí una localidad de la lista."),
    ],
)
def test_modal_invalid_returns_the_native_errors_without_writing(
    web, geografia, cambios, campo, error
):
    datos = _datos(geografia, **cambios)
    respuesta = web.post(NUEVA, datos, **XHR)

    assert respuesta.status_code == 400
    data = respuesta.json()
    assert data["fields"][campo]["errors"] == [error]
    assert data["fields"]["nombre"]["value"] == datos["nombre"]
    assert Escuela.objects.count() == 0


def test_modal_rejects_a_foreign_locality_and_a_duplicate(web, geografia, escuelas):
    vinculada, _ = escuelas
    antes = _catalogo()
    ajena = web.post(NUEVA, _datos(geografia, localidad=geografia["ushuaia"].pk), **XHR)
    assert ajena.json()["fields"]["localidad"]["errors"] == [
        "La localidad no es de esa provincia."
    ]
    assert ajena.json()["localidad_inicial"] == {
        "id": geografia["ushuaia"].pk,
        "text": "Ushuaia · Ushuaia",
    }
    duplicada = web.post(NUEVA, _datos(geografia, cueanexo="060123400"), **XHR).json()
    assert duplicada["fields"]["cueanexo"]["errors"] == [
        "Ya existe: EP 12 (San Justo)."
    ]
    assert duplicada["duplicada_url"] == f"/inspecciones/?editar={vinculada.pk}"
    assert _catalogo() == antes


def test_modal_edit_saves_and_clears_the_review_mark(web, geografia, escuelas):
    _, revisar = escuelas
    respuesta = web.post(
        _editar(revisar), _datos(geografia, cueanexo="020000901", nombre="EP 9"), **XHR
    )

    mensaje = "Se guardaron los cambios de EP 9 (020000901)."
    assert respuesta.json() == {"ok": True, "mensaje": mensaje, "otra": False}
    revisar.refresh_from_db()
    assert (revisar.codigo, revisar.cue, revisar.a_revisar) == (
        "020000900",
        "020000901",
        False,
    )
    assert _toasts(web) == [mensaje]
    assert web.post(f"{API}999999/editar/", _datos(geografia), **XHR).status_code == 404


# --- Form: page --------------------------------------------------------------------


def test_page_create_redirects_like_the_native_page(web, geografia):
    normal = web.post(NUEVA, _datos(geografia))
    assert normal.json() == {"ok": True, "redirect": "/inspecciones/?q=060123400"}
    assert _toasts(web) == ["Se agregó la escuela EP N° 12 (060123400)."]

    otra = web.post(NUEVA, {**_datos(geografia, cueanexo="060123401"), "otra": "1"})
    assert otra.json() == {"ok": True, "redirect": "/inspecciones/escuelas/nueva/"}
    # The next page (the new form) shows the message; the modal never consumes it.
    assert web.get(NUEVA, **XHR).json()["messages"] == []
    assert [m["message"] for m in web.get(NUEVA).json()["messages"]] == [
        "Se agregó la escuela EP N° 12 (060123401)."
    ]

    invalida = web.post(NUEVA, _datos(geografia, cueanexo="1"))
    assert invalida.status_code == 400
    assert invalida.json()["fields"]["cueanexo"]["errors"]
    assert Escuela.objects.count() == 2


# --- Access -------------------------------------------------------------------------


def test_guards_csrf_and_rejections_do_not_write(
    gestor_web, client, inspector_a, geografia, escuelas
):
    vinculada, _ = escuelas
    antes = _catalogo()
    otro = get_user_model().objects.create_user("otro")
    for url in (API, NUEVA, _editar(vinculada), LOCALIDADES):
        anonimo = Client().get(url)
        assert anonimo.status_code == 401, url
        assert anonimo.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    for usuario in (inspector_a, otro):
        client.force_login(_ready(usuario))
        for url in (API, NUEVA, LOCALIDADES):
            assert client.get(url).status_code == 403, url
        assert client.post(NUEVA, _datos(geografia), **XHR).status_code == 403
        assert client.post(_editar(vinculada), _datos(geografia)).status_code == 403
    assert Client().post(NUEVA, _datos(geografia)).status_code == 401
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(gestor_web)
    assert csrf.post(NUEVA, _datos(geografia), **XHR).status_code == 403
    assert _catalogo() == antes


def test_superuser_and_coordination_keep_the_native_rule(client, coordinacion):
    superuser = _ready(
        get_user_model().objects.create_superuser("super_web", password="x")
    )
    for usuario in (superuser, _ready(coordinacion)):
        client.force_login(usuario)
        assert client.get(API).status_code == 200, usuario.username
        assert client.get(NUEVA).status_code == 200, usuario.username


def test_admindocs_head_does_not_bypass_the_api(client, escuelas):
    vinculada, _ = escuelas
    staff = _ready(get_user_model().objects.create_user("staff_web", is_staff=True))
    client.force_login(staff)

    for url in (API, NUEVA, _editar(vinculada), LOCALIDADES):
        respuesta = client.head(url)
        assert "X-View" not in respuesta, url
        assert respuesta.status_code in (403, 405), url


# --- Runtime ---------------------------------------------------------------------------


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="inspecciones",
        ROOT_URLCONF="inspecciones_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, *, target, method="GET"):
    return web_gate.sign(
        audience="inspecciones",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method=method,
        target=target,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_only_signed_requests(web, gestor_web, geografia):
    assert (
        web.get(
            API, RAW_URI=API, HTTP_X_SISOC_WEB_GATE=_signed(gestor_web, web, target=API)
        ).status_code
        == 200
    )
    sin_firma = web.post(NUEVA, _datos(geografia), RAW_URI=NUEVA, **XHR)
    assert sin_firma.status_code == 403
    assert sin_firma.json() == {"detail": web_gate.DETAIL_REJECTED}
    assert Escuela.objects.count() == 0
    firmado = web.post(
        NUEVA,
        _datos(geografia),
        RAW_URI=NUEVA,
        HTTP_X_SISOC_WEB_GATE=_signed(gestor_web, web, target=NUEVA, method="POST"),
        **XHR,
    )
    assert firmado.status_code == 200
    assert firmado.json()["ok"] is True
    assert Escuela.objects.count() == 1


# --- Local React entries -----------------------------------------------------------------


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(
        '<!doctype html><script src="/v2/sisoc/assets/app-1.js"></script>',
        encoding="utf-8",
    )
    module = types.ModuleType("escuelas_preview_test_urls")
    module.urlpatterns = actas_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_entries_serve_the_index_after_the_native_guards(
    web, escuelas, inspector_a, geografia
):
    vinculada, _ = escuelas
    paginas = (
        "/inspecciones/",
        "/inspecciones/escuelas/nueva/",
        f"/inspecciones/escuelas/{vinculada.pk}/editar/",
    )
    for pagina in paginas:
        respuesta = web.get(pagina)
        assert respuesta.status_code == 200, pagina
        assert b"/inspecciones/react/assets/app-1.js" in respuesta.content, pagina
        assert "no-store" in respuesta["Cache-Control"]
        assert "csrftoken" in respuesta.cookies
    assert web.get("/inspecciones/", {"page": "9"}).status_code == 404
    assert web.get("/inspecciones/escuelas/999999/editar/").status_code == 404
    client = Client()
    for pagina in paginas:
        assert client.get(pagina)["Location"].startswith("/login"), pagina
    client.force_login(inspector_a)
    for pagina in paginas:
        assert client.get(pagina).status_code == 403, pagina
    # The page-mode POST stays the native view.
    native = web.post(
        "/inspecciones/escuelas/nueva/", _datos(geografia, cueanexo="060123499")
    )
    assert native.status_code == 302
    assert native["Location"] == "/inspecciones/?q=060123499"


def test_production_urlconf_keeps_the_native_tab(web):
    respuesta = web.get(reverse("inspecciones_panel"))

    assert respuesta.status_code == 200
    assert "inspecciones/escuelas.html" in [t.name for t in respuesta.templates]
