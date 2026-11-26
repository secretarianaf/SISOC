"""Web API (G1 v1) of the CDI worker detail: ``/api/web/cdi/centros/<pk>/trabajadores/<id>/``.

Read-only projection of ``TrabajadorCentroInfanciaDetailView`` (CDI05) for the
React page. Every field is compared with the HTML the native page renders.
"""

from datetime import date
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
    TRABAJADOR_CAPACITACIONES_CHOICES,
    TRABAJADOR_GRUPO_PERTENENCIA_CHOICES,
    TRABAJADOR_LENGUAJES_CHOICES,
    TRABAJADOR_TIPO_DISCAPACIDAD_CHOICES,
    AccesoCDI,
    CentroDeInfancia,
    Trabajador,
)
from core import web_gate
from core.constants import UserGroups
from core.models import Provincia

WRITES = ("INSERT", "UPDATE", "DELETE")
VER = "centrodeinfancia.view_trabajador"
VER_CENTRO = "centrodeinfancia.view_centrodeinfancia"
EDITAR = "centrodeinfancia.change_trabajador"
ELIMINAR = "centrodeinfancia.delete_trabajador"

pytestmark = pytest.mark.django_db


def _url(centro_pk, trabajador_pk):
    return f"/api/web/cdi/centros/{centro_pk}/trabajadores/{trabajador_pk}/"


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


# Por defecto SIMEPI Equipo Nacional: está en la regla de la Fuerza de Trabajo
# (#2943) con alcance nacional y no suma permisos de edición.
def _usuario(
    username,
    *,
    perms=(VER,),
    superuser=False,
    grupos=(UserGroups.SIMEPI_EQUIPO_NACIONAL,),
):
    user = User.objects.create_user(username=username, is_superuser=superuser)
    for codigo in perms:
        user.user_permissions.add(_permiso(codigo))
    for nombre in grupos:
        user.groups.add(Group.objects.get_or_create(name=nombre)[0])
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
        nombre="CDI Girasoles", provincia=provincia, codigo_cdi="CDI-7"
    )
    otro = CentroDeInfancia.objects.create(nombre="CDI Ajeno", provincia=provincia)
    trabajador = Trabajador.objects.create(
        centro=centro,
        nombre="Lucía",
        apellido="Gómez",
        fecha_carga=date(2026, 9, 1),
        fecha_nacimiento=date(1990, 5, 6),
        subcomponente="cdi",
        dni=30111222,
        sin_cuil=True,
        email="lucia@example.test",
        capacitaciones_certificadas=_codigos(TRABAJADOR_CAPACITACIONES_CHOICES),
        grupo_pertenencia=_codigos(TRABAJADOR_GRUPO_PERTENENCIA_CHOICES),
        lenguajes=_codigos(TRABAJADOR_LENGUAJES_CHOICES),
        tipo_discapacidad=_codigos(TRABAJADOR_TIPO_DISCAPACIDAD_CHOICES),
        numero_cud="12345",
    )
    ajeno = Trabajador.objects.create(centro=otro, nombre="Otra", apellido="Persona")
    return {"centro": centro, "otro": otro, "trabajador": trabajador, "ajeno": ajeno}


class _Pares(HTMLParser):
    """``label``/``value`` pairs of ``_trabajador_campo.html``, in page order."""

    def __init__(self):
        super().__init__()
        self.pares, self._modo, self._etiqueta, self._valor = [], None, None, ""

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


def _nativo(client, centro, trabajador):
    respuesta = client.get(
        reverse("centrodeinfancia_trabajador_ver", args=[centro.pk, trabajador.pk])
    )
    assert respuesta.status_code == 200
    analizador = _Pares()
    analizador.feed(respuesta.content.decode())
    return analizador.pares


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
    client = _cliente(_usuario("web-trab-paridad", superuser=True))

    respuesta = client.get(_url(datos["centro"].pk, datos["trabajador"].pk))
    pares = _nativo(client, datos["centro"], datos["trabajador"])

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == "application/json"
    assert respuesta["Cache-Control"] == "private, no-store"
    assert "Cookie" in respuesta["Vary"]
    data = respuesta.json()
    assert len(pares) > 35
    assert _campos(data) == pares
    assert data["label"] == "Gómez, Lucía"
    assert data["centro"] == {
        "id": datos["centro"].pk,
        "nombre": "CDI Girasoles",
        "url": f"/centrodeinfancia/detalle/{datos['centro'].pk}",
    }
    assert data["messages"] == []
    assert set(data) == {
        "id",
        "label",
        "centro",
        "editar_url",
        "eliminar_url",
        "sections",
        "messages",
    }


def test_sections_chips_and_cuil_flag_follow_the_native_markup(datos):
    client = _cliente(_usuario("web-trab-secciones", superuser=True))

    data = client.get(_url(datos["centro"].pk, datos["trabajador"].pk)).json()

    assert [s["key"] for s in data["sections"]] == [
        "institucion",
        "fuerza_trabajo",
        "formacion",
        "contratacion",
        "contacto",
        "identidad",
        "discapacidad",
    ]
    secciones = {s["key"]: s for s in data["sections"]}
    fuerza = dict(_campos({"sections": [secciones["fuerza_trabajo"]]}))
    assert fuerza["CUIT"] == "No posee CUIL"
    trabajador = datos["trabajador"]
    formacion = secciones["formacion"]["blocks"][1]
    assert formacion == {
        "kind": "badges",
        "label": "Capacitaciones certificadas (últimos tres años)",
        "tone": "warning",
        "items": [str(x) for x in trabajador.capacitaciones_certificadas_display],
        "wrapper": "mt-3",
    }
    identidad = secciones["identidad"]["blocks"]
    assert [b["spaced"] for b in identidad if b["kind"] == "fields"] == [True]
    assert [(b["tone"], b["wrapper"]) for b in identidad[1:]] == [
        ("warning", "mb-3"),
        ("info", ""),
    ]
    discapacidad = secciones["discapacidad"]["blocks"]
    assert discapacidad[0]["spaced"] is True
    assert (discapacidad[1]["tone"], discapacidad[1]["wrapper"]) == ("danger", "")
    Trabajador.objects.filter(pk=trabajador.pk).update(
        capacitaciones_certificadas=[],
        grupo_pertenencia=[],
        lenguajes=[],
        tipo_discapacidad=[],
        sin_cuil=False,
        cuit="20-11111111-2",
    )
    vacio = client.get(_url(datos["centro"].pk, trabajador.pk)).json()
    assert not [
        b for s in vacio["sections"] for b in s["blocks"] if b["kind"] == "badges"
    ]
    assert dict(_campos(vacio))["CUIT"] == "20-11111111-2"


def test_edit_and_delete_links_follow_the_native_permissions(datos):
    centro, trabajador = datos["centro"], datos["trabajador"]
    sin = _cliente(_usuario("web-trab-solo-ver")).get(_url(centro.pk, trabajador.pk))
    con = _cliente(_usuario("web-trab-gestor", perms=(VER, EDITAR, ELIMINAR))).get(
        _url(centro.pk, trabajador.pk)
    )

    assert sin.status_code == 200
    assert sin.json()["editar_url"] is None
    assert sin.json()["eliminar_url"] is None
    assert (
        con.json()["editar_url"]
        == f"/centrodeinfancia/{centro.pk}/trabajadores/{trabajador.pk}/editar/"
    )
    assert con.json()["eliminar_url"] == (
        f"/api/web/cdi/centros/{centro.pk}/trabajadores/{trabajador.pk}/eliminar/"
    )


def test_scope_and_nested_ids_are_enforced(datos):
    user = _usuario("web-trab-referente", grupos=[UserGroups.CDI_REFERENTE_CENTRO])
    AccesoCDI.objects.create(user=user, centro=datos["centro"])
    cliente = _cliente(user)

    assert (
        cliente.get(_url(datos["centro"].pk, datos["trabajador"].pk)).status_code == 200
    )
    # Centre outside the scope, worker of another centre and a mixed pair: 404.
    assert cliente.get(_url(datos["otro"].pk, datos["ajeno"].pk)).status_code == 404
    assert cliente.get(_url(datos["centro"].pk, datos["ajeno"].pk)).status_code == 404
    assert (
        cliente.get(_url(datos["otro"].pk, datos["trabajador"].pk)).status_code == 404
    )
    assert cliente.get(_url(datos["centro"].pk, 999999)).status_code == 404
    native = cliente.get(
        reverse(
            "centrodeinfancia_trabajador_ver",
            args=[datos["centro"].pk, datos["ajeno"].pk],
        )
    )
    assert native.status_code == 404


def test_reads_never_write(datos):
    client = _cliente(_usuario("web-trab-lectura", superuser=True))
    client.get(_url(datos["centro"].pk, datos["trabajador"].pk))

    with CaptureQueriesContext(connection) as queries:
        assert (
            client.get(_url(datos["centro"].pk, datos["trabajador"].pk)).status_code
            == 200
        )

    assert not [
        q["sql"] for q in queries.captured_queries if q["sql"].startswith(WRITES)
    ]


def test_anonymous_gets_401_json(datos):
    respuesta = Client().get(_url(datos["centro"].pk, datos["trabajador"].pk))

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert respuesta["Cache-Control"] == "private, no-store"


def test_without_the_view_permission_gets_403(datos):
    sin = _usuario("web-trab-sin-permiso", perms=(), grupos=())
    otro = _usuario("web-trab-otro-permiso", perms=(VER_CENTRO,), grupos=())

    for user in (sin, otro):
        respuesta = _cliente(user).get(_url(datos["centro"].pk, datos["trabajador"].pk))
        assert respuesta.status_code == 403
        assert respuesta.json() != {"detail": web_gate.DETAIL_REQUIREMENT}


def test_pending_requirement_is_reported_and_a_forged_header_is_ignored(datos):
    user = _usuario("web-trab-pendiente", superuser=True)
    user.profile.must_change_password = True
    user.profile.save()
    client = _cliente(user)
    destino = _url(datos["centro"].pk, datos["trabajador"].pk)
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
    client = _cliente(_usuario("web-trab-metodos", superuser=True))
    destino = _url(datos["centro"].pk, datos["trabajador"].pk)

    assert client.post(destino).status_code == 405
    assert client.delete(destino).status_code == 405
    assert client.head(destino).status_code == 200


def test_admindocs_head_does_not_bypass_the_web_api(datos):
    staff = User.objects.create_user("web-trab-staff", is_staff=True)
    respuesta = _cliente(_ready(staff)).head(
        _url(datos["centro"].pk, datos["trabajador"].pk)
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
    user = _usuario("web-trab-runtime", superuser=True)
    client = _cliente(user)
    destino = _url(datos["centro"].pk, datos["trabajador"].pk)
    valido = _signed(user, client, destino)

    ok = client.get(destino, RAW_URI=destino, HTTP_X_SISOC_WEB_GATE=valido)

    assert ok.status_code == 200
    assert ok.json()["id"] == datos["trabajador"].pk
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
    destino = _url(datos["centro"].pk, datos["trabajador"].pk)
    user = _usuario("web-trab-runtime-sin", perms=(), grupos=())
    client = _cliente(user)

    sin = client.get(
        destino, RAW_URI=destino, HTTP_X_SISOC_WEB_GATE=_signed(user, client, destino)
    )
    anonimo = Client().get(destino, RAW_URI=destino)

    assert sin.status_code == 403
    assert sin.json() != {"detail": web_gate.DETAIL_REJECTED}
    assert anonimo.status_code == 401
