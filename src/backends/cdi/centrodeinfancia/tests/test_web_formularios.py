"""Web API (G1 v1) of the CDI institutional form list and detail (CDI03).

``/api/web/cdi/centros/<pk>/formularios/`` and ``.../<form_pk>/`` run the native
list and detail views. Every cell is compared with the HTML the native page
renders for the same records.
"""

from datetime import date, time
from decimal import Decimal
from html.parser import HTMLParser

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from centrodeinfancia.models import (
    AccesoCDI,
    CentroDeInfancia,
    FormularioCDI,
    FormularioCDIArticulationFrequency,
    FormularioCDIHorarioFuncionamiento,
    FormularioCDIRoomDistribution,
    FormularioCDIWaitlistByAgeGroup,
)
from core import web_gate
from core.models import Provincia

WRITES = ("INSERT", "UPDATE", "DELETE")
VER = "centrodeinfancia.view_formulariocdi"
VER_CENTRO = "centrodeinfancia.view_centrodeinfancia"

pytestmark = pytest.mark.django_db


def _lista(centro_pk, pagina=None):
    base = f"/api/web/cdi/centros/{centro_pk}/formularios/"
    return base if pagina is None else f"{base}?page={pagina}"


def _detalle(centro_pk, form_pk):
    return f"/api/web/cdi/centros/{centro_pk}/formularios/{form_pk}/"


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
    return permiso or Permission.objects.create(
        content_type=ContentType.objects.get_for_model(Group),
        codename=codename,
        name=codename,
    )


def _usuario(username, *, perms=(VER,), superuser=False):
    user = User.objects.create_user(
        username=username,
        is_superuser=superuser,
        first_name="Ana",
        last_name="Paz",
    )
    for codigo in perms:
        user.user_permissions.add(_permiso(codigo))
    return _ready(user)


def _cliente(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="datos")
def datos_fixture():
    provincia = Provincia.objects.create(nombre="Mendoza")
    centro = CentroDeInfancia.objects.create(
        nombre="CDI Girasoles", provincia=provincia, codigo_cdi="CDI-7"
    )
    otro = CentroDeInfancia.objects.create(nombre="CDI Ajeno", provincia=provincia)
    autor = User.objects.create_user("autor-form", first_name="Lu", last_name="Gómez")
    formulario = FormularioCDI.objects.create(
        centro=centro,
        created_by=autor,
        fecha_relevamiento=date(2026, 3, 13),
        nombre_completo_respondente="Ana Pérez",
        codigo_cdi="CDI-7",
        nombre_cdi="CDI Girasoles",
        dias_funcionamiento=["lunes", "martes"],
    )
    FormularioCDIHorarioFuncionamiento.objects.create(
        formulario=formulario, dia="lunes", hora_apertura=time(8), hora_cierre=None
    )
    FormularioCDIRoomDistribution.objects.create(
        formulario=formulario,
        grupo_etario="lactantes",
        cantidad_salas=2,
        superficie_exclusiva_m2=Decimal("12.5"),
        cantidad_ninos=0,
        cantidad_personal_sala=4,
    )
    FormularioCDIRoomDistribution.objects.create(
        formulario=formulario, grupo_etario="tres_anos", cantidad_salas=1
    )
    FormularioCDIWaitlistByAgeGroup.objects.create(
        formulario=formulario, grupo_etario="lactantes", cantidad_demanda_insatisfecha=5
    )
    FormularioCDIArticulationFrequency.objects.create(
        formulario=formulario, tipo_institucion="justicia_juzgado", frecuencia="mensual"
    )
    sin_autor = FormularioCDI.objects.create(centro=centro)
    ajeno = FormularioCDI.objects.create(centro=otro)
    return {
        "centro": centro,
        "otro": otro,
        "formulario": formulario,
        "sin_autor": sin_autor,
        "ajeno": ajeno,
    }


class _Celdas(HTMLParser):
    """Texts of the ``td`` cells, the ``tfoot`` headers and the label/value pairs."""

    def __init__(self):
        super().__init__()
        self.celdas, self.pie, self.pares = [], [], []
        self._cap, self._buf, self._pie, self._etiqueta = None, "", False, None
        self._pend = None

    def handle_starttag(self, tag, attrs):
        clases = dict(attrs).get("class", "") or ""
        if tag == "tfoot":
            self._pie = True
        if tag == "td":
            self._cap, self._buf = "td", ""
        elif tag == "th" and self._pie:
            self._cap, self._buf = "th", ""
        elif tag == "div" and clases == "text-muted small":
            self._cap, self._buf = "label", ""
        elif tag == "div" and self._pend:
            self._cap, self._buf = "value", ""

    def handle_data(self, data):
        if self._cap:
            self._buf += data

    def handle_endtag(self, tag):
        if tag == "tfoot":
            self._pie = False
        if tag == "td" and self._cap == "td":
            self.celdas.append(" ".join(self._buf.split()))
            self._cap = None
        elif tag == "th" and self._cap == "th":
            self.pie.append(" ".join(self._buf.split()))
            self._cap = None
        elif tag == "div" and self._cap == "label":
            self._pend = " ".join(self._buf.split())
            self._cap = None
        elif tag == "div" and self._cap == "value":
            self.pares.append((self._pend, " ".join(self._buf.split())))
            self._pend, self._cap = None, None


def _nativo(client, nombre, *args):
    respuesta = client.get(reverse(nombre, args=args))
    assert respuesta.status_code == 200
    analizador = _Celdas()
    analizador.feed(respuesta.content.decode())
    return respuesta, analizador


# --- List --------------------------------------------------------------------------


def test_list_rows_match_the_native_html(datos):
    client = _cliente(_usuario("fl-paridad", superuser=True))
    centro = datos["centro"]

    respuesta = client.get(_lista(centro.pk))
    _, nativo = _nativo(client, "centrodeinfancia_formulario_listado", centro.pk)

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == "application/json"
    assert respuesta["Cache-Control"] == "private, no-store"
    assert "Cookie" in respuesta["Vary"]
    data = respuesta.json()
    celdas = [
        valor
        for fila in data["rows"]
        for valor in (
            fila["codigo"],
            fila["fecha"],
            fila["respondente"],
            fila["creado"],
            fila["actualizado"],
            "Ver Editar",
        )
    ]
    # The last native cell holds the two action links.
    assert [c for c in nativo.celdas] == celdas
    assert len(data["rows"]) == 2
    assert data["centro"] == {
        "id": centro.pk,
        "nombre": "CDI Girasoles",
        "url": f"/centrodeinfancia/detalle/{centro.pk}",
    }
    assert data["crear_url"] == f"/centrodeinfancia/{centro.pk}/formularios/crear/"
    filas = {fila["id"]: fila for fila in data["rows"]}
    completa = filas[datos["formulario"].pk]
    assert completa["fecha"] == "13/03/2026" and completa["respondente"] == "Ana Pérez"
    vacia = filas[datos["sin_autor"].pk]
    assert vacia["fecha"] == "-" and vacia["respondente"] == "-"
    assert vacia["ver_url"] == (
        f"/centrodeinfancia/{centro.pk}/formularios/{datos['sin_autor'].pk}/"
    )
    assert data["messages"] == []
    assert data["page"]["is_paginated"] is False


def test_list_pagination_follows_the_native_pages(datos):
    for _ in range(12):
        FormularioCDI.objects.create(centro=datos["centro"])
    client = _cliente(_usuario("fl-paginas", superuser=True))
    centro = datos["centro"]

    uno = client.get(_lista(centro.pk)).json()
    dos = client.get(_lista(centro.pk, 2)).json()
    nativo = client.get(
        reverse("centrodeinfancia_formulario_listado", args=[centro.pk]), {"page": 2}
    )

    assert len(uno["rows"]) == 10 and len(dos["rows"]) == 4
    assert uno["page"] == {
        "is_paginated": True,
        "number": 1,
        "count": 14,
        "previous": None,
        "next": 2,
        "range": [1, 2],
    }
    assert dos["page"]["previous"] == 1 and dos["page"]["next"] is None
    assert nativo.context["page_obj"].number == 2
    assert client.get(_lista(centro.pk, 9)).status_code == 404
    assert client.get(_lista(centro.pk, "x")).status_code == 404


def test_list_scope_and_permission(datos):
    user = _usuario("fl-referente")
    AccesoCDI.objects.create(user=user, centro=datos["centro"])
    cliente = _cliente(user)
    sin = _cliente(_usuario("fl-sin", perms=()))
    otro_permiso = _cliente(_usuario("fl-otro", perms=(VER_CENTRO,)))

    assert cliente.get(_lista(datos["centro"].pk)).status_code == 200
    assert cliente.get(_lista(datos["otro"].pk)).status_code == 404
    assert sin.get(_lista(datos["centro"].pk)).status_code == 403
    assert otro_permiso.get(_lista(datos["centro"].pk)).status_code == 403
    assert Client().get(_lista(datos["centro"].pk)).status_code == 401


# --- Detail ---------------------------------------------------------------------------


def test_detail_cells_match_the_native_html(datos):
    client = _cliente(_usuario("fd-paridad", superuser=True))
    centro, formulario = datos["centro"], datos["formulario"]

    respuesta = client.get(_detalle(centro.pk, formulario.pk))
    _, nativo = _nativo(
        client, "centrodeinfancia_formulario_detalle", centro.pk, formulario.pk
    )

    assert respuesta.status_code == 200
    data = respuesta.json()
    assert [(i["label"], i["value"]) for s in data["sections"] for i in s["items"]] == (
        nativo.pares
    )
    assert len(nativo.pares) > 40
    celdas = [c for fila in data["horarios"] + data["salas"]["rows"] for c in fila]
    celdas += [c for fila in data["demanda"]["rows"] for c in fila]
    celdas += [c for fila in data["articulacion"] for c in fila]
    assert nativo.celdas == celdas
    assert nativo.pie == [
        "Totales",
        *data["salas"]["totales"],
        "-",
        "Total",
        data["demanda"]["total"],
    ]
    assert data["horarios"] == [["Lunes", "08:00", "-"]]
    assert data["salas"]["rows"][0][:5] == ["Lactantes", "2", "12,50", "-", "4"]
    assert data["id"] == formulario.pk
    assert data["codigo_cdi"] == "CDI-7"
    assert data["creado_por"] == "Lu Gómez"
    assert data["editar_url"] == (
        f"/centrodeinfancia/{centro.pk}/formularios/{formulario.pk}/editar/"
    )
    assert set(data) == {
        "id",
        "centro",
        "codigo_cdi",
        "creado",
        "creado_por",
        "editar_url",
        "sections",
        "horarios",
        "salas",
        "demanda",
        "articulacion",
        "messages",
    }


def test_detail_without_author_or_rows(datos):
    client = _cliente(_usuario("fd-vacio", superuser=True))

    data = client.get(_detalle(datos["centro"].pk, datos["sin_autor"].pk)).json()

    assert data["creado_por"] is None
    assert data["codigo_cdi"] == "CDI-7"
    assert data["horarios"] == []
    assert data["salas"]["rows"] == [] and data["demanda"]["rows"] == []


def test_detail_scope_nested_ids_and_reads_without_writes(datos):
    user = _usuario("fd-referente")
    AccesoCDI.objects.create(user=user, centro=datos["centro"])
    cliente = _cliente(user)
    centro, otro = datos["centro"], datos["otro"]

    assert cliente.get(_detalle(centro.pk, datos["formulario"].pk)).status_code == 200
    assert cliente.get(_detalle(otro.pk, datos["ajeno"].pk)).status_code == 404
    assert cliente.get(_detalle(centro.pk, datos["ajeno"].pk)).status_code == 404
    assert cliente.get(_detalle(centro.pk, 999999)).status_code == 404
    with CaptureQueriesContext(connection) as queries:
        cliente.get(_detalle(centro.pk, datos["formulario"].pk))
        cliente.get(_lista(centro.pk))
    assert not [
        q["sql"] for q in queries.captured_queries if q["sql"].startswith(WRITES)
    ]


def test_methods_and_admindocs(datos):
    client = _cliente(_usuario("fd-metodos", superuser=True))
    staff = User.objects.create_user("fd-staff", is_staff=True)
    destino = _detalle(datos["centro"].pk, datos["formulario"].pk)

    assert client.post(destino).status_code == 405
    assert client.delete(_lista(datos["centro"].pk)).status_code == 405
    assert client.head(destino).status_code == 200
    respuesta = _cliente(_ready(staff)).head(destino)
    assert "X-View" not in respuesta
    assert respuesta.status_code == 403


def test_pending_requirement_and_forged_header(datos):
    user = _usuario("fd-pendiente", superuser=True)
    user.profile.must_change_password = True
    user.profile.save()
    client = _cliente(user)
    destino = _lista(datos["centro"].pk)
    falso = web_gate.sign(
        audience="cdi",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method="GET",
        target=destino,
    )

    respuesta = client.get(destino, HTTP_X_SISOC_WEB_GATE=falso, RAW_URI=destino)

    assert respuesta.status_code == 403
    assert respuesta.json()["detail"] == web_gate.DETAIL_REQUIREMENT


# --- Runtime: only the core's signed attestation reaches the view -----------------------


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="cdi",
        ROOT_URLCONF="cdi_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, target, *, method="GET", now=None, audience="cdi"):
    return web_gate.sign(
        audience=audience,
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method=method,
        target=target,
        now=now,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_a_signed_request_and_rejects_bad_ones(datos):
    user = _usuario("fd-runtime", superuser=True)
    client = _cliente(user)
    destino = _detalle(datos["centro"].pk, datos["formulario"].pk)
    valido = _signed(user, client, destino)

    ok = client.get(destino, RAW_URI=destino, HTTP_X_SISOC_WEB_GATE=valido)

    assert ok.status_code == 200
    assert ok.json()["id"] == datos["formulario"].pk
    alterados = {
        "missing": None,
        "other_target": _signed(user, client, destino + "?x=1"),
        "other_audience": _signed(user, client, destino, audience="inspecciones"),
        "other_method": _signed(user, client, destino, method="POST"),
        "expired": _signed(user, client, destino, now=timezone.now().timestamp() - 61),
    }
    for motivo, token in alterados.items():
        extra = {"RAW_URI": destino}
        if token is not None:
            extra["HTTP_X_SISOC_WEB_GATE"] = token
        rechazo = client.get(destino, **extra)
        assert rechazo.status_code == 403, motivo
        assert rechazo.json() == {"detail": web_gate.DETAIL_REJECTED}, motivo


@pytest.mark.usefixtures("runtime")
def test_runtime_still_applies_the_view_permission_and_anonymous_is_401(datos):
    destino = _lista(datos["centro"].pk)
    user = _usuario("fd-runtime-sin", perms=())
    client = _cliente(user)

    sin = client.get(
        destino, RAW_URI=destino, HTTP_X_SISOC_WEB_GATE=_signed(user, client, destino)
    )

    assert sin.status_code == 403
    assert sin.json() != {"detail": web_gate.DETAIL_REJECTED}
    assert Client().get(destino, RAW_URI=destino).status_code == 401
