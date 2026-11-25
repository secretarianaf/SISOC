"""Web API (G1 v1) of the CDI soft-delete confirmations: centre and nómina.

``/api/web/cdi/centros/<pk>/eliminar/`` and
``/api/web/cdi/centros/<pk>/nomina/<pk2>/eliminar/`` inherit the native
``CentroDeInfanciaDeleteView`` and ``NominaCentroInfanciaDeleteView``: the
same URL permission, scope, CDI-A3 auditor veto, cascade preview, soft delete,
message and redirect. Every rejected request is checked against a snapshot.
"""

from urllib.parse import urlencode

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.urls import reverse

from centrodeinfancia.models import AccesoCDI, CentroDeInfancia, NominaCentroInfancia
from ciudadanos.models import Ciudadano
from core import web_gate
from core.constants import UserGroups
from core.models import Provincia, Sexo

API = "/api/web/cdi/"
BAJA_CENTRO = "centrodeinfancia.delete_centrodeinfancia"
BAJA_NOMINA = "centrodeinfancia.delete_nominacentroinfancia"
VETO = "El rol Auditoría tiene acceso de solo lectura."
MENSAJE_CENTRO = "Centro de Desarrollo Infantil dado de baja correctamente."
MENSAJE_NOMINA = "Registro de nómina dado de baja correctamente."

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
    return permiso or Permission.objects.create(
        content_type=ContentType.objects.get_for_model(Group),
        codename=codename,
        name=codename,
    )


def _usuario(username, *perms, grupos=()):
    user = User.objects.create_user(username=username)
    for codigo in perms:
        user.user_permissions.add(_permiso(codigo))
    for nombre in grupos:
        user.groups.add(Group.objects.get_or_create(name=nombre)[0])
    return _ready(user)


class WebClient(Client):
    """Posts to the web API URL-encoded, as the React page does."""

    def post(self, path, data=None, content_type=None, **extra):
        if content_type is None:
            return super().post(
                path,
                urlencode(data or {}),
                content_type="application/x-www-form-urlencoded",
                **extra,
            )
        return super().post(path, data, content_type=content_type, **extra)


def _cliente(user):
    client = WebClient()
    client.force_login(user)
    return client


def _centro_api(pk):
    return f"{API}centros/{pk}/eliminar/"


def _nomina_api(pk, pk2):
    return f"{API}centros/{pk}/nomina/{pk2}/eliminar/"


@pytest.fixture(name="datos")
def datos_fixture():
    provincia = Provincia.objects.create(nombre="Mendoza")
    centro = CentroDeInfancia.objects.create(nombre="CDI Girasol", provincia=provincia)
    ajeno = CentroDeInfancia.objects.create(nombre="CDI Ajeno", provincia=provincia)
    ciudadano = Ciudadano.objects.create(
        apellido="Paz",
        nombre="Sofía",
        documento=30111222,
        sexo=Sexo.objects.get_or_create(sexo="Femenino")[0],
    )
    nomina = NominaCentroInfancia.objects.create(centro=centro, ciudadano=ciudadano)
    return centro, ajeno, nomina


def _estado():
    centros = list(
        CentroDeInfancia.all_objects.order_by("pk").values("pk", "deleted_at")
    )
    nominas = list(
        NominaCentroInfancia.all_objects.order_by("pk").values("pk", "deleted_at")
    )
    return centros, nominas


# --- Centre ----------------------------------------------------------------------


def test_centre_confirmation_projects_the_native_component(datos):
    centro, _, _ = datos
    respuesta = _cliente(_usuario("baja-centro-ver", BAJA_CENTRO)).get(
        _centro_api(centro.pk)
    )

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    assert data["title"] == "Eliminar Centro de Desarrollo Infantil"
    assert data["object_name"] == "CDI GIRASOL"
    assert data["confirm_text"] == "Dar de baja"
    assert data["cancel_text"] == "Cancelar"
    assert data["cancel_url"] == reverse("centrodeinfancia")
    assert data["cascade_preview"]["total_afectados"] >= 2
    assert data["messages"] == []


def test_centre_post_is_the_native_soft_delete_with_its_message(datos):
    centro, _, nomina = datos
    user = _usuario(
        "baja-centro-post", BAJA_CENTRO, "centrodeinfancia.view_centrodeinfancia"
    )
    client = _cliente(user)

    respuesta = client.post(_centro_api(centro.pk))

    assert respuesta.json() == {"ok": True, "redirect": reverse("centrodeinfancia")}
    fila = CentroDeInfancia.all_objects.get(pk=centro.pk)
    assert fila.deleted_at is not None
    assert fila.deleted_by_id == user.pk
    assert NominaCentroInfancia.all_objects.get(pk=nomina.pk).deleted_at is not None
    lista = client.get(reverse("centrodeinfancia"))
    assert MENSAJE_CENTRO in [str(m) for m in lista.context["messages"]]


def test_centre_requires_the_native_permission_and_scope(datos):
    centro, ajeno, _ = datos
    antes = _estado()
    sin_permiso = _cliente(
        _usuario("baja-centro-sin", "centrodeinfancia.view_centrodeinfancia")
    )
    assert sin_permiso.get(_centro_api(centro.pk)).status_code == 403
    assert sin_permiso.post(_centro_api(centro.pk)).status_code == 403

    referente = _usuario("baja-centro-ref", BAJA_CENTRO)
    AccesoCDI.objects.create(user=referente, centro=centro)
    fuera = _cliente(referente)
    negado = fuera.get(_centro_api(ajeno.pk))
    assert negado.status_code == 404
    assert "CDI AJENO" not in negado.content.decode()
    assert fuera.post(_centro_api(ajeno.pk)).status_code == 404
    assert _estado() == antes


def test_centre_auditor_veto_is_kept_without_effects(datos):
    centro, _, _ = datos
    antes = _estado()
    client = _cliente(
        _usuario("baja-centro-aud", BAJA_CENTRO, grupos=[UserGroups.SIMEPI_AUDITORIA])
    )

    respuesta = client.post(_centro_api(centro.pk))

    assert respuesta.status_code == 403
    assert respuesta.json() == {"detail": VETO}
    assert _estado() == antes


# --- Nómina ----------------------------------------------------------------------


def test_nomina_confirmation_projects_the_native_component(datos):
    centro, _, nomina = datos
    data = (
        _cliente(_usuario("baja-nomina-ver", BAJA_NOMINA))
        .get(_nomina_api(centro.pk, nomina.pk))
        .json()
    )

    assert data["title"] == "Eliminar registro de nómina"
    assert data["object_name"] == str(nomina).upper()
    assert data["confirm_text"] == "Dar de baja"
    assert data["cancel_text"] == "Cancelar"
    assert data["cancel_url"] == reverse(
        "centrodeinfancia_nomina_ver", kwargs={"pk": centro.pk}
    )
    assert data["cascade_preview"]["total_afectados"] >= 1


def test_nomina_post_is_the_native_soft_delete_back_to_the_list(datos):
    centro, _, nomina = datos
    user = _usuario(
        "baja-nomina-post", BAJA_NOMINA, "centrodeinfancia.view_nominacentroinfancia"
    )
    client = _cliente(user)

    respuesta = client.post(_nomina_api(centro.pk, nomina.pk))

    destino = reverse("centrodeinfancia_nomina_ver", kwargs={"pk": centro.pk})
    assert respuesta.json() == {"ok": True, "redirect": destino}
    fila = NominaCentroInfancia.all_objects.get(pk=nomina.pk)
    assert fila.deleted_at is not None
    assert fila.deleted_by_id == user.pk
    assert CentroDeInfancia.objects.filter(pk=centro.pk).exists()
    lista = client.get(destino)
    assert MENSAJE_NOMINA in [str(m) for m in lista.context["messages"]]


def test_nomina_of_another_centre_or_out_of_scope_is_404(datos):
    centro, ajeno, nomina = datos
    antes = _estado()
    client = _cliente(_usuario("baja-nomina-cruzada", BAJA_NOMINA))
    assert client.get(_nomina_api(ajeno.pk, nomina.pk)).status_code == 404
    assert client.post(_nomina_api(ajeno.pk, nomina.pk)).status_code == 404

    referente = _usuario("baja-nomina-ref", BAJA_NOMINA)
    AccesoCDI.objects.create(user=referente, centro=ajeno)
    fuera = _cliente(referente)
    negado = fuera.get(_nomina_api(centro.pk, nomina.pk))
    assert negado.status_code == 404
    assert "PAZ" not in negado.content.decode()
    assert fuera.post(_nomina_api(centro.pk, nomina.pk)).status_code == 404
    sin_permiso = _cliente(_usuario("baja-nomina-sin"))
    assert sin_permiso.post(_nomina_api(centro.pk, nomina.pk)).status_code == 403
    assert _estado() == antes


# --- Gate ------------------------------------------------------------------------


def test_anonymous_and_pending_requirement_are_rejected_without_effects(datos):
    centro, _, nomina = datos
    antes = _estado()
    for url in (_centro_api(centro.pk), _nomina_api(centro.pk, nomina.pk)):
        anonimo = Client().post(url)
        assert anonimo.status_code == 401
        assert anonimo.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}

    user = _usuario("baja-pendiente", BAJA_CENTRO, BAJA_NOMINA)
    user.profile.must_change_password = True
    user.profile.save()
    respuesta = _cliente(user).post(_centro_api(centro.pk))
    assert respuesta.status_code == 403
    assert respuesta.json()["state"] == "password_change_required"
    assert _estado() == antes


def test_only_urlencoded_posts_are_accepted(datos):
    centro, _, _ = datos
    antes = _estado()
    client = _cliente(_usuario("baja-json", BAJA_CENTRO))

    respuesta = client.post(
        _centro_api(centro.pk), '{"x": 1}', content_type="application/json"
    )

    assert respuesta.status_code == 415
    assert _estado() == antes


def test_admindocs_head_does_not_bypass_the_web_api(datos):
    centro, _, nomina = datos
    staff = _ready(User.objects.create_user("baja-staff", is_staff=True))
    client = _cliente(staff)

    for url in (_centro_api(centro.pk), _nomina_api(centro.pk, nomina.pk)):
        respuesta = client.head(url)
        assert "X-View" not in respuesta
        assert respuesta.status_code == 403
