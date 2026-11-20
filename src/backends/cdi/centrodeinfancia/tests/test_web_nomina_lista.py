"""Web API (G1 v1) of the CDI nómina list and its derivation.

``GET /api/web/cdi/centros/<pk>/nomina/`` projects ``NominaCentroInfanciaDetailView``
(CDI04.02) and ``POST /api/web/cdi/nomina/<pk>/derivar/`` is the native
``nomina_centrodeinfancia_derivar`` behind the G1 gate (CDI04.03). Cells and
metrics are compared with the HTML the native page renders; every rejected
POST is checked against a full snapshot of the nómina and derivation tables.
"""

import re
from datetime import date, timedelta
from html.parser import HTMLParser

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from centrodeinfancia.models import (
    AccesoCDI,
    CentroDeInfancia,
    NominaCentroInfancia,
    NominaCentroInfanciaDerivacion,
)
from ciudadanos.models import Ciudadano
from core import web_gate
from core.models import Provincia, Sexo

WRITES = ("INSERT", "UPDATE", "DELETE")
VER = "centrodeinfancia.view_nominacentroinfancia"
CAMBIAR = "centrodeinfancia.change_nominacentroinfancia"
AGREGAR = "centrodeinfancia.add_nominacentroinfancia"

pytestmark = pytest.mark.django_db


def _lista(pk):
    return f"/api/web/cdi/centros/{pk}/nomina/"


def _derivar(pk):
    return f"/api/web/cdi/nomina/{pk}/derivar/"


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


def _cliente(user, **extra):
    client = Client(**extra)
    client.force_login(user)
    return client


def _ficha(centro, documento, estado=NominaCentroInfancia.ESTADO_ACTIVO, **extra):
    # The native cell reads ``ciudadano.sexo.sexo``: without a sex it raises (as the HTML does).
    ciudadano = Ciudadano.objects.create(
        apellido=f"Apellido{documento}",
        nombre=f"Nombre{documento}",
        documento=documento,
        sexo=Sexo.objects.get_or_create(sexo="Femenino")[0],
    )
    return NominaCentroInfancia.objects.create(
        centro=centro, ciudadano=ciudadano, estado=estado, **extra
    )


@pytest.fixture(name="datos")
def datos_fixture():
    provincia = Provincia.objects.create(nombre="Mendoza")
    centro = CentroDeInfancia.objects.create(
        nombre="CDI Girasoles", provincia=provincia, codigo_cdi="CDI-7"
    )
    destino = CentroDeInfancia.objects.create(nombre="CDI Destino", provincia=provincia)
    ajeno = CentroDeInfancia.objects.create(nombre="CDI Ajeno", provincia=provincia)
    activa = _ficha(
        centro,
        30111222,
        dni=30111222,
        apellido="Ramírez",
        nombre="Sofía",
        sexo="Femenino",
        sala="Sala 1",
        fecha_nacimiento=date.today() - timedelta(days=365 * 3 + 30),
    )
    pendiente = _ficha(
        centro,
        30111223,
        NominaCentroInfancia.ESTADO_PENDIENTE,
        sexo="Masculino",
        sala="Sala 2",
    )
    baja = _ficha(centro, 30111224, NominaCentroInfancia.ESTADO_BAJA)
    return {
        "centro": centro,
        "destino": destino,
        "ajeno": ajeno,
        "activa": activa,
        "pendiente": pendiente,
        "baja": baja,
    }


class _Tabla(HTMLParser):
    """Rows of ``#tablaNomina`` (cell texts, state, room) and the metric numbers."""

    def __init__(self):
        super().__init__()
        self.filas, self.numeros = [], []
        self._en_tabla = self._en_celda = self._en_numero = False
        self._fila = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table" and a.get("id") == "tablaNomina":
            self._en_tabla = True
        elif tag == "tr" and self._en_tabla and "data-estado" in a:
            self._fila = {
                "estado": a["data-estado"],
                "sala": a.get("data-sala", ""),
                "celdas": [],
            }
        elif tag == "td" and self._fila is not None:
            self._en_celda = True
            self._fila["celdas"].append("")
        elif tag == "div" and a.get("class") == "cdi-stat-num":
            self._en_numero = True
            self.numeros.append("")

    def handle_data(self, data):
        if self._en_celda:
            self._fila["celdas"][-1] += data
        elif self._en_numero:
            self.numeros[-1] += data

    def handle_endtag(self, tag):
        if tag == "td":
            self._en_celda = False
        elif tag == "div":
            self._en_numero = False
        elif tag == "tr" and self._fila is not None:
            self.filas.append(self._fila)
            self._fila = None
        elif tag == "table":
            self._en_tabla = False


def _nativo(client, centro, pagina=None):
    url = reverse("centrodeinfancia_nomina_ver", args=[centro.pk])
    respuesta = client.get(url, {"page": pagina} if pagina else {})
    assert respuesta.status_code == 200
    tabla = _Tabla()
    tabla.feed(respuesta.content.decode())
    return tabla


def _estado():
    """Every nómina row (deleted included) plus every derivation row."""
    fichas = list(NominaCentroInfancia.all_objects.order_by("pk").values())
    derivaciones = list(NominaCentroInfanciaDerivacion.objects.order_by("pk").values())
    return fichas, derivaciones


# --- List: parity, scope, permissions -----------------------------------------


def test_rows_and_metrics_match_the_native_html(datos):
    client = _cliente(_usuario("web-nomlis-paridad", superuser=True))
    centro = datos["centro"]

    respuesta = client.get(_lista(centro.pk))
    nativo = _nativo(client, centro)

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == "application/json"
    assert respuesta["Cache-Control"] == "private, no-store"
    assert "Cookie" in respuesta["Vary"]
    data = respuesta.json()
    assert len(nativo.filas) == 3
    for fila, nativa in zip(data["rows"], nativo.filas, strict=True):
        assert fila["estado"] == nativa["estado"]
        assert fila["sala_filtro"] == nativa["sala"]
        textos = [re.sub(r"\s+", " ", c).strip() for c in nativa["celdas"][:7]]
        assert [
            fila["fecha"],
            fila["nombre"],
            fila["dni"],
            fila["sexo"],
            fila["edad"],
            fila["sala"],
        ] == textos[:6]
    stats = data["stats"]
    assert [
        stats["asistentes"],
        stats["hombres"],
        stats["mujeres"],
        stats["x"],
        stats["menores"],
        stats["espera"],
    ] == [n.strip() for n in nativo.numeros]
    assert (stats["asistentes"], stats["espera"], stats["mujeres"]) == ("3", "1", "2")
    assert data["rangos"]["ninos"] == {
        "num": "1",
        "pct": "100",
        "width": 100,
        "zero": False,
    }
    assert data["rangos"]["adultos"] == {
        "num": "0",
        "pct": "0",
        "width": 0,
        "zero": True,
    }
    assert data["centro"] == {
        "id": centro.pk,
        "nombre": "CDI Girasoles",
        "url": f"/centrodeinfancia/detalle/{centro.pk}",
        "codigo_cdi": "CDI-7",
        "ubicacion": "-, Mendoza",
    }
    assert data["urls"]["crear"] == f"/centrodeinfancia/{centro.pk}/nomina/crear/"
    assert data["messages"] == []


def test_row_links_and_derive_targets_follow_the_native_rules(datos):
    client = _cliente(_usuario("web-nomlis-links", superuser=True))
    centro = datos["centro"]

    data = client.get(_lista(centro.pk)).json()

    activa = next(f for f in data["rows"] if f["id"] == datos["activa"].pk)
    assert activa["urls"] == {
        "ver": f"/centrodeinfancia/{centro.pk}/nomina/{activa['id']}/ver/",
        "editar": f"/centrodeinfancia/{centro.pk}/nomina/{activa['id']}/editar/",
        "borrar": f"/centrodeinfancia/{centro.pk}/nomina/{activa['id']}/eliminar/",
    }
    assert activa["derivar_nombre"] == "Sofía Ramírez"
    assert activa["ciudadano_url"] == f"/ciudadanos/ver/{datos['activa'].ciudadano_id}"
    assert [c["nombre"] for c in data["centros_para_derivar"]] == [
        "CDI Ajeno",
        "CDI Destino",
    ]


def test_pagination_keeps_global_metrics_and_an_invalid_page_is_404(datos):
    for numero in range(100):
        _ficha(datos["centro"], 31000000 + numero)
    client = _cliente(_usuario("web-nomlis-paginas", superuser=True))
    centro = datos["centro"]

    primera = client.get(_lista(centro.pk)).json()
    segunda = client.get(_lista(centro.pk), {"page": 2}).json()

    assert len(primera["rows"]) == 100
    assert len(segunda["rows"]) == 3
    assert primera["page"] == {
        "has_other_pages": True,
        "number": 1,
        "num_pages": 2,
        "count": 103,
        "start": 1,
        "end": 100,
        "previous": None,
        "next": 2,
    }
    assert segunda["page"]["previous"] == 1 and segunda["page"]["next"] is None
    assert segunda["stats"] == primera["stats"]
    assert client.get(_lista(centro.pk), {"page": 3}).status_code == 404
    assert client.get(_lista(centro.pk), {"page": "x"}).status_code == 404
    assert _nativo(client, centro, 2).filas[0]["estado"] == segunda["rows"][0]["estado"]


def test_scope_limits_the_centre_and_the_derive_targets(datos):
    user = _usuario("web-nomlis-referente")
    AccesoCDI.objects.create(user=user, centro=datos["centro"])
    client = _cliente(user)

    ok = client.get(_lista(datos["centro"].pk))

    assert ok.status_code == 200
    assert ok.json()["centros_para_derivar"] == []
    assert client.get(_lista(datos["ajeno"].pk)).status_code == 404
    assert client.get(_lista(999999)).status_code == 404


def test_list_reads_never_write(datos):
    client = _cliente(_usuario("web-nomlis-lectura", superuser=True))
    client.get(_lista(datos["centro"].pk))

    with CaptureQueriesContext(connection) as queries:
        assert client.get(_lista(datos["centro"].pk)).status_code == 200

    assert not [
        q["sql"] for q in queries.captured_queries if q["sql"].startswith(WRITES)
    ]


def test_list_needs_the_nomina_permission_and_only_serves_get(datos):
    centro = datos["centro"]
    sin = _usuario("web-nomlis-sin", perms=())
    otro = _usuario(
        "web-nomlis-otro", perms=("centrodeinfancia.view_centrodeinfancia",)
    )
    con = _cliente(_usuario("web-nomlis-con"))
    antes = _estado()

    for user in (sin, otro):
        respuesta = _cliente(user).get(_lista(centro.pk))
        assert respuesta.status_code == 403
        assert respuesta.json() != {"detail": web_gate.DETAIL_REQUIREMENT}
    anonimo = Client().get(_lista(centro.pk))
    assert anonimo.status_code == 401
    assert anonimo.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert con.post(_lista(centro.pk)).status_code == 405
    assert con.head(_lista(centro.pk)).status_code == 200
    assert _estado() == antes


def test_pending_requirement_is_reported_and_a_forged_header_is_ignored(datos):
    user = _usuario("web-nomlis-pendiente", superuser=True)
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


# --- Derivation ----------------------------------------------------------------


def test_derive_persists_the_native_effects_and_answers_the_native_json(datos):
    user = _usuario("web-nomder-ok", perms=(CAMBIAR, AGREGAR), superuser=True)
    client = _cliente(user)
    activa = datos["activa"]

    respuesta = client.post(
        _derivar(activa.pk),
        {"centro_destino_id": datos["destino"].pk, "motivo": "  Mudanza familiar  "},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "success": True,
        "message": "Derivación realizada correctamente.",
    }
    assert respuesta["Cache-Control"] == "private, no-store"
    activa.refresh_from_db()
    assert activa.estado == NominaCentroInfancia.ESTADO_BAJA
    nueva = NominaCentroInfancia.objects.get(
        ciudadano=activa.ciudadano, centro=datos["destino"]
    )
    assert nueva.estado == NominaCentroInfancia.ESTADO_PENDIENTE
    assert nueva.pk != activa.pk
    derivacion = NominaCentroInfanciaDerivacion.objects.get()
    assert (derivacion.nomina_origen_id, derivacion.nomina_destino_id) == (
        activa.pk,
        nueva.pk,
    )
    assert derivacion.centro_origen_id == datos["centro"].pk
    assert derivacion.centro_destino_id == datos["destino"].pk
    assert derivacion.usuario == user
    assert derivacion.motivo == "Mudanza familiar"
    assert NominaCentroInfancia.objects.filter(centro=datos["centro"]).count() == 3


@pytest.mark.parametrize(
    ("cuerpo", "mensaje"),
    [
        ({"centro_destino_id": "", "motivo": "x"}, "Centro destino inválido."),
        ({"centro_destino_id": "abc"}, "Centro destino inválido."),
        ({}, "Centro destino inválido."),
        (
            {"centro_destino_id": 999999},
            "El centro destino no existe o no está dentro de tu alcance.",
        ),
    ],
)
def test_rejected_derivations_answer_400_and_leave_the_data_unchanged(
    datos, cuerpo, mensaje
):
    client = _cliente(_usuario("web-nomder-rechazo", superuser=True))
    antes = _estado()

    respuesta = client.post(_derivar(datos["activa"].pk), cuerpo)

    assert respuesta.status_code == 400
    assert respuesta.json() == {"success": False, "message": mensaje}
    assert _estado() == antes


def test_derive_domain_rejections_leave_the_data_unchanged(datos):
    client = _cliente(_usuario("web-nomder-dominio", superuser=True))
    antes = _estado()

    igual = client.post(
        _derivar(datos["activa"].pk), {"centro_destino_id": datos["centro"].pk}
    )
    no_activa = client.post(
        _derivar(datos["pendiente"].pk), {"centro_destino_id": datos["destino"].pk}
    )
    baja = client.post(
        _derivar(datos["baja"].pk), {"centro_destino_id": datos["destino"].pk}
    )

    assert igual.status_code == 400
    assert igual.json()["message"] == (
        "El centro destino debe ser diferente al centro de origen."
    )
    for respuesta in (no_activa, baja):
        assert respuesta.status_code == 400
        assert respuesta.json() == {
            "success": False,
            "message": "Solo se pueden derivar personas con estado Activo.",
        }
    assert _estado() == antes


def test_derive_is_not_repeatable_after_a_success(datos):
    client = _cliente(_usuario("web-nomder-repite", superuser=True))
    datos_post = {"centro_destino_id": datos["destino"].pk}
    assert client.post(_derivar(datos["activa"].pk), datos_post).status_code == 200
    antes = _estado()

    repetida = client.post(_derivar(datos["activa"].pk), datos_post)

    assert repetida.status_code == 400
    assert repetida.json()["success"] is False
    assert _estado() == antes


def test_derive_to_a_centre_outside_the_scope_or_a_foreign_record_changes_nothing(
    datos,
):
    user = _usuario("web-nomder-alcance", perms=(CAMBIAR, AGREGAR))
    AccesoCDI.objects.create(user=user, centro=datos["centro"])
    client = _cliente(user)
    ajena = _ficha(datos["ajeno"], 32000001)
    antes = _estado()

    fuera = client.post(
        _derivar(datos["activa"].pk), {"centro_destino_id": datos["destino"].pk}
    )
    de_otro = client.post(_derivar(ajena.pk), {"centro_destino_id": datos["centro"].pk})
    inexistente = client.post(_derivar(999999), {"centro_destino_id": 1})

    assert fuera.status_code == 400
    assert fuera.json()["message"] == (
        "El centro destino no existe o no está dentro de tu alcance."
    )
    assert de_otro.status_code == 404
    assert inexistente.status_code == 404
    assert _estado() == antes


def test_derive_needs_change_or_add_permission(datos):
    antes = _estado()
    sin = _cliente(_usuario("web-nomder-sin", perms=(VER,)))
    solo_cambiar = _cliente(_usuario("web-nomder-cambiar", perms=(CAMBIAR,)))
    solo_agregar = _cliente(_usuario("web-nomder-agregar", perms=(AGREGAR,)))
    cuerpo = {"centro_destino_id": datos["destino"].pk}

    rechazada = sin.post(_derivar(datos["activa"].pk), cuerpo)

    assert rechazada.status_code == 403
    assert _estado() == antes
    # The native decorator is "any of": either permission derives, like the URL.
    assert solo_cambiar.post(_derivar(datos["activa"].pk), cuerpo).status_code == 200
    segunda = _ficha(datos["centro"], 33000001)
    assert (
        solo_agregar.post(
            _derivar(segunda.pk), {"centro_destino_id": datos["destino"].pk}
        ).status_code
        == 200
    )


def test_derive_only_accepts_post_csrf_and_a_session(datos):
    superusuario = _usuario("web-nomder-metodos", superuser=True)
    client = _cliente(superusuario)
    estricto = _cliente(superusuario, enforce_csrf_checks=True)
    antes = _estado()
    cuerpo = {"centro_destino_id": datos["destino"].pk}

    get = client.get(_derivar(datos["activa"].pk))
    sin_csrf = estricto.post(_derivar(datos["activa"].pk), cuerpo)
    anonimo = Client().post(_derivar(datos["activa"].pk), cuerpo)

    assert get.status_code == 405
    assert get.json() == {"success": False, "message": "Método no permitido."}
    assert sin_csrf.status_code == 403
    assert anonimo.status_code in (401, 403)
    assert _estado() == antes
    # The native page renders ``{% csrf_token %}``, which is what sets the cookie.
    pagina = estricto.get(
        reverse("centrodeinfancia_nomina_ver", args=[datos["centro"].pk])
    )
    token = pagina.cookies["csrftoken"].value
    con_csrf = estricto.post(
        _derivar(datos["activa"].pk), cuerpo, HTTP_X_CSRFTOKEN=token
    )
    assert con_csrf.status_code == 200


def test_derive_pending_requirement_blocks_before_any_write(datos):
    user = _usuario("web-nomder-pendiente", superuser=True)
    user.profile.must_change_password = True
    user.profile.save()
    antes = _estado()

    respuesta = _cliente(user).post(
        _derivar(datos["activa"].pk), {"centro_destino_id": datos["destino"].pk}
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["detail"] == web_gate.DETAIL_REQUIREMENT
    assert _estado() == antes


# --- Runtime: only the core's signed attestation reaches the views -----------


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="cdi",
        ROOT_URLCONF="cdi_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, *, target, method):
    return web_gate.sign(
        audience="cdi",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method=method,
        target=target,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_accepts_a_signed_derivation_and_rejects_an_unsigned_one(datos):
    user = _usuario("web-nomder-runtime", perms=(CAMBIAR, AGREGAR))
    client = _cliente(user)
    target = _derivar(datos["activa"].pk)
    cuerpo = {"centro_destino_id": datos["destino"].pk}
    antes = _estado()

    sin_firma = client.post(target, cuerpo, RAW_URI=target)
    firma_get = client.post(
        target,
        cuerpo,
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(user, client, target=target, method="GET"),
    )
    assert sin_firma.status_code == 403
    assert firma_get.status_code == 403
    assert _estado() == antes

    firmada = client.post(
        target,
        cuerpo,
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(user, client, target=target, method="POST"),
    )
    assert firmada.status_code == 200
    assert NominaCentroInfanciaDerivacion.objects.count() == 1


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_the_list_only_with_a_valid_attestation(datos):
    user = _usuario("web-nomlis-runtime")
    client = _cliente(user)
    target = _lista(datos["centro"].pk)

    sin_firma = client.get(target, RAW_URI=target)
    firmada = client.get(
        target,
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(user, client, target=target, method="GET"),
    )

    assert sin_firma.status_code == 403
    assert firmada.status_code == 200
    assert len(firmada.json()["rows"]) == 3
