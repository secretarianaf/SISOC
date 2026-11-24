"""CDI07 observations: web API (G1 v1) and the CDI-A3 auditor veto.

The API inherits the native views, so the same form, scope, server-side
author/date, ``next`` handling and soft delete apply. CDI-A3 (2026-10-28):
SIMEPI auditors cannot create, edit or delete observations, with the same
predicate and exceptions as CDI-A2 (``es_auditor_simepi``: superuser,
SIMEPI - Administrador and SIMEPI - Analista de datos are not vetoed), on the
native pages and on the API. Reads keep their policy.
"""

from urllib.parse import urlencode

import pytest
from auditlog.models import LogEntry
from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.db import connection
from django.test import Client, override_settings
from django.test.client import MULTIPART_CONTENT as MULTIPART
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from centrodeinfancia.models import CentroDeInfancia, ObservacionCentroInfancia
from core import web_gate
from core.constants import UserGroups
from core.models import Provincia

API = "/api/web/cdi/"
WRITES = ("INSERT", "UPDATE", "DELETE")
VETO = "El rol Auditoría tiene acceso de solo lectura."
BAJA = "Observación dada de baja correctamente."
OPERACIONES = (
    "centrodeinfancia.view_centrodeinfancia",
    "centrodeinfancia.add_intervencioncentroinfancia",
    "centrodeinfancia.change_intervencioncentroinfancia",
    "centrodeinfancia.delete_intervencioncentroinfancia",
)

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return User.objects.get(pk=user.pk)


def _usuario(username, *, perms=OPERACIONES, grupos=(), superuser=False):
    user = User.objects.create_user(
        username=username,
        first_name="Ana",
        last_name="Operadora",
        is_superuser=superuser,
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
    """Posts to the web API URL-encoded, as the React page does."""

    def post(self, path, data=None, content_type=None, **extra):
        if content_type is None and str(path).startswith(API):
            return super().post(
                path,
                urlencode(data or {}),
                content_type="application/x-www-form-urlencoded",
                **extra,
            )
        return super().post(path, data, content_type=content_type or MULTIPART, **extra)


def _cliente(user):
    client = WebClient()
    client.force_login(user)
    return client


def _ficha(pk):
    return reverse("centrodeinfancia_detalle", args=[pk])


@pytest.fixture(name="centro")
def centro_fixture():
    return CentroDeInfancia.objects.create(
        nombre="CDI Sintético", provincia=Provincia.objects.create(nombre="Mendoza")
    )


@pytest.fixture(name="observacion")
def observacion_fixture(centro):
    return ObservacionCentroInfancia.objects.create(
        centro=centro, observador="Otra Persona", observacion="Texto original."
    )


def _crear(pk):
    return f"{API}centros/{pk}/observaciones/crear/"


def _detalle(pk):
    return f"{API}observaciones/{pk}/"


def _editar(pk):
    return f"{API}observaciones/{pk}/editar/"


def _eliminar(pk):
    return f"{API}observaciones/{pk}/eliminar/"


def _estado():
    """Every observation row, deleted ones included, plus the audit trail size."""
    filas = list(
        ObservacionCentroInfancia.all_objects.order_by("pk").values(
            "pk", "observacion", "observador", "centro_id", "deleted_at", "deleted_by"
        )
    )
    return filas, LogEntry.objects.count()


# --- Create -------------------------------------------------------------------


def test_create_form_projects_the_native_field(centro):
    respuesta = _cliente(_usuario("obs-form")).get(_crear(centro.pk))

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    assert "Cookie" in respuesta["Vary"]
    assert respuesta.json() == {
        "centro": {
            "id": centro.pk,
            "nombre": "CDI Sintético",
            "url": _ficha(centro.pk),
        },
        "field": {
            "name": "observacion",
            "label": "Observación",
            "required": True,
            "rows": 4,
            "placeholder": "Describa la observación",
        },
        "value": "",
        "errors": {},
        "messages": [],
    }


def test_create_sets_centre_author_and_date_on_the_server_and_goes_to_the_detail(
    centro,
):
    otro = CentroDeInfancia.objects.create(nombre="Otro")
    antes = timezone.now()

    respuesta = _cliente(_usuario("obs-alta")).post(
        _crear(centro.pk),
        {"observacion": "Visita sin novedades.", "centro": otro.pk, "observador": "x"},
    )

    creada = ObservacionCentroInfancia.objects.get()
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/centrodeinfancia/observacion/{creada.pk}/",
    }
    assert creada.centro_id == centro.pk
    assert creada.observador == "Ana Operadora"
    assert creada.observacion == "Visita sin novedades."
    assert creada.fecha_visita >= antes


def test_create_author_falls_back_to_the_username(centro):
    user = _usuario("obs-sin-nombre")
    user.first_name = user.last_name = ""
    user.save()

    _cliente(user).post(_crear(centro.pk), {"observacion": "Texto."})

    assert ObservacionCentroInfancia.objects.get().observador == "obs-sin-nombre"


def test_create_follows_a_safe_next_and_ignores_an_external_one(centro):
    client = _cliente(_usuario("obs-next"))
    ficha = _ficha(centro.pk)

    interno = client.post(f"{_crear(centro.pk)}?next={ficha}", {"observacion": "A"})
    externo = client.post(
        f"{_crear(centro.pk)}?next=https://ejemplo.invalid/", {"observacion": "B"}
    )

    assert interno.json()["redirect"] == ficha
    segunda = ObservacionCentroInfancia.objects.get(observacion="B")
    assert externo.json()["redirect"] == f"/centrodeinfancia/observacion/{segunda.pk}/"


def test_create_invalid_returns_the_native_error_and_writes_nothing(centro):
    client = _cliente(_usuario("obs-invalida"))
    antes = _estado()

    respuesta = client.post(_crear(centro.pk), {"observacion": ""})

    assert respuesta.status_code == 400
    assert respuesta.json()["errors"] == {
        "observacion": [{"message": "Este campo es requerido.", "code": "required"}]
    }
    assert respuesta.json()["value"] == ""
    assert _estado() == antes


def test_create_for_a_centre_outside_the_scope_is_404(centro):
    egp = _usuario("obs-egp-sin-territorio", grupos=[UserGroups.SIMEPI_EGP])
    client = _cliente(egp)
    antes = _estado()

    assert client.get(_crear(centro.pk)).status_code == 404
    assert client.post(_crear(centro.pk), {"observacion": "x"}).status_code == 404
    assert client.get(_crear(999999)).status_code == 404
    assert _estado() == antes


def test_create_requires_the_add_permission(centro):
    sin_alta = _cliente(
        _usuario("obs-sin-alta", perms=["centrodeinfancia.view_centrodeinfancia"])
    )
    antes = _estado()

    assert sin_alta.get(_crear(centro.pk)).status_code == 403
    assert sin_alta.post(_crear(centro.pk), {"observacion": "x"}).status_code == 403
    assert _estado() == antes


def test_only_urlencoded_posts_are_accepted(centro):
    client = _cliente(_usuario("obs-formato"))

    respuesta = client.post(
        _crear(centro.pk), {"observacion": "x"}, content_type="application/json"
    )

    assert respuesta.status_code == 415
    assert not ObservacionCentroInfancia.objects.exists()
    assert client.put(_crear(centro.pk)).status_code == 405


# --- Detail and edit ----------------------------------------------------------


def test_detail_projects_the_native_card(observacion):
    fecha = timezone.localtime(observacion.fecha_visita).strftime("%d/%m/%Y %H:%M")
    client = _cliente(
        _usuario("obs-ver", perms=["centrodeinfancia.view_centrodeinfancia"])
    )

    respuesta = client.get(_detalle(observacion.pk))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id": observacion.pk,
        "centro": {
            "id": observacion.centro_id,
            "nombre": "CDI Sintético",
            "url": _ficha(observacion.centro_id),
        },
        "observador": "Otra Persona",
        "fecha": fecha,
        "observacion": "Texto original.",
        "urls": {
            "editar": f"/centrodeinfancia/observacion/{observacion.pk}/editar/",
            "eliminar": f"/centrodeinfancia/observacion/{observacion.pk}/eliminar/",
        },
        "messages": [],
    }
    assert client.post(_detalle(observacion.pk)).status_code == 405


def test_detail_without_author_shows_a_dash_and_reads_never_write(observacion):
    observacion.observador = ""
    observacion.save()
    client = _cliente(_usuario("obs-lectura"))
    client.get(_detalle(observacion.pk))

    with CaptureQueriesContext(connection) as queries:
        data = client.get(_detalle(observacion.pk)).json()
        client.get(_editar(observacion.pk))
        client.get(_eliminar(observacion.pk))

    assert data["observador"] == "-"
    assert not [
        q["sql"] for q in queries.captured_queries if q["sql"].startswith(WRITES)
    ]


def test_edit_keeps_the_centre_and_goes_to_the_detail(observacion):
    otro = CentroDeInfancia.objects.create(nombre="Otro")
    client = _cliente(_usuario("obs-edicion"))

    formulario = client.get(_editar(observacion.pk)).json()
    respuesta = client.post(
        _editar(observacion.pk), {"observacion": "Texto nuevo.", "centro": otro.pk}
    )

    observacion.refresh_from_db()
    assert formulario["value"] == "Texto original."
    assert formulario["centro"]["id"] == observacion.centro_id
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/centrodeinfancia/observacion/{observacion.pk}/",
    }
    assert observacion.observacion == "Texto nuevo."
    assert observacion.centro.nombre == "CDI Sintético"
    assert observacion.observador == "Otra Persona"


def test_edit_invalid_is_400_without_changes(observacion):
    client = _cliente(_usuario("obs-edicion-mal"))
    antes = _estado()

    respuesta = client.post(_editar(observacion.pk), {"observacion": ""})

    assert respuesta.status_code == 400
    assert respuesta.json()["errors"]["observacion"][0]["code"] == "required"
    assert _estado() == antes


# --- Delete -------------------------------------------------------------------


def test_delete_confirmation_projects_the_native_component(observacion):
    data = _cliente(_usuario("obs-confirmar")).get(_eliminar(observacion.pk)).json()

    assert data["object_name"] == str(observacion).upper()
    assert data["confirm_text"] == "Dar de baja"
    assert data["cancel_text"] == "Cancelar"
    assert data["cancel_url"] == f"/centrodeinfancia/observacion/{observacion.pk}/"
    assert data["cascade_preview"]["total_afectados"] >= 1


def test_delete_is_a_soft_delete_back_to_the_centre_with_the_native_message(
    observacion,
):
    user = _usuario("obs-baja")
    client = _cliente(user)

    respuesta = client.post(_eliminar(observacion.pk))

    fila = ObservacionCentroInfancia.all_objects.get(pk=observacion.pk)
    assert respuesta.json() == {
        "ok": True,
        "redirect": _ficha(observacion.centro_id),
    }
    assert fila.deleted_at is not None
    assert fila.deleted_by_id == user.pk
    assert fila.observacion == "Texto original."
    assert not ObservacionCentroInfancia.objects.filter(pk=observacion.pk).exists()
    assert client.get(_detalle(observacion.pk)).status_code == 404
    ficha = client.get(_ficha(observacion.centro_id))
    assert [str(m) for m in ficha.context["messages"]] == [BAJA]


def test_delete_requires_the_delete_permission(observacion):
    client = _cliente(
        _usuario(
            "obs-sin-baja",
            perms=[
                "centrodeinfancia.view_centrodeinfancia",
                "centrodeinfancia.change_intervencioncentroinfancia",
            ],
        )
    )
    antes = _estado()

    assert client.get(_eliminar(observacion.pk)).status_code == 403
    assert client.post(_eliminar(observacion.pk)).status_code == 403
    assert _estado() == antes


# --- CDI-A3 auditor veto (API and native) -----------------------------------

VETADOS = {
    "auditoria_mixta": [UserGroups.SIMEPI_AUDITORIA],
    "auditoria_egp": [UserGroups.SIMEPI_AUDITORIA, UserGroups.SIMEPI_EGP],
    "auditoria_equipo_nacional": [
        UserGroups.SIMEPI_AUDITORIA,
        UserGroups.SIMEPI_EQUIPO_NACIONAL,
    ],
}
EXCEPTUADOS = {
    "sin_auditoria": [],
    "auditoria_administrador": [
        UserGroups.SIMEPI_AUDITORIA,
        UserGroups.SIMEPI_ADMINISTRADOR,
    ],
    "auditoria_analista": [
        UserGroups.SIMEPI_AUDITORIA,
        UserGroups.SIMEPI_ANALISTA_DATOS,
    ],
}


def _mutaciones(centro, observacion, native):
    if native:
        return [
            (
                reverse("centrodeinfancia_observacion_crear", args=[centro.pk]),
                {"observacion": "x"},
            ),
            (
                reverse("centrodeinfancia_observacion_editar", args=[observacion.pk]),
                {"observacion": "y"},
            ),
            (
                reverse("centrodeinfancia_observacion_eliminar", args=[observacion.pk]),
                {},
            ),
        ]
    return [
        (_crear(centro.pk), {"observacion": "x"}),
        (_editar(observacion.pk), {"observacion": "y"}),
        (_eliminar(observacion.pk), {}),
    ]


@pytest.mark.parametrize("native", [False, True], ids=["api", "native"])
@pytest.mark.parametrize("perfil", sorted(VETADOS))
def test_auditor_mutations_are_rejected_without_effects(
    centro, observacion, perfil, native
):
    client = _cliente(_usuario(f"obs-veto-{perfil}", grupos=VETADOS[perfil]))
    antes = _estado()

    for url, datos in _mutaciones(centro, observacion, native):
        respuesta = client.post(url, datos)
        assert respuesta.status_code == 403, url
        if not native:
            assert respuesta.json() == {"detail": VETO}, url

    assert _estado() == antes


@pytest.mark.parametrize("perfil", sorted(VETADOS))
def test_auditor_reads_keep_their_policy(centro, observacion, perfil):
    client = _cliente(_usuario(f"obs-lee-{perfil}", grupos=VETADOS[perfil]))

    assert client.get(_detalle(observacion.pk)).status_code == 200
    assert client.get(_crear(centro.pk)).status_code == 200
    assert client.get(_editar(observacion.pk)).status_code == 200
    assert client.get(_eliminar(observacion.pk)).status_code == 200
    assert (
        client.get(
            reverse("centrodeinfancia_observacion_detalle", args=[observacion.pk])
        ).status_code
        == 200
    )
    assert (
        client.get(
            reverse("centrodeinfancia_observacion_crear", args=[centro.pk])
        ).status_code
        == 200
    )


@pytest.mark.parametrize("native", [False, True], ids=["api", "native"])
@pytest.mark.parametrize("perfil", sorted(EXCEPTUADOS))
def test_exceptions_keep_their_mutations(centro, observacion, perfil, native):
    client = _cliente(_usuario(f"obs-ok-{perfil}", grupos=EXCEPTUADOS[perfil]))
    crear, editar, eliminar = _mutaciones(centro, observacion, native)

    assert client.post(*crear).status_code in (200, 302)
    assert client.post(*editar).status_code in (200, 302)
    assert client.post(*eliminar).status_code in (200, 302)

    assert ObservacionCentroInfancia.objects.filter(observacion="x").count() == 1
    fila = ObservacionCentroInfancia.all_objects.get(pk=observacion.pk)
    assert fila.observacion == "y"
    assert fila.deleted_at is not None


@pytest.mark.parametrize("native", [False, True], ids=["api", "native"])
def test_superuser_auditor_is_not_vetoed(centro, observacion, native):
    client = _cliente(
        _usuario(
            "obs-super-auditor",
            perms=(),
            grupos=[UserGroups.SIMEPI_AUDITORIA],
            superuser=True,
        )
    )
    crear, editar, eliminar = _mutaciones(centro, observacion, native)

    for url, datos in (crear, editar, eliminar):
        assert client.post(url, datos).status_code in (200, 302), url
    assert ObservacionCentroInfancia.all_objects.get(pk=observacion.pk).deleted_at


def test_auditor_without_the_action_permission_gets_the_permission_403_first(
    observacion,
):
    client = _cliente(
        _usuario(
            "obs-auditor-puro",
            perms=["centrodeinfancia.view_centrodeinfancia"],
            grupos=[UserGroups.SIMEPI_AUDITORIA],
        )
    )

    respuesta = client.post(_editar(observacion.pk), {"observacion": "y"})

    assert respuesta.status_code == 403
    assert respuesta.json() != {"detail": VETO}


# --- Gate -----------------------------------------------------------------------


def test_anonymous_gets_401_json(observacion):
    for url in (_detalle(observacion.pk), _crear(observacion.centro_id)):
        respuesta = Client().post(url, {"observacion": "x"})
        assert respuesta.status_code == 401
        assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert ObservacionCentroInfancia.objects.count() == 1


def test_pending_web_requirement_blocks_before_any_write(observacion):
    user = _usuario("obs-pendiente")
    user.profile.must_change_password = True
    user.profile.save()
    antes = _estado()

    respuesta = _cliente(user).post(_eliminar(observacion.pk))

    assert respuesta.status_code == 403
    assert respuesta.json()["detail"] == web_gate.DETAIL_REQUIREMENT
    assert respuesta.json()["state"] == "password_change_required"
    assert _estado() == antes


def test_admindocs_head_does_not_bypass_the_web_api(observacion):
    staff = User.objects.create_user("obs-staff", is_staff=True)
    respuesta = _cliente(_ready(staff)).head(_detalle(observacion.pk))

    assert "X-View" not in respuesta
    assert respuesta.status_code == 403


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
def test_runtime_accepts_a_signed_post_and_rejects_an_unsigned_one(observacion):
    user = _usuario("obs-runtime")
    client = _cliente(user)
    target = _editar(observacion.pk)

    sin_firma = client.post(target, {"observacion": "z"}, RAW_URI=target)
    firma_get = client.post(
        target,
        {"observacion": "z"},
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(user, client, target=target, method="GET"),
    )
    observacion.refresh_from_db()
    assert sin_firma.status_code == 403
    assert firma_get.status_code == 403
    assert observacion.observacion == "Texto original."

    firmada = client.post(
        target,
        {"observacion": "z"},
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(user, client, target=target, method="POST"),
    )
    observacion.refresh_from_db()
    assert firmada.status_code == 200
    assert observacion.observacion == "z"


@pytest.mark.usefixtures("runtime")
def test_runtime_keeps_the_auditor_veto_after_a_valid_attestation(observacion):
    user = _usuario("obs-runtime-auditor", grupos=[UserGroups.SIMEPI_AUDITORIA])
    client = _cliente(user)
    target = _eliminar(observacion.pk)
    antes = _estado()

    respuesta = client.post(
        target,
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(user, client, target=target, method="POST"),
    )

    assert respuesta.status_code == 403
    assert respuesta.json() == {"detail": VETO}
    assert _estado() == antes
