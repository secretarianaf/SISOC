"""Web API (G1 v1) of the CDI centre detail / legajo and its two native writes.

``GET /api/web/cdi/centros/<pk>/`` projects ``CentroDeInfanciaDetailView``
(CDI09.01); the user status change and the worker soft delete are the native
views behind the G1 gate. Info fields and metrics are compared with the HTML the
native page renders; every rejected write is checked against a full snapshot of
the access, worker and audit tables.
"""

import re
from datetime import date, time, timedelta
from html.parser import HTMLParser
from urllib.parse import urlencode

import pytest
from auditlog.models import LogEntry
from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from centrodeinfancia.models import (
    AccesoCDI,
    CentroDeInfancia,
    CentroDeInfanciaHorarioFuncionamiento,
    DepartamentoIpi,
    NominaCentroInfancia,
    ObservacionCentroInfancia,
    Trabajador,
)
from ciudadanos.models import Ciudadano
from core import web_gate
from core.constants import UserGroups
from core.models import Municipio, Provincia, Sexo

API = "/api/web/cdi/"
WRITES = ("INSERT", "UPDATE", "DELETE")
VER = "centrodeinfancia.view_centrodeinfancia"
BAJA_TRABAJADOR = "centrodeinfancia.delete_trabajador"
EDITAR_TRABAJADOR = "centrodeinfancia.change_trabajador"
VETO = "El rol Auditoría tiene acceso de solo lectura."

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return User.objects.get(pk=user.pk)


def _usuario(username, *, perms=(VER,), grupos=(), superuser=False, **extra):
    user = User.objects.create_user(
        username=username,
        first_name=extra.pop("first_name", "Ana"),
        last_name=extra.pop("last_name", "Operadora"),
        is_superuser=superuser,
        **extra,
    )
    for code in perms:
        app, codename = code.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    for nombre in grupos:
        user.groups.add(Group.objects.get_or_create(name=nombre)[0])
    return _ready(user)


class WebClient(Client):
    """Posts URL-encoded to the web API, as the React page does."""

    def post(self, path, data=None, content_type=None, **extra):
        if content_type is None and str(path).startswith(API):
            return super().post(
                path,
                urlencode(data or {}),
                content_type="application/x-www-form-urlencoded",
                **extra,
            )
        return super().post(path, data, **extra)


def _cliente(user):
    client = WebClient()
    client.force_login(user)
    return client


def _detalle(pk, **params):
    return f"{API}centros/{pk}/" + (f"?{urlencode(params)}" if params else "")


def _estado_url(pk, acceso):
    return f"{API}centros/{pk}/usuarios/{acceso}/estado/"


def _baja_url(pk, trabajador):
    return f"{API}centros/{pk}/trabajadores/{trabajador}/eliminar/"


@pytest.fixture(name="datos")
def datos_fixture():
    provincia = Provincia.objects.create(nombre="Mendoza")
    departamento = DepartamentoIpi.objects.create(
        codigo_departamento="50001",
        nombre="Godoy Cruz",
        provincia=provincia,
        decil_ipi=4,
    )
    municipio = Municipio.objects.create(nombre="Godoy Cruz", provincia=provincia)
    centro = CentroDeInfancia.objects.create(
        nombre="CDI Girasoles & Co",
        codigo_cdi="CDI-7",
        organizacion="Fundación Sol",
        cuit_organizacion_gestiona="30712345678",
        provincia=provincia,
        departamento=departamento,
        municipio=municipio,
        calle="San Martín",
        numero="123",
        telefono="261555",
        latitud=-32.5,
        longitud=-68.8,
        mail="cdi@example.test",
        nombre_referente="Rosa",
        apellido_referente="Pérez",
        email_referente="rosa@example.test",
        telefono_referente="261777",
        meses_funcionamiento=["1", "2"],
        dias_funcionamiento=["lunes", "martes"],
        tipo_jornada="otra",
        tipo_jornada_otra="Mixta",
        fecha_inicio=date(2019, 1, 1),
    )
    CentroDeInfanciaHorarioFuncionamiento.objects.create(
        centro=centro, dia="lunes", hora_apertura=time(8), hora_cierre=time(16, 30)
    )
    ajeno = CentroDeInfancia.objects.create(nombre="CDI Ajeno", provincia=provincia)
    sexo = Sexo.objects.get_or_create(sexo="Femenino")[0]
    for numero in range(3):
        ciudadano = Ciudadano.objects.create(
            apellido=f"Ap{numero}", nombre="No", documento=50000 + numero, sexo=sexo
        )
        NominaCentroInfancia.objects.create(
            centro=centro,
            ciudadano=ciudadano,
            estado=NominaCentroInfancia.ESTADO_ACTIVO,
            fecha_nacimiento=date.today() - timedelta(days=365 * 3),
        )
    trabajador = Trabajador.objects.create(
        centro=centro,
        nombre="Lucía",
        apellido="Gómez",
        fecha_carga=date(2026, 9, 1),
        subcomponente="PFPI",
    )
    ajeno_trabajador = Trabajador.objects.create(
        centro=ajeno, nombre="Otro", apellido="Ajeno"
    )
    for numero in range(7):
        ObservacionCentroInfancia.objects.create(
            centro=centro,
            observador="Obs <b>" if numero == 0 else f"Obs {numero}",
            observacion=("x" * 100) if numero == 0 else f"Texto {numero}",
            fecha_visita=timezone.now() - timedelta(days=numero),
        )
    return {
        "centro": centro,
        "ajeno": ajeno,
        "trabajador": trabajador,
        "ajeno_trabajador": ajeno_trabajador,
    }


def _acceso(centro, username, *, responsable=False, estado="activo", **extra):
    user = User.objects.create_user(
        username=username,
        first_name="Ref",
        last_name=username,
        email=f"{username}@x.test",
    )
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="centrodeinfancia", codename="view_centrodeinfancia"
        )
    )
    user.profile.temporary_password_plaintext = f"Temp-{username}"
    user.profile.save()
    acceso = AccesoCDI.objects.create(
        user=user, centro=centro, es_responsable=responsable, estado=estado, **extra
    )
    return acceso


class _Native(HTMLParser):
    """Label/value pairs of ``.cdf-info-item`` and the hero/metric numbers."""

    def __init__(self):
        super().__init__()
        self.pares, self.hero, self.metricas = [], [], []
        self._pila = []
        self._texto = {}

    def handle_starttag(self, tag, attrs):
        clase = dict(attrs).get("class", "")
        for objetivo in ("cdf-info-label", "cdf-info-value", "cdi-stat-num"):
            if tag == "div" and objetivo in clase.split():
                self._pila.append(objetivo)
                self._texto[objetivo] = ""
                return
        if tag == "b" and not self._pila:
            self._pila.append("hero")
            self._texto["hero"] = ""

    def handle_data(self, data):
        for clave in list(self._texto):
            if self._pila and self._pila[-1] == clave:
                self._texto[clave] += data

    def handle_endtag(self, tag):
        if not self._pila or tag not in ("div", "b"):
            return
        clave = self._pila.pop()
        texto = re.sub(r"\s+", " ", self._texto.pop(clave)).strip()
        if clave == "cdf-info-label":
            self.pares.append([texto, None])
        elif clave == "cdf-info-value":
            self.pares[-1][1] = texto
        elif clave == "cdi-stat-num":
            self.metricas.append(texto)
        else:
            self.hero.append(texto)


def _nativo(client, centro):
    respuesta = client.get(reverse("centrodeinfancia_detalle", args=[centro.pk]))
    assert respuesta.status_code == 200
    parser = _Native()
    parser.feed(respuesta.content.decode())
    return parser


def _estado():
    accesos = list(AccesoCDI.objects.order_by("pk").values())
    trabajadores = list(Trabajador.all_objects.order_by("pk").values())
    return accesos, trabajadores, LogEntry.objects.count()


def _mensajes(client, centro_pk):
    return [m["message"] for m in client.get(_detalle(centro_pk)).json()["messages"]]


# --- Read: parity, scope, permissions -----------------------------------------


def test_info_fields_and_metrics_match_the_native_html(datos):
    client = _cliente(_usuario("leg-paridad", superuser=True))
    centro = datos["centro"]

    respuesta = client.get(_detalle(centro.pk))
    nativo = _nativo(client, centro)

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == "application/json"
    assert respuesta["Cache-Control"] == "private, no-store"
    assert "Cookie" in respuesta["Vary"]
    data = respuesta.json()
    pares = [
        [item["label"], item["value"]]
        for item in (
            data["general"]
            + [{"label": "Nombre y apellido", "value": data["referente"]["nombre"]}]
            + data["referente"]["items"]
            + data["funcionamiento"]["items"]
        )
    ]
    esperado = [
        (etiqueta, valor) for etiqueta, valor in nativo.pares if valor is not None
    ]
    horarios = next(v for e, v in esperado if e == "Horarios por día")
    assert horarios == "Lunes: 08:00 a 16:30"
    assert [tuple(par) for par in pares] == [
        par for par in esperado if par[0] != "Horarios por día"
    ]
    assert data["funcionamiento"]["horarios"] == [
        {"dia": "Lunes", "apertura": "08:00", "cierre": "16:30"}
    ]
    assert data["mapa"] == (
        "https://maps.google.com/maps?q=San+Mart%C3%ADn%2C+123%2C+Godoy+Cruz%2C"
        "+Mendoza&output=embed"
    )
    assert data["mapa"] in client.get(
        reverse("centrodeinfancia_detalle", args=[centro.pk])
    ).content.decode().replace("&amp;", "&")
    assert data["hero"] == {
        "nomina": 3,
        "trabajadores": 1,
        "formularios": None,
        "anio_inicio": "2019",
    }
    assert [str(data["hero"]["nomina"]), "1", "2019"] == nativo.hero[:3]
    nomina = data["nomina"]
    assert [nomina[k] for k in ("hombres", "mujeres", "x", "menores")] == [
        int(n) for n in nativo.metricas
    ]
    assert (nomina["mujeres"], nomina["menores"]) == (3, 3)
    assert data["centro"]["codigo_cdi"] == "CDI-7"
    assert data["messages"] == []


def test_observations_page_of_five_with_native_cells_and_page_links(datos):
    client = _cliente(_usuario("leg-obs", superuser=True))
    centro = datos["centro"]

    primera = client.get(_detalle(centro.pk)).json()["observaciones"]
    segunda = client.get(_detalle(centro.pk, observaciones_page=2, otro="a b")).json()[
        "observaciones"
    ]
    invalida = client.get(_detalle(centro.pk, observaciones_page="zzz"))

    assert len(primera["filas"]) == 5
    assert primera["paginated"] is True
    assert (primera["number"], primera["previous"], primera["next"]) == (1, None, 2)
    assert primera["range"] == [1, 2]
    assert primera["count"] == 7
    assert primera["filas"][0]["observador"] == "Obs <b>"
    assert primera["filas"][0]["texto"] == "x" * 79 + "…"
    assert re.fullmatch(r"\d\d/\d\d/\d{4} \d\d:\d\d", primera["filas"][0]["fecha"])
    assert primera["filas"][0]["ver"].startswith("/centrodeinfancia/observacion/")
    assert len(segunda["filas"]) == 2
    assert (segunda["previous"], segunda["next"]) == (1, None)
    assert segunda["query_prefix"] == "otro=a%20b&"
    assert invalida.status_code == 200
    assert invalida.json()["observaciones"]["number"] == 1  # Django get_page falls back
    assert primera["crear_url"] == f"{API}centros/{centro.pk}/observaciones/crear/"


def test_empty_observations_omit_the_total_like_the_native_component(datos):
    client = _cliente(_usuario("leg-vacio", superuser=True))
    centro = datos["ajeno"]

    nativo = client.get(reverse("centrodeinfancia_detalle", args=[centro.pk]))
    data = client.get(_detalle(centro.pk)).json()["observaciones"]

    assert "Se encontraron" not in nativo.content.decode()
    assert (data["filas"], data["count"], data["paginated"]) == ([], None, False)


def test_workers_and_actions_follow_the_native_permissions(datos):
    centro = datos["centro"]
    # Equipo Nacional: ve la Fuerza de Trabajo (#2943); las acciones siguen
    # dependiendo del permiso.
    en = [UserGroups.SIMEPI_EQUIPO_NACIONAL]
    solo = _cliente(_usuario("leg-trab-solo", grupos=en))
    todo = _cliente(
        _usuario(
            "leg-trab-todo",
            perms=(VER, EDITAR_TRABAJADOR, BAJA_TRABAJADOR),
            grupos=en,
        )
    )

    sin = solo.get(_detalle(centro.pk)).json()["trabajadores"]
    con = todo.get(_detalle(centro.pk)).json()["trabajadores"]

    fila = sin["filas"][0]
    assert fila["nombre"] == "Gómez, Lucía"
    assert fila["fecha_carga"] == "1 Set. 2026"  # as {{ fecha_carga }} localizes it
    assert (fila["editar"], fila["eliminar"], sin["crear_url"]) == (None, None, None)
    fila = con["filas"][0]
    assert fila["editar"].endswith(f"/trabajadores/{datos['trabajador'].pk}/editar/")
    assert fila["eliminar"] == _baja_url(centro.pk, datos["trabajador"].pk)
    assert con["crear_url"].endswith(f"/{centro.pk}/trabajadores/crear/")


def test_users_table_follows_the_native_per_row_credential_rule(datos):
    centro = datos["centro"]
    propio = _acceso(centro, "leg-resp", responsable=True)
    otro = _acceso(centro, "leg-otro")
    susp = _acceso(centro, "leg-susp", estado="suspendido", motivo_estado="Licencia")
    cambiada = _acceso(centro, "leg-cambiada")
    cambiada.user.profile.temporary_password_plaintext = ""
    cambiada.user.profile.save()

    super_data = (
        _cliente(_usuario("leg-super", superuser=True))
        .get(_detalle(centro.pk))
        .json()["usuarios"]
    )
    resp = _cliente(
        _usuario("leg-resp-cliente", perms=(VER,))
    )  # not linked: sees nothing
    resp_data = resp.get(_detalle(centro.pk)).json()["usuarios"]
    propia = _cliente(User.objects.get(pk=propio.user_id))
    propia_data = propia.get(_detalle(centro.pk)).json()

    assert resp_data is None
    filas = {f["username"]: f for f in super_data["filas"]}
    assert list(filas)[0] == "leg-resp"  # responsible first
    assert filas["leg-resp"]["responsable"] is True
    assert filas["leg-otro"]["password"] == {"kind": "value", "value": "Temp-leg-otro"}
    assert filas["leg-cambiada"]["password"]["kind"] == "changed"
    assert filas["leg-susp"]["estado"] == "suspendido"
    assert filas["leg-susp"]["motivo"] == "Licencia"
    assert filas["leg-resp"]["acciones"] is None
    assert filas["leg-otro"]["acciones"] == {
        "activo": True,
        "usuario": "Ref leg-otro",
        "url": _estado_url(centro.pk, otro.pk),
    }
    assert filas["leg-susp"]["acciones"]["activo"] is False
    assert super_data["credenciales"] and super_data["administrar"]
    # The linked responsible account administers, but only reads her own password.
    pf = {f["username"]: f for f in propia_data["usuarios"]["filas"]}
    assert pf["leg-resp"]["password"]["kind"] == "value"
    assert pf["leg-otro"]["password"]["kind"] == "unavailable"
    assert pf["leg-resp"]["acciones"] is None
    assert susp.pk and cambiada.pk


def test_non_admin_linked_user_sees_only_his_own_row_without_actions(datos):
    centro = datos["centro"]
    _acceso(centro, "leg-resp2", responsable=True)
    simple = _acceso(centro, "leg-simple")

    data = _cliente(User.objects.get(pk=simple.user_id)).get(_detalle(centro.pk))

    assert data.status_code == 200
    usuarios = data.json()["usuarios"]
    assert [f["username"] for f in usuarios["filas"]] == ["leg-simple"]
    assert usuarios["administrar"] is False
    assert "acciones" not in usuarios["filas"][0]
    assert usuarios["generar_url"] is None


def test_scope_permission_and_methods(datos):
    centro = datos["centro"]
    egp = _cliente(_usuario("leg-egp", grupos=[UserGroups.SIMEPI_EGP]))
    sin = _cliente(_usuario("leg-sin", perms=()))
    con = _cliente(_usuario("leg-con"))
    antes = _estado()

    assert egp.get(_detalle(centro.pk)).status_code == 404
    assert con.get(_detalle(999999)).status_code == 404
    assert sin.get(_detalle(centro.pk)).status_code == 403
    anonimo = Client().get(_detalle(centro.pk))
    assert anonimo.status_code == 401
    assert anonimo.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert con.post(_detalle(centro.pk)).status_code == 405
    assert con.head(_detalle(centro.pk)).status_code == 200
    assert _estado() == antes


def test_read_never_writes_and_a_forged_gate_header_is_ignored(datos):
    user = _usuario("leg-lectura", superuser=True)
    client = _cliente(user)
    centro = datos["centro"]

    with CaptureQueriesContext(connection) as queries:
        assert client.get(_detalle(centro.pk)).status_code == 200
    assert not [
        q["sql"] for q in queries.captured_queries if q["sql"].startswith(WRITES)
    ]

    pendiente = _usuario("leg-pendiente", superuser=True)
    pendiente.profile.must_change_password = True
    pendiente.profile.save()
    cliente = _cliente(pendiente)
    destino = _detalle(centro.pk)
    falso = web_gate.sign(
        audience="cdi",
        user_pk=pendiente.pk,
        session_key=cliente.cookies[settings.SESSION_COOKIE_NAME].value,
        method="GET",
        target=destino,
    )
    respuesta = cliente.get(destino, HTTP_X_SISOC_WEB_GATE=falso, RAW_URI=destino)
    assert respuesta.status_code == 403
    assert respuesta.json()["detail"] == web_gate.DETAIL_REQUIREMENT


@override_settings(CDI_INTERVENCIONES_VISIBLE=True)
def test_interventions_flag_keeps_the_native_page(datos):
    client = _cliente(_usuario("leg-flag", superuser=True))

    assert client.get(_detalle(datos["centro"].pk)).status_code == 409


@override_settings(CDI_FORMULARIOS_VISIBLE=True)
def test_forms_card_follows_the_flag_and_the_permission(datos):
    centro = datos["centro"]
    visible = _cliente(
        _usuario(
            "leg-form",
            perms=(VER, "centrodeinfancia.view_formulariocdi"),
        )
    )
    oculto = _cliente(_usuario("leg-noform"))

    data = visible.get(_detalle(centro.pk)).json()

    assert data["hero"]["formularios"] == 0
    assert data["formularios"]["filas"] == []
    assert data["formularios"]["crear_url"] is None
    assert oculto.get(_detalle(centro.pk)).json()["formularios"] is None


# --- Native writes --------------------------------------------------------------


def test_suspend_reactivate_and_baja_persist_the_native_effects(datos):
    centro = datos["centro"]
    admin = _cliente(_usuario("leg-admin", superuser=True))
    acceso = _acceso(centro, "leg-objetivo")

    respuesta = admin.post(
        _estado_url(centro.pk, acceso.pk),
        {"accion": "suspender", "motivo": " Licencia "},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/centrodeinfancia/detalle/{centro.pk}#usuarios",
    }
    assert respuesta["Cache-Control"] == "private, no-store"
    acceso.refresh_from_db()
    assert (acceso.estado, acceso.motivo_estado, acceso.activo) == (
        "suspendido",
        "Licencia",
        False,
    )
    assert acceso.fecha_baja is None
    assert _mensajes(admin, centro.pk) == ["Usuario «leg-objetivo» suspendido."]

    assert (
        admin.post(
            _estado_url(centro.pk, acceso.pk), {"accion": "reactivar"}
        ).status_code
        == 200
    )
    assert _mensajes(admin, centro.pk) == ["Usuario «leg-objetivo» reactivado."]
    acceso.refresh_from_db()
    assert (acceso.estado, acceso.motivo_estado, acceso.activo) == ("activo", "", True)

    admin.post(_estado_url(centro.pk, acceso.pk), {"accion": "baja", "motivo": "Fin"})
    acceso.refresh_from_db()
    assert (acceso.estado, acceso.motivo_estado) == ("baja", "Fin")
    assert acceso.fecha_baja is not None
    assert _mensajes(admin, centro.pk) == ["Usuario «leg-objetivo» dado de baja."]


@pytest.mark.parametrize(
    ("cuerpo", "mensaje"),
    [
        ({"accion": "suspender", "motivo": "  "}, "Indicá el motivo."),
        ({"accion": "borrar"}, "Acción no válida."),
        (
            {"accion": "reactivar"},
            "No se puede reactivar un usuario en estado «Activo».",
        ),
    ],
)
def test_rejected_status_changes_keep_the_data_and_flash_the_native_error(
    datos, cuerpo, mensaje
):
    centro = datos["centro"]
    admin = _cliente(_usuario("leg-admin-rechazo", superuser=True))
    acceso = _acceso(centro, "leg-intacto")
    antes = _estado()

    respuesta = admin.post(_estado_url(centro.pk, acceso.pk), cuerpo)

    assert respuesta.status_code == 200
    assert respuesta.json()["ok"] is True
    assert _estado() == antes
    assert _mensajes(admin, centro.pk) == [mensaje]


def test_status_change_rules_own_account_responsible_and_scope(datos):
    centro = datos["centro"]
    responsable = _acceso(centro, "leg-resp-rule", responsable=True)
    otro = _acceso(centro, "leg-otro-rule")
    admin = _cliente(_usuario("leg-admin-rule", superuser=True))
    propia = _cliente(User.objects.get(pk=responsable.user_id))
    antes = _estado()

    assert (
        admin.post(
            _estado_url(centro.pk, responsable.pk), {"accion": "baja", "motivo": "x"}
        ).status_code
        == 200
    )
    assert "responsable" in _mensajes(admin, centro.pk)[0]
    assert (
        propia.post(
            _estado_url(centro.pk, responsable.pk), {"accion": "baja", "motivo": "x"}
        ).status_code
        == 200
    )
    assert _mensajes(propia, centro.pk) == [
        "No podés cambiar el estado de tu propio usuario."
    ]
    assert _estado() == antes
    # Another centre's id with this centre's URL is 404 and changes nothing.
    assert (
        admin.post(
            _estado_url(datos["ajeno"].pk, otro.pk),
            {"accion": "suspender", "motivo": "x"},
        ).status_code
        == 404
    )
    assert (
        admin.post(
            _estado_url(centro.pk, 999999), {"accion": "suspender", "motivo": "x"}
        ).status_code
        == 404
    )
    assert _estado() == antes


def test_status_change_permissions_methods_csrf_and_auditor_veto(datos):
    centro = datos["centro"]
    acceso = _acceso(centro, "leg-perm")
    url = _estado_url(centro.pk, acceso.pk)
    cuerpo = {"accion": "suspender", "motivo": "x"}
    sin = _cliente(_usuario("leg-st-sin", perms=()))
    auditor = _cliente(
        _usuario("leg-st-aud", perms=(VER,), grupos=[UserGroups.SIMEPI_AUDITORIA])
    )
    sin_permiso_admin = _cliente(_usuario("leg-st-ver"))
    csrf = WebClient(enforce_csrf_checks=True)
    csrf.force_login(_usuario("leg-st-csrf", superuser=True))
    lector = _cliente(_usuario("leg-st-get", superuser=True))
    antes = _estado()

    assert sin.post(url, cuerpo).status_code == 403
    respuesta = auditor.post(url, cuerpo)
    assert (respuesta.status_code, respuesta.json()) == (403, {"detail": VETO})
    # Viewing is not administering: the native service refuses with PermissionDenied.
    assert sin_permiso_admin.post(url, cuerpo).status_code == 403
    assert (
        Client()
        .post(url, urlencode(cuerpo), content_type="application/x-www-form-urlencoded")
        .status_code
        == 401
    )
    assert csrf.post(url, cuerpo).status_code == 403
    assert lector.get(url).status_code == 405
    assert _estado() == antes


def test_worker_soft_delete_persists_the_native_effects(datos):
    centro = datos["centro"]
    user = _usuario(
        "leg-baja",
        perms=(VER, BAJA_TRABAJADOR),
        grupos=[UserGroups.SIMEPI_EQUIPO_NACIONAL],
    )
    client = _cliente(user)
    trabajador = datos["trabajador"]
    otros = [fila for fila in _estado()[1] if fila["id"] != trabajador.pk]

    respuesta = client.post(_baja_url(centro.pk, trabajador.pk))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/centrodeinfancia/detalle/{centro.pk}",
    }
    fila = Trabajador.all_objects.get(pk=trabajador.pk)
    assert fila.deleted_at is not None
    assert fila.deleted_by == user
    assert [f for f in _estado()[1] if f["id"] != trabajador.pk] == otros
    assert _mensajes(client, centro.pk) == ["Trabajador eliminado correctamente."]
    assert client.get(_detalle(centro.pk)).json()["trabajadores"]["filas"] == []


def test_rejected_worker_deletes_leave_the_data_unchanged(datos):
    centro = datos["centro"]
    sin_baja = _cliente(_usuario("leg-baja-sin"))
    con_baja = _cliente(_usuario("leg-baja-con", perms=(VER, BAJA_TRABAJADOR)))
    auditor = _cliente(
        _usuario(
            "leg-baja-aud",
            perms=(VER, BAJA_TRABAJADOR),
            grupos=[UserGroups.SIMEPI_AUDITORIA],
        )
    )
    antes = _estado()

    assert (
        sin_baja.post(_baja_url(centro.pk, datos["trabajador"].pk)).status_code == 403
    )
    respuesta = auditor.post(_baja_url(centro.pk, datos["trabajador"].pk))
    assert (respuesta.status_code, respuesta.json()) == (403, {"detail": VETO})
    assert (
        Client().post(_baja_url(centro.pk, datos["trabajador"].pk)).status_code == 401
    )
    # A worker of another centre, or a missing one, is 404 through this centre.
    assert (
        con_baja.post(_baja_url(centro.pk, datos["ajeno_trabajador"].pk)).status_code
        == 404
    )
    assert con_baja.post(_baja_url(centro.pk, 999999)).status_code == 404
    assert con_baja.get(_baja_url(centro.pk, datos["trabajador"].pk)).status_code == 405
    assert _estado() == antes
