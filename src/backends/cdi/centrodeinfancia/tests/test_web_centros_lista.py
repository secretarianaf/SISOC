"""Web API (G1 v1) of the CDI centres list: ``/api/web/cdi/centros/``.

Read-only projection of ``CentroDeInfanciaListView`` (CDI09.01) for the React
page. The monolith tests go through ``config.settings_all`` (policy evaluated
locally); the runtime tests switch to ``SISOC_BACKEND="cdi"`` with the real
runtime URLconf, where only a request the core signed reaches the view. Cells
are compared with the HTML the native page renders for the same request.
"""

import json
from html import unescape
from html.parser import HTMLParser

import pytest
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.storage.cookie import CookieStorage
from django.db import connection
from django.http import HttpResponse
from django.test import Client, RequestFactory, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from centrodeinfancia.models import AccesoCDI, CentroDeInfancia, NominaCentroInfancia
from ciudadanos.models import Ciudadano
from core import web_gate
from core.constants import UserGroups
from core.models import PreferenciaColumnas, Provincia

ROOT = "/api/web/cdi/centros/"
WRITES = ("INSERT", "UPDATE", "DELETE")

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return User.objects.get(pk=user.pk)


def _permiso(codigo):
    app, codename = codigo.split(".")
    permiso = Permission.objects.filter(
        content_type__app_label=app, codename=codename
    ).first()
    if permiso:
        return permiso
    return Permission.objects.create(
        content_type=ContentType.objects.get_for_model(Group),
        codename=codename,
        name=codename,
    )


def _usuario(
    username,
    *,
    perms=("centrodeinfancia.view_centrodeinfancia",),
    grupo=None,
    superuser=False,
):
    user = User.objects.create_user(username=username, is_superuser=superuser)
    for codigo in perms:
        user.user_permissions.add(_permiso(codigo))
    if grupo:
        user.groups.add(Group.objects.get_or_create(name=grupo)[0])
    return _ready(user)


def _cliente(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="datos")
def datos_fixture():
    mendoza = Provincia.objects.create(nombre="Mendoza")
    san_juan = Provincia.objects.create(nombre="San Juan")
    propio = CentroDeInfancia.objects.create(
        nombre="CDI Propio",
        organizacion="Cooperadora Uno",
        provincia=mendoza,
        calle="Calle 1",
        telefono="261-1",
        nombre_referente="Ana",
        apellido_referente="Pérez",
    )
    otro = CentroDeInfancia.objects.create(
        nombre="CDI Ultimo", provincia=san_juan, nombre_referente="Solo"
    )
    ciudadano = Ciudadano.objects.create(
        apellido="Gomez", nombre="Luz", documento=44444444
    )
    NominaCentroInfancia.objects.create(
        centro=propio, ciudadano=ciudadano, estado=NominaCentroInfancia.ESTADO_ACTIVO
    )
    return {"mendoza": mendoza, "san_juan": san_juan, "propio": propio, "otro": otro}


class _Filas(HTMLParser):
    """Rows of the native table: whitespace-normalised cell text and ``data-*`` value."""

    def __init__(self):
        super().__init__()
        self.filas, self._celda = [], None
        self._fila = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._fila = []
        elif tag == "td" and self._fila is not None:
            data = next((v for k, v in attrs if k.startswith("data-")), None)
            self._celda = {"text": "", "data": data}

    def handle_data(self, data):
        if self._celda is not None:
            self._celda["text"] += data

    def handle_endtag(self, tag):
        if tag == "td" and self._celda is not None:
            self._celda["text"] = " ".join(self._celda["text"].split())
            self._fila.append(self._celda)
            self._celda = None
        elif tag == "tr" and self._fila is not None:
            if self._fila:
                self.filas.append(self._fila)
            self._fila = None


def _nativas(client, params=None):
    respuesta = client.get(reverse("centrodeinfancia"), params or {})
    assert respuesta.status_code == 200
    analizador = _Filas()
    analizador.feed(respuesta.content.decode())
    return respuesta, analizador.filas


def _ids(data):
    return [fila["id"] for fila in data["results"]]


# --- Monolith: shape, parity and permissions --------------------------------


def test_projects_the_native_list_with_its_cells(datos):
    client = _cliente(_usuario("web-centros-super", superuser=True))

    respuesta = client.get(ROOT)

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == "application/json"
    assert respuesta["Cache-Control"] == "private, no-store"
    assert "Cookie" in respuesta["Vary"]
    data = respuesta.json()
    assert set(data) == {
        "breadcrumb",
        "filters_config",
        "favorites",
        "columns",
        "headers",
        "results",
        "page",
        "can_export",
        "nomina_ninos",
        "urls",
        "messages",
    }
    assert data["breadcrumb"] == [
        {"text": "Centro de Desarrollo Infantil", "url": "/centrodeinfancia/listar"},
        {"text": "Listar", "url": None},
    ]
    assert [h["key"] for h in data["headers"]] == [
        "nombre",
        "organizacion",
        "tiene_nomina",
        "provincia",
        "departamento",
        "municipio",
    ]
    assert [h["title"] for h in data["headers"]][:3] == [
        "Nombre",
        "Organización",
        "Tiene nómina",
    ]
    assert _ids(data) == [datos["propio"].pk, datos["otro"].pk]
    propio, otro = data["results"]
    assert propio["cells"][0] == {
        "text": "CDI Propio",
        "sort": "CDI Propio",
        "url": f"/centrodeinfancia/detalle/{datos['propio'].pk}",
    }
    assert [c["text"] for c in propio["cells"]] == [
        "CDI Propio",
        "Cooperadora Uno",
        "Si",
        "Mendoza",
        "-",
        "-",
    ]
    assert otro["cells"][1] == {"text": "-", "sort": "", "url": None}
    assert otro["cells"][2]["text"] == "No"
    assert propio["urls"] == {
        "detail": f"/centrodeinfancia/detalle/{datos['propio'].pk}",
        "edit": f"/centrodeinfancia/editar/{datos['propio'].pk}",
        "delete": f"/centrodeinfancia/eliminar/{datos['propio'].pk}",
    }
    assert data["page"] == {
        "is_paginated": False,
        "number": 1,
        "previous": None,
        "next": None,
        "range": [1],
        "count": 2,
        "query_prefix": "",
    }
    assert data["urls"] == {
        "list": "/centrodeinfancia/listar",
        "add": "/centrodeinfancia/crear",
        "export": "/centrodeinfancia/exportar",
    }
    assert data["columns"]["list_key"] == "centrodeinfancia_list"
    assert data["messages"] == []


def test_cells_match_the_native_html_for_every_column(datos):
    del datos
    user = _usuario("web-centros-paridad", superuser=True)
    claves = [
        "nombre",
        "organizacion",
        "tiene_nomina",
        "provincia",
        "departamento",
        "municipio",
        "localidad",
        "calle",
        "telefono",
        "referente",
    ]
    PreferenciaColumnas.objects.create(
        usuario=user, listado="centrodeinfancia_list", columnas=claves
    )
    client = _cliente(user)

    data = client.get(ROOT).json()
    _, filas = _nativas(client)

    assert [h["key"] for h in data["headers"]] == claves
    assert len(filas) == len(data["results"]) == 2
    for nativa, fila in zip(filas, data["results"]):
        celdas = nativa[: len(claves)]
        assert [" ".join(c["text"].split()) for c in fila["cells"]] == [
            c["text"] for c in celdas
        ]
        # ``data-*`` sort value of the native cell; an empty one falls back to text.
        assert [c["sort"] for c in fila["cells"]] == [
            c["data"] if c["data"] is not None else "" for c in celdas
        ]
    referente = {c["text"] for c in data["results"][0]["cells"]}
    assert "Ana Pérez" in referente
    assert data["results"][1]["cells"][9] == {
        "text": "Solo",
        "sort": "Solo ",
        "url": None,
    }


def test_a_saved_column_preference_changes_headers_and_cells(datos):
    del datos
    user = _usuario("web-centros-columnas", superuser=True)
    PreferenciaColumnas.objects.create(
        usuario=user, listado="centrodeinfancia_list", columnas=["telefono", "nombre"]
    )

    data = _cliente(user).get(ROOT).json()

    assert [h["key"] for h in data["headers"]] == ["telefono", "nombre"]
    assert [c["text"] for c in data["results"][0]["cells"]] == ["261-1", "CDI Propio"]
    assert data["columns"]["active"] == ["telefono", "nombre"]


def test_pages_of_ten_with_the_native_link_prefix(datos):
    for numero in range(12):
        CentroDeInfancia.objects.create(
            nombre=f"Centro {numero:02d}", provincia=datos["mendoza"]
        )
    client = _cliente(_usuario("web-centros-paginas", superuser=True))

    primera = client.get(ROOT).json()
    segunda = client.get(ROOT, {"page": 2, "x": "a b", "busqueda": "Centro"}).json()

    assert len(primera["results"]) == 10
    assert primera["page"]["is_paginated"] is True
    assert (primera["page"]["previous"], primera["page"]["next"]) == (None, 2)
    assert primera["page"]["range"] == [1, 2]
    assert primera["page"]["count"] == 14
    assert len(segunda["results"]) == 2
    assert segunda["page"]["number"] == 2
    assert segunda["page"]["previous"] == 1
    assert segunda["page"]["count"] == 12
    assert segunda["page"]["query_prefix"] == "busqueda=Centro&x=a%20b&"
    nativa, _ = _nativas(client, {"page": 2, "x": "a b", "busqueda": "Centro"})
    assert 'href="?busqueda=Centro&x=a%20b&page=1"' in unescape(nativa.content.decode())


@pytest.mark.parametrize("pagina", ["3", "0", "abc", "-1"])
def test_an_invalid_page_is_404_like_the_native_list(datos, pagina):
    del datos
    client = _cliente(_usuario("web-centros-404", superuser=True))

    assert client.get(ROOT, {"page": pagina}).status_code == 404
    assert client.get(reverse("centrodeinfancia"), {"page": pagina}).status_code == 404


def test_search_and_advanced_filters_narrow_like_the_native_list(datos):
    client = _cliente(_usuario("web-centros-filtros", superuser=True))
    filtros = json.dumps(
        {
            "logic": "AND",
            "items": [{"field": "provincia", "op": "eq", "value": "San Juan"}],
        }
    )

    for params, esperado in (
        ({"busqueda": "Cooperadora"}, [datos["propio"].pk]),
        ({"busqueda": " ultimo "}, [datos["otro"].pk]),
        ({"busqueda": "nada"}, []),
        ({"filters": filtros}, [datos["otro"].pk]),
    ):
        data = client.get(ROOT, params).json()
        nativa = client.get(reverse("centrodeinfancia"), params)
        assert (
            _ids(data) == esperado == [c.pk for c in nativa.context["centros"]]
        ), params
    vacia = client.get(ROOT, {"busqueda": "nada"}).json()
    assert vacia["page"]["count"] is None
    assert vacia["page"]["is_paginated"] is False
    assert [f["name"] for f in vacia["filters_config"]["fields"]][:3] == [
        "nombre",
        "codigo_cdi",
        "organizacion",
    ]


def test_scope_limits_the_list_to_the_actors_centres(datos):
    user = _usuario("web-centros-referente")
    AccesoCDI.objects.create(user=user, centro=datos["propio"])

    data = _cliente(user).get(ROOT).json()

    assert _ids(data) == [datos["propio"].pk]
    assert data["page"]["count"] == 1


def test_export_and_children_pdf_follow_the_native_rules(datos):
    del datos
    plano = _usuario("web-centros-plano")
    csv = _usuario(
        "web-centros-csv",
        perms=("centrodeinfancia.view_centrodeinfancia", "auth.role_exportar_a_csv"),
    )
    superusuario = _usuario("web-centros-admin", superuser=True)
    egp = _usuario("web-centros-egp", grupo=UserGroups.SIMEPI_EGP)

    assert _cliente(plano).get(ROOT).json()["can_export"] is False
    assert _cliente(plano).get(ROOT).json()["nomina_ninos"] is None
    assert _cliente(csv).get(ROOT).json()["can_export"] is True
    admin = _cliente(superusuario).get(ROOT).json()
    assert admin["can_export"] is True
    assert admin["nomina_ninos"] == {
        "provincias": [
            {"id": p.pk, "nombre": p.nombre}
            for p in Provincia.objects.order_by("nombre")
        ],
        "url": "/centrodeinfancia/nomina-ninos/descargar/",
    }
    assert _cliente(egp).get(ROOT).json()["nomina_ninos"] == {
        "provincias": [],
        "url": "/centrodeinfancia/nomina-ninos/descargar/",
    }


def test_reads_never_write(datos):
    del datos
    client = _cliente(_usuario("web-centros-lectura", superuser=True))
    client.get(ROOT)

    with CaptureQueriesContext(connection) as queries:
        assert client.get(ROOT, {"busqueda": "CDI"}).status_code == 200

    assert not [
        q["sql"] for q in queries.captured_queries if q["sql"].startswith(WRITES)
    ]


def _queue_message(client, text):
    """Queue a message in the client's cookie, as a native view would."""
    request = RequestFactory().get("/")
    request.COOKIES = {k: v.value for k, v in client.cookies.items()}
    storage = CookieStorage(request)
    storage.add(messages.SUCCESS, text)
    response = HttpResponse()
    storage.update(response)
    client.cookies.update(response.cookies)


def test_pending_messages_are_returned_once_like_the_native_toasts(datos):
    del datos
    client = _cliente(_usuario("web-centros-mensajes", superuser=True))
    _queue_message(client, "Centro de Desarrollo Infantil dado de baja correctamente.")

    primera = client.get(ROOT).json()["messages"]
    segunda = client.get(ROOT).json()["messages"]

    assert primera == [
        {
            "message": "Centro de Desarrollo Infantil dado de baja correctamente.",
            "level": "success",
        }
    ]
    assert segunda == []


def test_anonymous_gets_401_json():
    respuesta = Client().get(ROOT)

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert respuesta["Cache-Control"] == "private, no-store"


def test_without_the_view_permission_gets_403(datos):
    del datos
    sin_permiso = _usuario("web-centros-sin-permiso", perms=())
    otro_permiso = _usuario(
        "web-centros-otro", perms=("centrodeinfancia.view_nominacentroinfancia",)
    )

    for user in (sin_permiso, otro_permiso):
        respuesta = _cliente(user).get(ROOT)
        assert respuesta.status_code == 403
        assert respuesta.json() != {"detail": web_gate.DETAIL_REQUIREMENT}


def test_pending_web_requirement_is_reported_and_a_forged_header_is_ignored(datos):
    del datos
    user = _usuario("web-centros-pendiente", superuser=True)
    user.profile.must_change_password = True
    user.profile.save()
    client = _cliente(user)
    falso = web_gate.sign(
        audience="cdi",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method="GET",
        target=ROOT,
    )

    respuesta = client.get(ROOT, HTTP_X_SISOC_WEB_GATE=falso, RAW_URI=ROOT)

    assert respuesta.status_code == 403
    assert respuesta.json()["detail"] == web_gate.DETAIL_REQUIREMENT
    assert respuesta.json()["state"]


def test_only_get_is_served(datos):
    del datos
    client = _cliente(_usuario("web-centros-metodos", superuser=True))

    assert client.post(ROOT).status_code == 405
    assert client.head(ROOT).status_code == 200


def test_admindocs_head_does_not_bypass_the_web_api():
    staff = User.objects.create_user("web-centros-staff", is_staff=True)
    client = _cliente(_ready(staff))

    respuesta = client.head(ROOT)

    assert "X-View" not in respuesta
    assert respuesta.status_code == 403


# --- Runtime: only the core's signed attestation reaches the view -----------


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="cdi",
        ROOT_URLCONF="cdi_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, *, target=ROOT, method="GET", now=None, audience=None):
    return web_gate.sign(
        audience=audience or "cdi",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method=method,
        target=target,
        now=now,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_a_signed_request(datos):
    user = _usuario("web-centros-runtime", superuser=True)
    client = _cliente(user)
    target = f"{ROOT}?busqueda=Propio"

    respuesta = client.get(
        target,
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(user, client, target=target),
    )

    assert respuesta.status_code == 200
    assert _ids(respuesta.json()) == [datos["propio"].pk]
    assert respuesta["Cache-Control"] == "private, no-store"


@pytest.mark.usefixtures("runtime")
def test_runtime_rejects_missing_tampered_and_expired_attestations(datos):
    del datos
    user = _usuario("web-centros-runtime-mal", superuser=True)
    client = _cliente(user)
    valido = _signed(user, client)
    alterados = {
        "missing": None,
        "other_target": _signed(user, client, target=ROOT + "?page=2"),
        "other_audience": _signed(user, client, audience="inspecciones"),
        "other_method": _signed(user, client, method="POST"),
        "expired": _signed(user, client, now=timezone.now().timestamp() - 61),
        "bad_signature": valido[:-2] + ("AA" if not valido.endswith("AA") else "BB"),
    }

    for motivo, token in alterados.items():
        extra = {"RAW_URI": ROOT}
        if token is not None:
            extra["HTTP_X_SISOC_WEB_GATE"] = token
        respuesta = client.get(ROOT, **extra)
        assert respuesta.status_code == 403, motivo
        assert respuesta.json() == {"detail": web_gate.DETAIL_REJECTED}, motivo
    assert (
        client.get(ROOT, RAW_URI=ROOT, HTTP_X_SISOC_WEB_GATE=valido).status_code == 200
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_still_applies_the_view_permission(datos):
    del datos
    user = _usuario("web-centros-runtime-sin", perms=())
    client = _cliente(user)

    respuesta = client.get(
        ROOT, RAW_URI=ROOT, HTTP_X_SISOC_WEB_GATE=_signed(user, client)
    )

    assert respuesta.status_code == 403
    assert respuesta.json() != {"detail": web_gate.DETAIL_REJECTED}


@pytest.mark.usefixtures("runtime")
def test_runtime_anonymous_gets_401():
    respuesta = Client().get(ROOT, RAW_URI=ROOT)

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
