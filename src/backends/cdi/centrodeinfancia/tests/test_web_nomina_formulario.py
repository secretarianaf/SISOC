"""Web API (G1 v1) of the CDI nomina form detail: ``/api/web/cdi/nomina/<pk>/formulario/``.

Read-only projection of ``NominaCentroInfanciaFormularioDetailView`` for the React page.
Every row is compared with the HTML the native page renders for the same record.
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

from centrodeinfancia.models import AccesoCDI, CentroDeInfancia, NominaCentroInfancia
from ciudadanos.models import Ciudadano
from core import web_gate
from core.models import Provincia

VER = "centrodeinfancia.view_nominacentroinfancia"
WRITES = ("INSERT", "UPDATE", "DELETE")

pytestmark = pytest.mark.django_db


def _url(pk):
    return f"/api/web/cdi/nomina/{pk}/formulario/"


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
        talla=Decimal("85.5"),
        posee_cud=True,
        posee_obra_social=False,
        sala="Sala verde",
        observaciones="Primera línea",
    )
    return {"centro": centro, "otro": otro, "ficha": ficha}


class _Filas(HTMLParser):
    """``label``/``value`` cell pairs of ``nomina_formulario_detail.html``, in order."""

    def __init__(self):
        super().__init__()
        self.filas, self._celda, self._etiqueta, self._valor = [], None, None, ""

    def handle_starttag(self, tag, attrs):
        if tag == "td":
            self._celda = "value" if self._etiqueta is not None else "label"
            self._valor = ""

    def handle_data(self, data):
        if self._celda:
            self._valor += data

    def handle_endtag(self, tag):
        if tag != "td":
            return
        if self._celda == "label":
            self._etiqueta = self._valor.strip()
        else:
            self.filas.append((self._etiqueta, self._valor.strip()))
            self._etiqueta = None
        self._celda = None


def _nativo(client, ficha):
    respuesta = client.get(
        reverse("centrodeinfancia_nomina_formulario_ver", args=[ficha.pk])
    )
    parser = _Filas()
    parser.feed(respuesta.content.decode())
    return respuesta, parser.filas


def test_every_row_matches_the_native_html(datos):
    client = _cliente(_usuario("web-form-paridad", superuser=True))

    respuesta = client.get(_url(datos["ficha"].pk))
    nativo, filas = _nativo(client, datos["ficha"])

    assert respuesta.status_code == 200
    assert nativo.status_code == 200
    assert respuesta["Content-Type"] == "application/json"
    assert respuesta["Cache-Control"] == "private, no-store"
    assert "Cookie" in respuesta["Vary"]
    data = respuesta.json()
    assert len(filas) == 51
    assert [(r["label"], r["value"]) for r in data["rows"]] == filas
    assert set(data) == {"rows", "messages"}
    assert data["messages"] == []
    valores = dict(filas)
    assert valores["Fecha de nacimiento"] == "04/03/2023"
    assert valores["Posee CUD"] == "Sí"
    assert valores["Posee obra social"] == "No"
    assert valores["Recibe apoyo por discapacidad"] == "-"
    assert valores["Sala"] == "Sala verde"
    assert valores["Departamento domicilio"] == "-"


def test_scope_and_unknown_ids_are_enforced_like_the_native_page(datos):
    user = _usuario("web-form-referente")
    AccesoCDI.objects.create(user=user, centro=datos["centro"])
    cliente = _cliente(user)
    ajeno = NominaCentroInfancia.objects.create(
        centro=datos["otro"],
        ciudadano=Ciudadano.objects.create(apellido="X", nombre="Y", documento=1),
        estado=NominaCentroInfancia.ESTADO_ACTIVO,
    )

    assert cliente.get(_url(datos["ficha"].pk)).status_code == 200
    assert cliente.get(_url(ajeno.pk)).status_code == 404
    assert cliente.get(_url(999999)).status_code == 404
    native = cliente.get(
        reverse("centrodeinfancia_nomina_formulario_ver", args=[ajeno.pk])
    )
    assert native.status_code == 404


def test_reads_never_write(datos):
    client = _cliente(_usuario("web-form-lectura", superuser=True))
    client.get(_url(datos["ficha"].pk))

    with CaptureQueriesContext(connection) as queries:
        assert client.get(_url(datos["ficha"].pk)).status_code == 200

    assert not [
        q["sql"] for q in queries.captured_queries if q["sql"].startswith(WRITES)
    ]


def test_anonymous_gets_401_json(datos):
    respuesta = Client().get(_url(datos["ficha"].pk))

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert respuesta["Cache-Control"] == "private, no-store"


def test_without_the_view_permission_gets_403(datos):
    sin = _usuario("web-form-sin-permiso", perms=())
    otro = _usuario(
        "web-form-otro-permiso", perms=("centrodeinfancia.view_centrodeinfancia",)
    )

    for user in (sin, otro):
        respuesta = _cliente(user).get(_url(datos["ficha"].pk))
        assert respuesta.status_code == 403
        assert respuesta.json() != {"detail": web_gate.DETAIL_REQUIREMENT}


def test_pending_requirement_is_reported_and_a_forged_header_is_ignored(datos):
    user = _usuario("web-form-pendiente", superuser=True)
    user.profile.must_change_password = True
    user.profile.save()
    client = _cliente(user)
    destino = _url(datos["ficha"].pk)
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
    client = _cliente(_usuario("web-form-metodos", superuser=True))
    destino = _url(datos["ficha"].pk)

    assert client.post(destino).status_code == 405
    assert client.delete(destino).status_code == 405
    assert client.head(destino).status_code == 200


def _firmado(user, client, destino):
    return web_gate.sign(
        audience="cdi",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method="GET",
        target=destino,
    )


def test_runtime_serves_a_signed_request_and_still_applies_the_permission(datos):
    destino = _url(datos["ficha"].pk)
    with override_settings(
        SISOC_BACKEND="cdi",
        ROOT_URLCONF="cdi_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        user = _usuario("web-form-runtime", superuser=True)
        client = _cliente(user)
        ok = client.get(
            destino,
            RAW_URI=destino,
            HTTP_X_SISOC_WEB_GATE=_firmado(user, client, destino),
        )
        sin = _usuario("web-form-runtime-sin", perms=())
        cliente_sin = _cliente(sin)
        prohibido = cliente_sin.get(
            destino,
            RAW_URI=destino,
            HTTP_X_SISOC_WEB_GATE=_firmado(sin, cliente_sin, destino),
        )
        anonimo = Client().get(destino, RAW_URI=destino)

    assert ok.status_code == 200
    assert len(ok.json()["rows"]) == 51
    assert prohibido.status_code == 403
    assert anonimo.status_code == 401
