"""Web API (G1 v1) of the Asignaciones tab (IN02): ``/api/web/inspecciones/asignaciones/``.

The list runs ``AsignacionesView``; the form route runs ``AsignacionCrearView``
(modal with ``X-Requested-With``, or page); removal runs
``AsignacionQuitarView.post``. Monolith tests use ``config.settings_all``;
runtime tests switch to the inspecciones URLconf.
"""

import types
import uuid
from datetime import date, timedelta

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from config.urls_all import urlpatterns as monolith_patterns
from core import web_gate
from inspecciones.models import Acta, AsignacionEscuela, Escuela, Inspeccion
from inspecciones.services.formato import hoy
from inspecciones.web_preview import actas_preview_patterns

API = "/api/web/inspecciones/asignaciones/"
NUEVA = API + "nueva/"
VERIFICAR = API + "verificar/"
ESCUELAS = "/api/web/inspecciones/escuelas/buscar/"
XHR = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}
WRITES = ("INSERT", "UPDATE", "DELETE")
YA_ASIGNADA = "Esa escuela ya está asignada a ese inspector en esa jornada."

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


def _quitar(asignacion):
    return f"{API}{asignacion.pk}/quitar/"


def _toasts(web):
    return [m["message"] for m in web.get(API).json()["messages"]]


def _estado():
    return list(AsignacionEscuela.all_objects.order_by("pk").values())


def _acta(inspector, escuela, secuencia, **campos):
    fecha = campos.pop("fecha", hoy())
    inspeccion = Inspeccion.objects.create(
        uuid=uuid.uuid4(),
        inspector=inspector,
        estado=Inspeccion.Estado.FINALIZADA,
        revision=1,
        escuela=escuela,
        fecha_visita=fecha,
        turno="tarde",
        resultado="cerrada",
    )
    numero = f"ACTA-2026-{secuencia:06d}"
    return Acta.objects.create(
        inspeccion=inspeccion,
        inspector=inspector,
        escuela=escuela,
        numero=numero,
        anio=2026,
        secuencia=secuencia,
        fecha_visita=fecha,
        turno="tarde",
        resultado="cerrada",
        formulario_version="v1",
        instantanea={"numero": numero, "payload": {}},
        instantanea_sha256="0" * 64,
        cerrada_at=timezone.now() - timedelta(minutes=secuencia),
        firma_tipo="excepcion",
        **campos,
    )


@pytest.fixture(name="jornada")
def jornada_fixture(geografia, escuela, inspector_a, inspector_b, coordinacion):
    """Today: A has two schools (one with an acta), B one; yesterday: A one."""
    otra = Escuela.objects.create(
        codigo="060999900",
        cue="060999900",
        nombre="EP 99",
        provincia=geografia["bsas"],
        localidad="San Justo",
    )
    pendiente = AsignacionEscuela.objects.create(
        escuela=escuela, inspector=inspector_a, fecha=hoy()
    )
    con_acta = AsignacionEscuela.objects.create(
        escuela=otra, inspector=inspector_a, fecha=hoy()
    )
    acta = _acta(inspector_a, otra, 1)
    de_b = AsignacionEscuela.objects.create(
        escuela=escuela, inspector=inspector_b, fecha=hoy()
    )
    ayer = AsignacionEscuela.objects.create(
        escuela=otra, inspector=inspector_a, fecha=hoy() - timedelta(days=1)
    )
    return {
        "pendiente": pendiente,
        "con_acta": con_acta,
        "acta": acta,
        "de_b": de_b,
        "ayer": ayer,
        "otra": otra,
        "escuela": escuela,
    }


# --- List ------------------------------------------------------------------------


def test_list_projects_the_native_day(web, jornada):
    respuesta = web.get(API)

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    nativo = web.get(reverse("inspecciones_asignaciones")).context
    assert data["layout"]["breadcrumb"] == [
        {"text": "Inicio", "url": reverse("inicio")},
        {"text": "Inspecciones escolares", "url": reverse("inspecciones_panel")},
        {"text": "Asignaciones", "url": None},
    ]
    assert [tab["id"] for tab in data["tabs"]][-3:] == [
        "escuelas",
        "asignaciones",
        "actas",
    ]
    assert [fila["id"] for fila in data["results"]] == [
        f["asignacion"].pk for f in nativo["filas"]
    ]
    assert data["totales"] == {
        "total": 3,
        "pendiente": 2,
        "en_curso": 0,
        "finalizada": 1,
        "inspectores": 2,
    }
    assert data["filters"] == {
        "fecha": hoy().isoformat(),
        "inspector": None,
        "escuela": None,
        "provincia": "",
        "estado": "",
        "estado_acta": "",
    }
    assert data["day"] == {
        "es_hoy": True,
        "anterior": nativo["url_anterior"],
        "siguiente": nativo["url_siguiente"],
        "hoy": nativo["url_hoy"],
    }
    assert data["urls"] == {
        "nueva": f"{NUEVA}?fecha={hoy().isoformat()}",
        "importar": reverse("inspecciones_importar_asignaciones"),
    }
    assert data["options"]["estados"] == [
        {"value": "", "label": "Todos los estados"},
        {"value": "pendiente", "label": "Pendiente"},
        {"value": "en_curso", "label": "En curso"},
        {"value": "finalizada", "label": "Finalizada"},
    ]
    assert data["options"]["estados_acta"][0] == {
        "value": "",
        "label": "Todas las actas",
    }
    assert data["options"]["escuelas_url"] == ESCUELAS


def test_list_rows_carry_the_native_cells(web, jornada):
    filas = {f["id"]: f for f in web.get(API).json()["results"]}
    pendiente = filas[jornada["pendiente"].pk]
    con_acta = filas[jornada["con_acta"].pk]

    assert pendiente["inspector"] == {
        "nombre": "Inspector_A",
        "usuario": "inspector_a",
    }
    assert pendiente["iniciales"] == "I"
    assert pendiente["escuela"]["cueanexo"] == "060123400"
    assert pendiente["escuela"]["provincia"] == ""
    assert pendiente["estado"] == "pendiente"
    assert pendiente["actas"] == []
    assert pendiente["se_puede_quitar"] is True
    assert pendiente["quitar_url"] == _quitar(jornada["pendiente"])
    assert con_acta["estado_display"] == "Finalizada"
    assert con_acta["escuela"]["provincia"] == "Buenos Aires"
    assert con_acta["actas"] == [
        {
            "numero": jornada["acta"].numero,
            "url": f"/inspecciones/actas/{jornada['acta'].numero}/",
            "anulada": False,
            "prueba": False,
        }
    ]
    assert con_acta["se_puede_quitar"] is False


def test_list_filters_and_day_match_the_native_list(
    web, jornada, inspector_a, geografia
):
    ayer = (hoy() - timedelta(days=1)).isoformat()
    for params in (
        {"fecha": ayer},
        {"inspector": inspector_a.pk},
        {"escuela": jornada["otra"].pk},
        {"provincia": geografia["bsas"].pk},
        {"estado": "finalizada"},
        {"estado": "pendiente", "estado_acta": "validas"},
        {"estado_acta": "anuladas"},
        {"fecha": "no-es-fecha", "estado": "x"},
    ):
        data = web.get(API, params).json()
        nativo = web.get(reverse("inspecciones_asignaciones"), params).context
        assert [f["id"] for f in data["results"]] == [
            f["asignacion"].pk for f in nativo["filas"]
        ], params
        assert data["filters"]["fecha"] == nativo["fecha"].isoformat(), params
        assert data["day"]["anterior"] == nativo["url_anterior"], params
        assert data["day"]["siguiente"] == nativo["url_siguiente"], params


def test_day_totals_ignore_the_state_filters_while_rows_obey_them(web, jornada):
    data = web.get(API, {"estado": "finalizada"}).json()

    assert [f["id"] for f in data["results"]] == [jornada["con_acta"].pk]
    assert data["totales"]["total"] == 3
    assert data["totales"]["pendiente"] == 2
    assert data["page"]["count"] == 1
    vacio = web.get(API, {"estado": "en_curso"}).json()
    assert vacio["results"] == []
    assert vacio["totales"]["total"] == 3


def test_list_preloads_the_selected_inspector_and_school(web, jornada, inspector_a):
    data = web.get(
        API, {"inspector": inspector_a.pk, "escuela": jornada["otra"].pk}
    ).json()

    assert data["filters"]["inspector"] == {"id": inspector_a.pk, "text": "Inspector_A"}
    assert data["filters"]["escuela"]["id"] == jornada["otra"].pk
    assert data["filters"]["escuela"]["text"].startswith("EP 99")
    assert data["day"]["es_hoy"] is True
    assert (
        web.get(API, {"fecha": hoy() - timedelta(days=3)}).json()["day"]["es_hoy"]
        is False
    )


def test_list_unknown_page_is_the_last_one_reads_never_write_and_only_get(web, jornada):
    del jornada
    ultima = web.get(API, {"page": "9"})
    assert ultima.status_code == 200
    assert ultima.json()["page"]["number"] == 1
    with CaptureQueriesContext(connection) as consultas:
        assert web.get(API).status_code == 200
        assert web.get(NUEVA).status_code == 200
        assert web.get(VERIFICAR).status_code == 200
        assert web.get(ESCUELAS, {"q": "EP 9"}).status_code == 200
    assert not [
        q["sql"] for q in consultas.captured_queries if q["sql"].startswith(WRITES)
    ]
    for metodo in ("post", "put", "patch", "delete"):
        assert getattr(web, metodo)(API).status_code == 405, metodo
    assert web.get(API + "1/quitar/").status_code == 405
    for url in (VERIFICAR, ESCUELAS):
        assert web.post(url).status_code == 405, url


def test_school_search_and_notice_match_the_native_ajax(web, jornada, inspector_b):
    for params in ({"q": "EP 9"}, {"q": "EP"}, {"q": "060123"}):
        native = web.get(reverse("inspecciones_ajax_escuelas"), params).json()
        assert web.get(ESCUELAS, params).json() == native, params
    params = {
        "fecha": hoy().isoformat(),
        "escuela": jornada["escuela"].pk,
        "inspector": inspector_b.pk,
    }
    native = web.get(reverse("inspecciones_ajax_verificar_asignacion"), params).json()
    assert web.get(VERIFICAR, params).json() == native
    assert native["otras"] == ["Inspector_A"]
    assert web.get(VERIFICAR, {"fecha": "x"}).json() == {"otras": []}


# --- Form: data --------------------------------------------------------------------


def test_new_form_carries_the_requested_day_and_the_options(web):
    sin_fecha = web.get(NUEVA, **XHR).json()
    assert sin_fecha["fields"]["fecha"] == {"value": hoy().isoformat(), "errors": []}
    assert sin_fecha["fields"]["inspector"]["value"] == ""
    assert sin_fecha["inspector_inicial"] is None
    assert sin_fecha["escuela_inicial"] is None
    assert sin_fecha["layout"]["breadcrumb"][-1] == {
        "text": "Nueva asignación",
        "url": None,
    }
    assert sin_fecha["options"] == {
        "inspectores_url": "/api/web/inspecciones/inspectores/",
        "escuelas_url": ESCUELAS,
        "verificar_url": VERIFICAR,
    }
    con_fecha = web.get(NUEVA, {"fecha": "2026-03-04"}, **XHR).json()
    assert con_fecha["fields"]["fecha"]["value"] == "2026-03-04"
    assert web.get(NUEVA).json()["messages"] == []


# --- Form: modal (X-Requested-With) --------------------------------------------------


def _datos(escuela_obj, usuario, **cambios):
    return {
        "fecha": hoy().isoformat(),
        "inspector": usuario.pk,
        "escuela": escuela_obj.pk,
        **cambios,
    }


def test_modal_create_saves_and_queues_the_message(web, escuela, inspector_a):
    respuesta = web.post(NUEVA, _datos(escuela, inspector_a), **XHR)

    assert respuesta.status_code == 200
    mensaje = f"Se asignó {escuela.nombre} a Inspector_A para el {hoy():%d/%m/%Y}."
    assert respuesta.json() == {"ok": True, "mensaje": mensaje, "otra": False}
    asignacion = AsignacionEscuela.objects.get()
    assert (asignacion.escuela, asignacion.inspector, asignacion.fecha) == (
        escuela,
        inspector_a,
        hoy(),
    )
    assert asignacion.creada_por.username == "gestor"
    assert _toasts(web) == [mensaje]


def test_modal_create_and_another_keeps_the_day_without_a_message(
    web, escuela, inspector_a
):
    respuesta = web.post(NUEVA, {**_datos(escuela, inspector_a), "otra": "1"}, **XHR)

    assert respuesta.json()["otra"] is True
    assert AsignacionEscuela.objects.count() == 1
    assert _toasts(web) == []


def test_other_inspector_is_an_additional_visit_with_a_notice(
    web, jornada, inspector_b, escuela
):
    del jornada
    respuesta = web.post(
        NUEVA,
        _datos(escuela, inspector_b, fecha=(hoy() + timedelta(days=1)).isoformat()),
        **XHR,
    )
    assert respuesta.json()["otra"] is False
    assert "También la tiene asignada" not in respuesta.json()["mensaje"]
    AsignacionEscuela.objects.create(
        escuela=escuela,
        inspector_id=get_user_model().objects.get(username="inspector_a").pk,
        fecha=hoy() + timedelta(days=2),
    )
    aviso = web.post(
        NUEVA,
        _datos(escuela, inspector_b, fecha=(hoy() + timedelta(days=2)).isoformat()),
        **XHR,
    ).json()["mensaje"]
    assert aviso.endswith(" También la tiene asignada Inspector_A (otra visita).")


@pytest.mark.parametrize(
    "cambios, campo, error",
    [
        ({"fecha": ""}, "fecha", "Este campo es requerido."),
        ({"inspector": ""}, "inspector", "Este campo es requerido."),
        ({"escuela": ""}, "escuela", "Este campo es requerido."),
        ({"inspector": "999999"}, "inspector", "Elegí un inspector de la lista."),
        ({"escuela": "999999"}, "escuela", "Elegí una escuela de la lista."),
    ],
)
def test_modal_invalid_returns_the_native_errors_without_writing(
    web, escuela, inspector_a, cambios, campo, error
):
    respuesta = web.post(NUEVA, _datos(escuela, inspector_a, **cambios), **XHR)

    assert respuesta.status_code == 400
    data = respuesta.json()
    assert data["fields"][campo]["errors"] == [error]
    assert AsignacionEscuela.objects.count() == 0


def test_modal_invalid_keeps_the_values_and_the_chosen_options(
    web, escuela, inspector_a
):
    data = web.post(NUEVA, _datos(escuela, inspector_a, fecha=""), **XHR).json()

    assert data["fields"]["inspector"]["value"] == str(inspector_a.pk)
    assert data["inspector_inicial"] == {"id": inspector_a.pk, "text": "Inspector_A"}
    assert data["escuela_inicial"]["id"] == escuela.pk
    assert data["escuela_inicial"]["text"].startswith(escuela.nombre)


def test_a_coordination_user_is_not_an_inspector(web, escuela, coordinacion):
    respuesta = web.post(NUEVA, _datos(escuela, coordinacion), **XHR)

    assert respuesta.status_code == 400
    assert respuesta.json()["fields"]["inspector"]["errors"] == [
        "Elegí un inspector de la lista."
    ]
    assert AsignacionEscuela.objects.count() == 0


def test_duplicate_is_rejected_and_a_removed_one_is_restored(web, escuela, inspector_a):
    web.post(NUEVA, _datos(escuela, inspector_a), **XHR)
    duplicada = web.post(NUEVA, _datos(escuela, inspector_a), **XHR)
    assert duplicada.status_code == 400
    assert duplicada.json()["non_field_errors"] == [YA_ASIGNADA]
    assert AsignacionEscuela.objects.count() == 1

    asignacion = AsignacionEscuela.objects.get()
    assert web.post(_quitar(asignacion)).status_code == 200
    assert AsignacionEscuela.objects.count() == 0
    restaurada = web.post(NUEVA, _datos(escuela, inspector_a), **XHR)
    assert restaurada.status_code == 200
    assert AsignacionEscuela.all_objects.count() == 1
    assert AsignacionEscuela.objects.get().pk == asignacion.pk
    assert AsignacionEscuela.objects.get().deleted_at is None


# --- Form: page ------------------------------------------------------------------------


def test_page_create_redirects_like_the_native_page(web, escuela, inspector_a):
    normal = web.post(NUEVA, _datos(escuela, inspector_a, fecha="2026-03-04"))
    assert normal.json() == {
        "ok": True,
        "redirect": "/inspecciones/asignaciones/?fecha=2026-03-04",
    }
    mensaje = f"Se asignó {escuela.nombre} a Inspector_A para el 04/03/2026."
    assert _toasts(web) == [mensaje]

    otra = web.post(
        NUEVA, {**_datos(escuela, inspector_a, fecha="2026-03-05"), "otra": "1"}
    )
    assert otra.json() == {
        "ok": True,
        "redirect": "/inspecciones/asignaciones/nueva/?fecha=2026-03-05",
    }
    # The next page (the new form) shows the message; the modal never consumes it.
    assert web.get(NUEVA, **XHR).json()["messages"] == []
    assert [m["message"] for m in web.get(NUEVA).json()["messages"]] == [
        f"Se asignó {escuela.nombre} a Inspector_A para el 05/03/2026."
    ]

    invalida = web.post(NUEVA, _datos(escuela, inspector_a, fecha=""))
    assert invalida.status_code == 400
    assert invalida.json()["fields"]["fecha"]["errors"]
    assert AsignacionEscuela.objects.count() == 2


# --- Removal ---------------------------------------------------------------------------


def test_remove_soft_deletes_and_returns_to_the_day(web, jornada):
    asignacion = jornada["pendiente"]
    respuesta = web.post(_quitar(asignacion))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/inspecciones/asignaciones/?fecha={hoy().isoformat()}",
    }
    asignacion = AsignacionEscuela.all_objects.get(pk=asignacion.pk)
    assert asignacion.deleted_at is not None
    mensaje = f"Se quitó la asignación de {jornada['escuela'].nombre} a Inspector_A."
    assert _toasts(web) == [mensaje]
    assert web.get(API).json()["totales"]["total"] == 2


def test_remove_with_an_acta_is_rejected_with_the_native_message(web, jornada):
    asignacion = jornada["con_acta"]
    antes = _estado()
    respuesta = web.post(_quitar(asignacion))

    assert respuesta.json()["ok"] is True
    assert _estado() == antes
    assert _toasts(web) == [
        "No se puede quitar: la visita ya tiene un acta para esa jornada."
    ]
    # A cancelled acta is still evidence of the visit.
    jornada["acta"].estado = Acta.Estado.ANULADA
    jornada["acta"].save(update_fields=["estado"])
    web.post(_quitar(asignacion))
    assert _estado() == antes


def test_remove_missing_assignment_is_404_and_a_removed_one_too(web, jornada):
    assert web.post(f"{API}999999/quitar/").status_code == 404
    asignacion = jornada["pendiente"]
    web.post(_quitar(asignacion))
    assert web.post(_quitar(asignacion)).status_code == 404


def test_remove_uses_the_assignment_day_for_the_return(web, jornada):
    respuesta = web.post(_quitar(jornada["ayer"]))

    ayer = (hoy() - timedelta(days=1)).isoformat()
    assert respuesta.json()["redirect"] == f"/inspecciones/asignaciones/?fecha={ayer}"


# --- Access ----------------------------------------------------------------------------


def test_guards_csrf_and_rejections_do_not_write(
    gestor_web, client, inspector_a, escuela, jornada
):
    antes = _estado()
    otro = get_user_model().objects.create_user("otro")
    quitar = _quitar(jornada["pendiente"])
    for url in (API, NUEVA, VERIFICAR, ESCUELAS):
        anonimo = Client().get(url)
        assert anonimo.status_code == 401, url
        assert anonimo.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert Client().post(quitar).status_code == 401
    for usuario in (inspector_a, otro):
        client.force_login(_ready(usuario))
        for url in (API, NUEVA, VERIFICAR, ESCUELAS):
            assert client.get(url).status_code == 403, url
        assert (
            client.post(NUEVA, _datos(escuela, inspector_a), **XHR).status_code == 403
        )
        assert client.post(quitar).status_code == 403
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(gestor_web)
    assert csrf.post(NUEVA, _datos(escuela, inspector_a), **XHR).status_code == 403
    assert csrf.post(quitar).status_code == 403
    assert _estado() == antes


def test_superuser_and_coordination_keep_the_native_rule(client, coordinacion):
    superuser = _ready(
        get_user_model().objects.create_superuser("super_web", password="x")
    )
    for usuario in (superuser, _ready(coordinacion)):
        client.force_login(usuario)
        assert client.get(API).status_code == 200, usuario.username
        assert client.get(NUEVA).status_code == 200, usuario.username


def test_admindocs_head_does_not_bypass_the_api(client, jornada):
    staff = _ready(get_user_model().objects.create_user("staff_web", is_staff=True))
    client.force_login(staff)

    for url in (API, NUEVA, VERIFICAR, ESCUELAS, _quitar(jornada["pendiente"])):
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
def test_runtime_serves_only_signed_requests(web, gestor_web, escuela, inspector_a):
    assert (
        web.get(
            API, RAW_URI=API, HTTP_X_SISOC_WEB_GATE=_signed(gestor_web, web, target=API)
        ).status_code
        == 200
    )
    sin_firma = web.post(NUEVA, _datos(escuela, inspector_a), RAW_URI=NUEVA, **XHR)
    assert sin_firma.status_code == 403
    assert sin_firma.json() == {"detail": web_gate.DETAIL_REJECTED}
    assert AsignacionEscuela.objects.count() == 0
    firmado = web.post(
        NUEVA,
        _datos(escuela, inspector_a),
        RAW_URI=NUEVA,
        HTTP_X_SISOC_WEB_GATE=_signed(gestor_web, web, target=NUEVA, method="POST"),
        **XHR,
    )
    assert firmado.status_code == 200
    asignacion = AsignacionEscuela.objects.get()
    quitar = _quitar(asignacion)
    assert web.post(quitar, RAW_URI=quitar).status_code == 403
    assert AsignacionEscuela.objects.count() == 1
    assert (
        web.post(
            quitar,
            RAW_URI=quitar,
            HTTP_X_SISOC_WEB_GATE=_signed(
                gestor_web, web, target=quitar, method="POST"
            ),
        ).status_code
        == 200
    )
    assert AsignacionEscuela.objects.count() == 0


# --- Local React entries -----------------------------------------------------------------


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(
        '<!doctype html><script src="/v2/sisoc/assets/app-1.js"></script>',
        encoding="utf-8",
    )
    module = types.ModuleType("asignaciones_preview_test_urls")
    module.urlpatterns = actas_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_entries_serve_the_index_after_the_native_guards(
    web, jornada, inspector_a, escuela
):
    del jornada
    paginas = ("/inspecciones/asignaciones/", "/inspecciones/asignaciones/nueva/")
    for pagina in paginas:
        respuesta = web.get(pagina)
        assert respuesta.status_code == 200, pagina
        assert b"/inspecciones/react/assets/app-1.js" in respuesta.content, pagina
        assert "no-store" in respuesta["Cache-Control"]
        assert "csrftoken" in respuesta.cookies
    assert web.get("/inspecciones/asignaciones/", {"page": "9"}).status_code == 200
    client = Client()
    for pagina in paginas:
        assert client.get(pagina)["Location"].startswith("/login"), pagina
    client.force_login(inspector_a)
    for pagina in paginas:
        assert client.get(pagina).status_code == 403, pagina
    # The page-mode POST and the removal stay native.
    native = web.post(
        "/inspecciones/asignaciones/nueva/",
        _datos(escuela, inspector_a, fecha=date(2026, 3, 4).isoformat()),
    )
    assert native.status_code == 302
    assert native["Location"] == "/inspecciones/asignaciones/?fecha=2026-03-04"


def test_production_urlconf_keeps_the_native_tab(web):
    respuesta = web.get(reverse("inspecciones_asignaciones"))

    assert respuesta.status_code == 200
    assert "inspecciones/asignaciones.html" in [t.name for t in respuesta.templates]
