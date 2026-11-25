"""Web API (G1 v1) of the CDI beneficiary detail: ``/api/web/cdi/centros/<pk>/nomina/<id>/``.

Read-only projection of ``NominaCentroInfanciaDestinatariosDetailView``
(CDI04.01) for the React page. Every field is compared with the HTML the
native page renders for the same record.
"""

from datetime import date
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
    NOMINA_ALERGIA_CHOICES,
    TRABAJADOR_GRUPO_PERTENENCIA_CHOICES,
    TRABAJADOR_LENGUAJES_CHOICES,
    TRABAJADOR_TIPO_DISCAPACIDAD_CHOICES,
    AccesoCDI,
    CentroDeInfancia,
    NominaCentroInfancia,
)
from ciudadanos.models import Ciudadano
from core import web_gate
from core.models import Provincia

WRITES = ("INSERT", "UPDATE", "DELETE")
VER = "centrodeinfancia.view_centrodeinfancia"
EDITAR = "centrodeinfancia.change_nominacentroinfancia"

pytestmark = pytest.mark.django_db


def _url(centro_pk, nomina_pk):
    return f"/api/web/cdi/centros/{centro_pk}/nomina/{nomina_pk}/"


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
    user = User.objects.create_user(username=username, is_superuser=superuser)
    for codigo in perms:
        user.user_permissions.add(_permiso(codigo))
    return _ready(user)


def _cliente(user):
    client = Client()
    client.force_login(user)
    return client


def _codigos(choices):
    return [valor for valor, _ in choices][:2]


@pytest.fixture(name="datos")
def datos_fixture():
    provincia = Provincia.objects.create(nombre="Mendoza")
    centro = CentroDeInfancia.objects.create(
        nombre="CDI Girasoles", provincia=provincia
    )
    otro = CentroDeInfancia.objects.create(nombre="CDI Ajeno", provincia=provincia)
    ciudadano = Ciudadano.objects.create(
        apellido="Ramírez", nombre="Sofía", documento=44555666
    )
    ficha = NominaCentroInfancia.objects.create(
        centro=centro,
        ciudadano=ciudadano,
        estado=NominaCentroInfancia.ESTADO_ACTIVO,
        dni=44555666,
        apellido="Ramírez",
        nombre="Sofía",
        fecha_nacimiento=date(2023, 3, 4),
        sin_cuil_nino=True,
        talla=Decimal("85.5"),
        posee_cud=True,
        posee_obra_social=False,
        grupo_pertenencia=_codigos(TRABAJADOR_GRUPO_PERTENENCIA_CHOICES),
        lenguajes=_codigos(TRABAJADOR_LENGUAJES_CHOICES),
        tipo_discapacidad=_codigos(TRABAJADOR_TIPO_DISCAPACIDAD_CHOICES),
        alergias_alimentarias=_codigos(NOMINA_ALERGIA_CHOICES),
        vacunacion_nomivac={
            "bcg": {"dosis": 1, "fecha": "2023-03-05"},
            "varicela": {"dosis": 2},
        },
        observaciones="Primera línea\nSegunda línea",
        responsable_legal_1_apellido="Ramírez",
        responsable_legal_1_sin_cuil=True,
        responsable_legal_1_cuit="20-11111111-2",
    )
    return {"centro": centro, "otro": otro, "ficha": ficha}


class _Pares(HTMLParser):
    """``label``/``value`` pairs of ``_nomina_campo.html``, in page order."""

    def __init__(self):
        super().__init__()
        self.pares, self._modo, self._etiqueta = [], None, None

    def handle_starttag(self, tag, attrs):
        clases = dict(attrs).get("class", "")
        if tag == "p" and clases == "small mb-1":
            self._modo = "label"
        elif tag == "p" and clases == "mb-0" and self._etiqueta is not None:
            self._modo = "value"
            self._valor = ""

    def handle_data(self, data):
        if self._modo == "label":
            self._etiqueta = data.strip()
        elif self._modo == "value":
            self._valor += data

    def handle_endtag(self, tag):
        if tag == "p" and self._modo == "value":
            self.pares.append((self._etiqueta, self._valor.strip()))
            self._etiqueta = None
        if tag == "p":
            self._modo = None


def _nativo(client, centro, ficha):
    respuesta = client.get(
        reverse("centrodeinfancia_nomina_destinatario_ver", args=[centro.pk, ficha.pk])
    )
    assert respuesta.status_code == 200
    analizador = _Pares()
    analizador.feed(respuesta.content.decode())
    return respuesta, analizador.pares


def _campos(data):
    return [
        (item["label"], item["value"])
        for seccion in data["sections"]
        for bloque in seccion["blocks"]
        if bloque["kind"] == "fields"
        for item in bloque["items"]
    ]


# --- Monolith: shape, parity, scope and permissions ---------------------------


def test_every_field_matches_the_native_html(datos):
    client = _cliente(_usuario("web-nomina-paridad", superuser=True))

    respuesta = client.get(_url(datos["centro"].pk, datos["ficha"].pk))
    _, pares = _nativo(client, datos["centro"], datos["ficha"])

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == "application/json"
    assert respuesta["Cache-Control"] == "private, no-store"
    assert "Cookie" in respuesta["Vary"]
    data = respuesta.json()
    assert len(pares) > 60
    assert _campos(data) == pares
    assert data["label"] == "Ramírez, Sofía"
    assert data["centro"] == {
        "id": datos["centro"].pk,
        "nombre": "CDI Girasoles",
        "url": f"/centrodeinfancia/{datos['centro'].pk}/nomina/",
    }
    assert data["messages"] == []
    assert set(data) == {"id", "label", "centro", "editar_url", "sections", "messages"}


def test_sections_follow_the_native_order_and_conditions(datos):
    client = _cliente(_usuario("web-nomina-secciones", superuser=True))

    data = client.get(_url(datos["centro"].pk, datos["ficha"].pk)).json()

    assert [s["key"] for s in data["sections"]] == [
        "registro",
        "nino",
        "responsable1",
        "domicilio",
        "cultura",
        "discapacidad",
        "salud",
        "nutricion",
        "vacunacion",
        "observaciones",
    ]
    assert (
        data["sections"][0]["subtitle"] == "Tipo de registro, fecha y referente del CDI"
    )
    assert data["sections"][3]["subtitle"] is None
    ficha = datos["ficha"]
    ficha.responsable_legal_2_relacion = "madre"
    ficha.observaciones = ""
    ficha.save()
    data = client.get(_url(datos["centro"].pk, ficha.pk)).json()
    claves = [s["key"] for s in data["sections"]]
    assert "responsable2" in claves
    assert "observaciones" not in claves


def test_cuil_flags_chips_vaccines_and_observations(datos):
    client = _cliente(_usuario("web-nomina-detalle", superuser=True))

    data = client.get(_url(datos["centro"].pk, datos["ficha"].pk)).json()

    secciones = {s["key"]: s for s in data["sections"]}
    nino = dict(_campos({"sections": [secciones["nino"]]}))
    assert nino["CUIT"] == "No posee CUIL"
    responsable = dict(_campos({"sections": [secciones["responsable1"]]}))
    assert responsable["CUIT"] == "No posee CUIL"
    nutricion = secciones["nutricion"]["blocks"]
    assert [b["kind"] for b in nutricion] == [
        "fields",
        "badges",
        "rule",
        "caption",
        "fields",
    ]
    assert nutricion[1]["label"] == "Alergias alimentarias"
    assert nutricion[1]["items"] == [
        str(x) for x in datos["ficha"].alergias_alimentarias_display
    ]
    assert [b["tone"] for b in secciones["cultura"]["blocks"][1:]] == [
        "warning",
        "info",
    ]
    assert secciones["discapacidad"]["blocks"][1]["tone"] == "danger"
    # Spacing classes of the native markup: mb-3 rows and the first badge list.
    assert [b["spaced"] for b in secciones["cultura"]["blocks"]] == [True, True, False]
    assert secciones["nino"]["blocks"][0]["spaced"] is False
    assert secciones["vacunacion"]["blocks"] == [
        {
            "kind": "vaccines",
            "rows": [
                {"vaccine": "BCG", "doses": "1", "date": "2023-03-05"},
                {"vaccine": "Varicela", "doses": "2", "date": "—"},
            ],
        }
    ]
    assert secciones["observaciones"]["blocks"] == [
        {"kind": "text", "text": "Primera línea\nSegunda línea"}
    ]
    ficha = datos["ficha"]
    ficha.vacunacion_nomivac = {}
    ficha.save()
    vacia = _cliente(_usuario("web-nomina-vacia", superuser=True)).get(
        _url(datos["centro"].pk, ficha.pk)
    )
    assert vacia.json()["sections"][-2]["blocks"] == [
        {"kind": "vaccines", "rows": None}
    ]


def test_edit_link_only_with_the_native_edit_permission(datos):
    centro, ficha = datos["centro"], datos["ficha"]
    sin = _cliente(_usuario("web-nomina-solo-ver")).get(_url(centro.pk, ficha.pk))
    con = _cliente(_usuario("web-nomina-editor", perms=(VER, EDITAR))).get(
        _url(centro.pk, ficha.pk)
    )

    assert sin.status_code == 200
    assert sin.json()["editar_url"] is None
    assert (
        con.json()["editar_url"]
        == f"/centrodeinfancia/{centro.pk}/nomina/{ficha.pk}/editar/"
    )


def test_scope_and_nested_ids_are_enforced(datos):
    user = _usuario("web-nomina-referente")
    AccesoCDI.objects.create(user=user, centro=datos["centro"])
    cliente = _cliente(user)
    ajeno = NominaCentroInfancia.objects.create(
        centro=datos["otro"],
        ciudadano=Ciudadano.objects.create(apellido="X", nombre="Y", documento=1),
        estado=NominaCentroInfancia.ESTADO_ACTIVO,
    )

    assert cliente.get(_url(datos["centro"].pk, datos["ficha"].pk)).status_code == 200
    # Centre outside the scope, record of another centre and a mixed pair: 404.
    assert cliente.get(_url(datos["otro"].pk, ajeno.pk)).status_code == 404
    assert cliente.get(_url(datos["centro"].pk, ajeno.pk)).status_code == 404
    assert cliente.get(_url(datos["otro"].pk, datos["ficha"].pk)).status_code == 404
    assert cliente.get(_url(datos["centro"].pk, 999999)).status_code == 404
    native = cliente.get(
        reverse(
            "centrodeinfancia_nomina_destinatario_ver",
            args=[datos["centro"].pk, ajeno.pk],
        )
    )
    assert native.status_code == 404


def test_reads_never_write(datos):
    client = _cliente(_usuario("web-nomina-lectura", superuser=True))
    client.get(_url(datos["centro"].pk, datos["ficha"].pk))

    with CaptureQueriesContext(connection) as queries:
        assert (
            client.get(_url(datos["centro"].pk, datos["ficha"].pk)).status_code == 200
        )

    assert not [
        q["sql"] for q in queries.captured_queries if q["sql"].startswith(WRITES)
    ]


def test_anonymous_gets_401_json(datos):
    respuesta = Client().get(_url(datos["centro"].pk, datos["ficha"].pk))

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert respuesta["Cache-Control"] == "private, no-store"


def test_without_the_view_permission_gets_403(datos):
    sin = _usuario("web-nomina-sin-permiso", perms=())
    otro = _usuario(
        "web-nomina-otro-permiso", perms=("centrodeinfancia.view_nominacentroinfancia",)
    )

    for user in (sin, otro):
        respuesta = _cliente(user).get(_url(datos["centro"].pk, datos["ficha"].pk))
        assert respuesta.status_code == 403
        assert respuesta.json() != {"detail": web_gate.DETAIL_REQUIREMENT}


def test_pending_requirement_is_reported_and_a_forged_header_is_ignored(datos):
    user = _usuario("web-nomina-pendiente", superuser=True)
    user.profile.must_change_password = True
    user.profile.save()
    client = _cliente(user)
    destino = _url(datos["centro"].pk, datos["ficha"].pk)
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


def test_only_get_is_served(datos):
    client = _cliente(_usuario("web-nomina-metodos", superuser=True))
    destino = _url(datos["centro"].pk, datos["ficha"].pk)

    assert client.post(destino).status_code == 405
    assert client.delete(destino).status_code == 405
    assert client.head(destino).status_code == 200


def test_admindocs_head_does_not_bypass_the_web_api(datos):
    staff = User.objects.create_user("web-nomina-staff", is_staff=True)
    respuesta = _cliente(_ready(staff)).head(
        _url(datos["centro"].pk, datos["ficha"].pk)
    )

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
    user = _usuario("web-nomina-runtime", superuser=True)
    client = _cliente(user)
    destino = _url(datos["centro"].pk, datos["ficha"].pk)
    valido = _signed(user, client, destino)

    ok = client.get(destino, RAW_URI=destino, HTTP_X_SISOC_WEB_GATE=valido)

    assert ok.status_code == 200
    assert ok.json()["id"] == datos["ficha"].pk
    alterados = {
        "missing": None,
        "other_target": _signed(user, client, destino + "?x=1"),
        "other_audience": _signed(user, client, destino, audience="inspecciones"),
        "other_method": _signed(user, client, destino, method="POST"),
        "expired": _signed(user, client, destino, now=timezone.now().timestamp() - 61),
        "bad_signature": valido[:-2] + ("AA" if not valido.endswith("AA") else "BB"),
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
    destino = _url(datos["centro"].pk, datos["ficha"].pk)
    user = _usuario("web-nomina-runtime-sin", perms=())
    client = _cliente(user)

    sin = client.get(
        destino, RAW_URI=destino, HTTP_X_SISOC_WEB_GATE=_signed(user, client, destino)
    )
    anonimo = Client().get(destino, RAW_URI=destino)

    assert sin.status_code == 403
    assert sin.json() != {"detail": web_gate.DETAIL_REJECTED}
    assert anonimo.status_code == 401
