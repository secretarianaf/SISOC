"""Web API (G1 v1) of the Tablero tab (IN03): ``/api/web/inspecciones/tablero/``.

The shell runs ``TableroView``; the data, CSV and download routes return the
native views' own response, so every consumer reads the same service result.
Monolith tests use ``config.settings_all``; runtime tests switch to the
inspecciones URLconf.
"""

import csv
import io
import types
import zipfile

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from config.urls_all import urlpatterns as monolith_patterns
from core import web_gate
from inspecciones.models import Acta
from inspecciones.services import descarga_actas, tablero
from inspecciones.services.formato import hoy
from inspecciones.web_preview import actas_preview_patterns
from tests.test_inspecciones_tablero import crear_acta, nueva_escuela

API = "/api/web/inspecciones/tablero/"
DATOS = API + "datos/"
CSV = API + "exportar.csv"
DESCARGA = API + "descargar-actas/"
NATIVO = {
    DATOS: "/inspecciones/tablero/datos/",
    CSV: "/inspecciones/tablero/exportar.csv",
    DESCARGA: "/inspecciones/tablero/descargar-actas/",
}
PDF = b"%PDF-1.4 contenido"
WRITES = ("INSERT", "UPDATE", "DELETE")

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _cache_limpio():
    cache.clear()
    yield
    cache.clear()


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


@pytest.fixture(name="geo")
def geo_fixture(geografia):
    return {
        "a": (geografia["bsas"], geografia["san_justo"]),
        "b": (geografia["tdf"], geografia["ushuaia"]),
    }


@pytest.fixture(name="jornada")
def jornada_fixture(inspector_a, inspector_b, geo):
    """Four valid actas today plus one cancelled and one test acta (never counted)."""
    a = nueva_escuela("060000011", "a", geo)
    b = nueva_escuela("060000012", "b", geo)
    actas = [
        crear_acta(inspector_a, a, turno="manana"),
        crear_acta(inspector_b, a, turno="tarde", resultado="cerrada"),
        crear_acta(inspector_a, b, notificacion=Acta.EstadoNotificacion.CARGADA),
        crear_acta(inspector_a, None, ubicacion="manual", firma_tipo="firma"),
    ]
    crear_acta(inspector_a, a, estado=Acta.Estado.ANULADA)
    crear_acta(inspector_a, b, es_prueba=True)
    return {"actas": actas, "a": a, "b": b}


def _con_pdf(acta, contenido=PDF):
    acta.pdf.save("acta.pdf", ContentFile(contenido), save=True)
    return acta


def _cuerpo(respuesta):
    if getattr(respuesta, "streaming", False):
        return b"".join(respuesta.streaming_content)
    return respuesta.content


def _estado():
    return list(Acta.objects.order_by("pk").values_list("pk", "estado", "es_prueba"))


# --- Shell -------------------------------------------------------------------------


def test_shell_projects_the_native_tab(web, jornada, geo):
    del jornada
    respuesta = web.get(API)

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    nativo = web.get(reverse("inspecciones_tablero")).context
    assert data["layout"]["breadcrumb"] == [
        {"text": "Inicio", "url": reverse("inicio")},
        {"text": "Inspecciones escolares", "url": reverse("inspecciones_panel")},
        {"text": "Tablero", "url": None},
    ]
    assert [tab["id"] for tab in data["tabs"]] == [
        "tablero",
        "escuelas",
        "asignaciones",
        "actas",
    ]
    assert data["options"] == nativo["opciones"]
    assert data["options"]["provincias"][0] == {
        "id": geo["a"][0].pk,
        "nombre": "Buenos Aires",
    }
    assert data["intervalo_ms"] == nativo["intervalo_ms"] == 5000
    assert data["filters"] == {
        "fecha": hoy().isoformat(),
        "provincia": "",
        "localidad": "",
        "inspector": "",
        "turno": "",
        "notificacion": "",
    }
    assert data["urls"] == {"datos": DATOS, "exportar": CSV, "descargar": DESCARGA}
    assert data["messages"] == []


def test_shell_carries_the_validated_filters_and_ignores_invalid_ones(
    web, inspector_a, geo
):
    ok = web.get(
        API,
        {
            "fecha": "2026-03-04",
            "provincia": geo["a"][0].pk,
            "localidad": geo["a"][1].pk,
            "inspector": inspector_a.pk,
            "turno": "tarde",
            "notificacion": "pendiente",
        },
    ).json()["filters"]
    assert ok == {
        "fecha": "2026-03-04",
        "provincia": str(geo["a"][0].pk),
        "localidad": str(geo["a"][1].pk),
        "inspector": str(inspector_a.pk),
        "turno": "tarde",
        "notificacion": "pendiente",
    }
    invalid = web.get(
        API,
        {"fecha": "x", "provincia": "x", "turno": "zzz", "notificacion": "otra"},
    ).json()["filters"]
    nativo = web.get(
        reverse("inspecciones_tablero"),
        {"fecha": "x", "provincia": "x", "turno": "zzz", "notificacion": "otra"},
    ).context["filtros"]
    assert invalid["fecha"] == nativo.fecha.isoformat() == hoy().isoformat()
    assert (invalid["provincia"], invalid["turno"], invalid["notificacion"]) == (
        "",
        "",
        "",
    )


# --- Live data ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"turno": "tarde"},
        {"notificacion": "cargada"},
        {"fecha": "2020-01-01"},
        {"turno": "noche", "provincia": "x"},
    ],
)
def test_data_is_the_native_response(web, jornada, params):
    del jornada
    api = web.get(DATOS, params)
    nativo = web.get(NATIVO[DATOS], params)

    assert api.status_code == 200
    assert api.json() == nativo.json()
    assert "no-store" in api["Cache-Control"]
    assert api["Content-Type"].startswith("application/json")


def test_data_filters_by_province_and_inspector(web, jornada, inspector_a, geo):
    del jornada
    params = {"provincia": geo["a"][0].pk, "inspector": inspector_a.pk}
    data = web.get(DATOS, params).json()

    assert data["indicadores"]["actas_validas"] == 1
    assert data["opciones"]["localidades"] == [
        {"id": geo["a"][1].pk, "nombre": "San Justo · La Matanza"}
    ]
    assert data == web.get(NATIVO[DATOS], params).json()


def test_all_consumers_count_the_same_actas(web, jornada):
    """Figures, rows, map, CSV and ZIP agree: no cancelled and no test acta."""
    for acta in jornada["actas"]:
        _con_pdf(acta)
    data = web.get(DATOS).json()
    csv_texto = web.get(CSV).content.decode("utf-8").lstrip("﻿")
    filas = list(csv.reader(io.StringIO(csv_texto), delimiter=";"))[1:]
    zip_ = web.get(DESCARGA)
    with zipfile.ZipFile(io.BytesIO(_cuerpo(zip_))) as archivo:
        pdfs = [n for n in archivo.namelist() if n.endswith(".pdf")]

    esperadas = sorted(a.numero for a in jornada["actas"])
    assert data["indicadores"]["actas_validas"] == 4
    assert sorted(a["numero"] for a in data["ultimas"]) == esperadas
    assert sorted(fila[0] for fila in filas) == esperadas
    assert sorted(p.removesuffix(".pdf") for p in pdfs) == esperadas
    assert sum(t["cantidad"] for t in data["turnos"]) == 4
    puntos = [p["numero"] for p in data["mapa"]["puntos"]]
    assert len(puntos) == data["mapa"]["con_gps"] == 3
    assert data["mapa"]["sin_coordenadas"] == 1
    assert (
        len(tablero.actas_validas(tablero.leer_filtros({})))
        == data["indicadores"]["actas_validas"]
    )


# --- CSV ---------------------------------------------------------------------------


def test_csv_is_the_native_file(web, jornada, inspector_a):
    del jornada
    for params in ({}, {"inspector": inspector_a.pk, "turno": "manana"}):
        api = web.get(CSV, params)
        nativo = web.get(NATIVO[CSV], params)

        assert api.status_code == 200
        assert api.content == nativo.content
        assert api["Content-Type"] == nativo["Content-Type"]
        assert api["Content-Disposition"] == nativo["Content-Disposition"]
        assert "no-store" in api["Cache-Control"]
    assert "attachment" in api["Content-Disposition"]


# --- Download ----------------------------------------------------------------------


def test_one_acta_downloads_as_pdf_with_private_headers(web, inspector_a, geo):
    acta = _con_pdf(crear_acta(inspector_a, nueva_escuela("060000021", "a", geo)))

    respuesta = web.get(DESCARGA)

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == "application/pdf"
    assert f"{acta.numero}.pdf" in respuesta["Content-Disposition"]
    assert "attachment" in respuesta["Content-Disposition"]
    assert respuesta["Cache-Control"] == "private, no-store"
    assert respuesta["X-Content-Type-Options"] == "nosniff"
    assert _cuerpo(respuesta) == PDF


def test_several_actas_download_as_zip_like_the_native_route(web, jornada):
    for acta in jornada["actas"]:
        _con_pdf(acta, PDF + acta.numero.encode())

    api = web.get(DESCARGA)
    nativo = web.get(NATIVO[DESCARGA])

    assert api["Content-Type"] == nativo["Content-Type"] == "application/zip"
    assert api["Content-Disposition"] == nativo["Content-Disposition"]
    assert api["X-Content-Type-Options"] == "nosniff"
    with zipfile.ZipFile(io.BytesIO(_cuerpo(api))) as a:
        with zipfile.ZipFile(io.BytesIO(_cuerpo(nativo))) as n:
            assert sorted(a.namelist()) == sorted(n.namelist())


def test_download_respects_the_filters(web, jornada, inspector_b):
    for acta in jornada["actas"]:
        _con_pdf(acta)

    respuesta = web.get(DESCARGA, {"inspector": inspector_b.pk})

    assert respuesta["Content-Type"] == "application/pdf"
    assert f"{jornada['actas'][1].numero}.pdf" in respuesta["Content-Disposition"]


def test_nothing_to_download_warns_and_returns_to_the_tablero(web):
    respuesta = web.get(DESCARGA, {"turno": "tarde"})

    assert respuesta.status_code == 302
    assert respuesta["Location"].startswith("/inspecciones/tablero/?")
    assert "turno=tarde" in respuesta["Location"]
    assert not respuesta.has_header("Content-Disposition")
    mensajes = web.get(API).json()["messages"]
    assert mensajes == [
        {"message": descarga_actas.MENSAJE_SIN_ACTAS, "level": "warning"}
    ]


def test_only_actas_without_pdf_and_the_cap_keep_the_native_messages(
    web, inspector_a, geo, monkeypatch
):
    crear_acta(inspector_a, nueva_escuela("060000031", "a", geo))
    sin_pdf = web.get(DESCARGA)
    assert sin_pdf.status_code == 302
    assert [m["message"] for m in web.get(API).json()["messages"]] == [
        descarga_actas.MENSAJE_SIN_PDF
    ]
    monkeypatch.setattr(descarga_actas, "MAX_ACTAS", 1)
    _con_pdf(crear_acta(inspector_a, nueva_escuela("060000032", "a", geo)))
    _con_pdf(crear_acta(inspector_a, nueva_escuela("060000033", "a", geo)))
    tope = web.get(DESCARGA)
    assert tope.status_code == 302
    assert [m["message"] for m in web.get(API).json()["messages"]] == [
        descarga_actas.mensaje_tope(1)
    ]


# --- Methods, reads ----------------------------------------------------------------


def test_reads_never_write_and_only_get(web, jornada):
    del jornada
    with CaptureQueriesContext(connection) as consultas:
        for url in (API, DATOS, CSV, DESCARGA):
            assert web.get(url).status_code in (200, 302), url
    assert not [
        q["sql"] for q in consultas.captured_queries if q["sql"].startswith(WRITES)
    ]
    for url in (API, DATOS, CSV, DESCARGA):
        for metodo in ("post", "put", "patch", "delete"):
            assert getattr(web, metodo)(url).status_code == 405, (url, metodo)


# --- Access ------------------------------------------------------------------------


def test_guards_do_not_leak_or_write(gestor_web, client, inspector_a, jornada):
    del jornada
    antes = _estado()
    otro = get_user_model().objects.create_user("otro")
    for url in (API, DATOS, CSV, DESCARGA):
        anonimo = Client().get(url)
        assert anonimo.status_code == 401, url
        assert anonimo.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    for usuario in (inspector_a, otro):
        client.force_login(_ready(usuario))
        for url in (API, DATOS, CSV, DESCARGA):
            respuesta = client.get(url)
            assert respuesta.status_code == 403, url
            assert b"ACTA-" not in respuesta.content, url
    assert _estado() == antes


def test_superuser_and_coordination_keep_the_native_rule(client, coordinacion):
    superuser = _ready(
        get_user_model().objects.create_superuser("super_web", password="x")
    )
    for usuario in (superuser, _ready(coordinacion)):
        client.force_login(usuario)
        for url in (API, DATOS, CSV):
            assert client.get(url).status_code == 200, (usuario.username, url)


def test_admindocs_head_does_not_bypass_the_api(client, jornada):
    del jornada
    staff = _ready(get_user_model().objects.create_user("staff_web", is_staff=True))
    client.force_login(staff)

    for url in (API, DATOS, CSV, DESCARGA):
        respuesta = client.head(url)
        assert "X-View" not in respuesta, url
        assert respuesta.status_code in (403, 405), url


# --- Runtime -----------------------------------------------------------------------


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="inspecciones",
        ROOT_URLCONF="inspecciones_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, *, target):
    return web_gate.sign(
        audience="inspecciones",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method="GET",
        target=target,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_only_signed_requests(web, gestor_web, jornada):
    del jornada
    for url in (API, DATOS, CSV):
        sin_firma = web.get(url, RAW_URI=url)
        assert sin_firma.status_code == 403, url
        assert sin_firma.json() == {"detail": web_gate.DETAIL_REJECTED}, url
        firmado = web.get(
            url, RAW_URI=url, HTTP_X_SISOC_WEB_GATE=_signed(gestor_web, web, target=url)
        )
        assert firmado.status_code == 200, url
    otro = web.get(
        DATOS,
        RAW_URI=DATOS,
        HTTP_X_SISOC_WEB_GATE=_signed(gestor_web, web, target=API),
    )
    assert otro.status_code == 403


# --- Local React entry -------------------------------------------------------------


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(
        '<!doctype html><script src="/v2/sisoc/assets/app-1.js"></script>',
        encoding="utf-8",
    )
    module = types.ModuleType("tablero_preview_test_urls")
    module.urlpatterns = actas_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_entry_serves_the_index_after_the_native_guards(web, inspector_a):
    respuesta = web.get("/inspecciones/tablero/")
    assert respuesta.status_code == 200
    assert b"/inspecciones/react/assets/app-1.js" in respuesta.content
    assert "no-store" in respuesta["Cache-Control"]
    assert "csrftoken" in respuesta.cookies
    client = Client()
    assert client.get("/inspecciones/tablero/")["Location"].startswith("/login")
    client.force_login(inspector_a)
    assert client.get("/inspecciones/tablero/").status_code == 403
    # The data, CSV and download stay the native routes.
    assert web.get("/inspecciones/tablero/datos/").json()["indicadores"]


def test_production_urlconf_keeps_the_native_tab(web):
    respuesta = web.get(reverse("inspecciones_tablero"))

    assert respuesta.status_code == 200
    assert "inspecciones/tablero.html" in [t.name for t in respuesta.templates]
