"""Web API (G1 v1) of the CDF centre create, edit and soft delete (CDF04.02).

Each endpoint runs the native view; the tests pin the current access rules
(D1 parity: create needs only ``view_centro``; edit and delete need referente
FK, superuser or SSE, not an ``AccesoCDF``), the persisted effects through
explicit fields (cascade included) and the native messages verbatim.
"""

from datetime import time

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.test import Client
from django.urls import reverse

from centrodefamilia.models import (
    AccesoCDF,
    Actividad,
    ActividadCentro,
    Categoria,
    Centro,
)
from core import web_gate
from core.constants import UserGroups
from core.models import Provincia

ROOT = "/api/web/cdf/centros/"

pytestmark = pytest.mark.django_db


def _user(username, *roles, view=True, superuser=False):
    factory = User.objects.create_superuser if superuser else User.objects.create_user
    user = factory(username, password="x") if superuser else factory(username)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    if view:
        user.user_permissions.add(
            Permission.objects.get(
                content_type=ContentType.objects.get_for_model(Centro),
                codename="view_centro",
            )
        )
    for role in roles:
        permission, _ = Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Group),
            codename=role,
            defaults={"name": role},
        )
        user.user_permissions.add(permission)
    return User.objects.get(pk=user.pk)


def _client(user, csrf=False):
    client = Client(enforce_csrf_checks=csrf)
    client.force_login(user)
    return client


@pytest.fixture(name="provincia")
def provincia_fixture():
    return Provincia.objects.create(nombre="Provincia Sintética")


@pytest.fixture(name="referente")
def referente_fixture():
    grupo, _ = Group.objects.get_or_create(name=UserGroups.CDF_REFERENTE_CENTRO)
    user = _user("ref_grupo")
    user.groups.add(grupo)
    return user


def _centro(nombre, provincia, **extra):
    datos = {
        "nombre": nombre,
        "tipo": "faro",
        "codigo": nombre[:20],
        "provincia": provincia,
        "domicilio_actividad": "Domicilio",
        "telefono": "011",
        "celular": "15",
        "correo": "c@example.com",
        "nombre_referente": "Rita",
        "apellido_referente": "Ref",
        "telefono_referente": "012",
        "correo_referente": "r@example.com",
    }
    datos.update(extra)
    return Centro.objects.create(**datos)


@pytest.fixture(name="faro")
def faro_fixture(provincia):
    return _centro("Faro Uno", provincia)


def _payload(provincia, referente, **over):
    datos = {
        "tipo": "faro",
        "nombre": "Centro Nuevo",
        "codigo": "NUEVO-1",
        "provincia": str(provincia.pk),
        "domicilio_actividad": "Calle 1",
        "telefono": "011-1",
        "celular": "15-1",
        "correo": "nuevo@example.com",
        "nombre_referente": "Nora",
        "apellido_referente": "Nueva",
        "telefono_referente": "011-2",
        "correo_referente": "nora@example.com",
        "referente": str(referente.pk),
        "activo": "on",
    }
    datos.update(over)
    return {k: v for k, v in datos.items() if v is not None}


def _flash(client):
    respuesta = client.get(reverse("centro_list"))
    return [str(m) for m in get_messages(respuesta.wsgi_request)]


# --- Create -----------------------------------------------------------------


def test_options_describe_the_native_form_in_order(provincia, referente, faro):
    otro = _user("sin_grupo")
    data = _client(_user("gestor", "role_cdf_sse")).get(f"{ROOT}options/").json()

    nombres = [campo["name"] for campo in data["fields"]]
    assert nombres[:4] == ["tipo", "nombre", "codigo", "organizacion_asociada"]
    assert nombres[-3:] == ["faro_asociado", "foto", "activo"]
    campos = {campo["name"]: campo for campo in data["fields"]}
    assert campos["tipo"]["widget"] == "select" and campos["tipo"]["required"] is True
    assert campos["organizacion_asociada"]["choices"][0] == {
        "value": "",
        "label": "Seleccionar organización...",
    }
    referentes = [c["value"] for c in campos["referente"]["choices"]]
    assert str(referente.pk) in referentes and str(otro.pk) not in referentes
    assert [c["value"] for c in campos["faro_asociado"]["choices"]] == [
        "",
        str(faro.pk),
    ]
    assert campos["activo"] == {**campos["activo"], "widget": "checkbox", "value": True}
    assert campos["foto"]["widget"] == "file" and campos["foto"]["current"] is None
    assert campos["nombre"]["attrs"] == {"maxlength": "200"}
    assert data["locked"] == [] and data["errors"] == {}


def test_options_with_faro_lock_tipo_and_faro(faro):
    data = (
        _client(_user("gestor", "role_cdf_sse"))
        .get(f"{ROOT}options/", {"faro": faro.pk})
        .json()
    )

    campos = {campo["name"]: campo for campo in data["fields"]}
    assert (
        campos["tipo"]["widget"] == "hidden" and campos["tipo"]["value"] == "adherido"
    )
    assert campos["faro_asociado"]["value"] == str(faro.pk)
    assert data["locked"] == ["tipo", "faro_asociado"]


def test_create_is_open_to_any_view_centro_holder_and_returns_to_the_list(
    provincia, referente
):
    client = _client(_user("solo_view"))

    respuesta = client.post(f"{ROOT}crear/", _payload(provincia, referente))

    assert respuesta.status_code == 201
    centro = Centro.objects.get(codigo="NUEVO-1")
    assert respuesta.json() == {
        "id": centro.pk,
        "message": "Centro creado exitosamente.",
        "redirect": "list",
        "url": "/centrodefamilia/centros/",
    }
    assert (centro.nombre, centro.tipo, centro.referente_id, centro.activo) == (
        "Centro Nuevo",
        "faro",
        referente.pk,
        True,
    )
    assert _flash(client) == ["Centro creado exitosamente."]


def test_invalid_create_answers_400_with_errors_and_saves_nothing(provincia, referente):
    client = _client(_user("gestor", "role_cdf_sse"))

    faltan = client.post(f"{ROOT}crear/", _payload(provincia, referente, nombre=None))
    adherido = client.post(
        f"{ROOT}crear/", _payload(provincia, referente, tipo="adherido")
    )
    coordenada = client.post(
        f"{ROOT}crear/", _payload(provincia, referente, latitud="-34.1")
    )

    assert faltan.status_code == 400
    assert faltan.json()["errors"]["nombre"][0]["code"] == "required"
    campos = {c["name"]: c for c in faltan.json()["fields"]}
    assert campos["codigo"]["value"] == "NUEVO-1"
    assert adherido.json()["non_field_errors"] == [
        "Debe asociar un Centro FARO activo si el centro es ADHERIDO."
    ]
    assert coordenada.json()["non_field_errors"] == [
        "Complete latitud y longitud, o deje ambas vacías."
    ]
    assert not Centro.all_objects.filter(codigo="NUEVO-1").exists()


def test_faro_query_forces_adherido_and_the_faro_over_a_forged_body(
    provincia, referente, faro
):
    client = _client(_user("gestor", "role_cdf_sse"))
    otro_faro = _centro("Faro Dos", provincia)

    respuesta = client.post(
        f"{ROOT}crear/?faro={faro.pk}",
        _payload(provincia, referente, tipo="faro", faro_asociado=str(otro_faro.pk)),
    )

    assert respuesta.status_code == 201
    centro = Centro.objects.get(codigo="NUEVO-1")
    assert (centro.tipo, centro.faro_asociado_id) == ("adherido", faro.pk)


def test_post_without_csrf_is_rejected_without_effects(provincia, referente, faro):
    client = _client(_user("gestor", "role_cdf_sse"), csrf=True)

    crear = client.post(f"{ROOT}crear/", _payload(provincia, referente))
    baja = client.post(f"{ROOT}{faro.pk}/eliminar/")

    assert crear.status_code == baja.status_code == 403
    assert not Centro.objects.filter(codigo="NUEVO-1").exists()
    assert Centro.objects.filter(pk=faro.pk).exists()


# --- Edit -------------------------------------------------------------------


def test_edit_returns_current_values_and_saves_to_the_detail(
    provincia, referente, faro
):
    Centro.objects.filter(pk=faro.pk).update(referente=referente)
    client = _client(referente)

    actual = client.get(f"{ROOT}{faro.pk}/editar/").json()
    campos = {c["name"]: c for c in actual["fields"]}
    assert campos["nombre"]["value"] == "Faro Uno"
    assert campos["referente"]["value"] == str(referente.pk)

    respuesta = client.post(
        f"{ROOT}{faro.pk}/editar/",
        _payload(provincia, referente, nombre="Faro Renombrado", codigo=faro.codigo),
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id": faro.pk,
        "message": "Centro actualizado correctamente.",
        "redirect": "detail",
        "url": f"/centrodefamilia/centros/{faro.pk}/",
    }
    assert Centro.objects.get(pk=faro.pk).nombre == "Faro Renombrado"
    assert _flash(client) == ["Centro actualizado correctamente."]


def test_edit_and_delete_deny_an_active_access_without_fk(provincia, referente, faro):
    acceso = _user("acceso_activo")
    AccesoCDF.objects.create(user=acceso, centro=faro, activo=True)
    client = _client(acceso)

    assert client.get(f"{ROOT}{faro.pk}/").status_code == 200
    for metodo, url in (
        ("get", f"{ROOT}{faro.pk}/editar/"),
        ("post", f"{ROOT}{faro.pk}/editar/"),
        ("get", f"{ROOT}{faro.pk}/eliminar/"),
        ("post", f"{ROOT}{faro.pk}/eliminar/"),
    ):
        datos = _payload(provincia, referente, nombre="X") if metodo == "post" else {}
        assert getattr(client, metodo)(url, datos).status_code == 403, (metodo, url)
        assert client.get(reverse("centro_update", args=[faro.pk])).status_code == 403
    faro.refresh_from_db()
    assert (faro.nombre, faro.deleted_at) == ("Faro Uno", None)


def test_invalid_edit_keeps_the_object_and_reports_errors(provincia, referente, faro):
    client = _client(_user("gestor", "role_cdf_sse"))

    respuesta = client.post(
        f"{ROOT}{faro.pk}/editar/", _payload(provincia, referente, correo="no-mail")
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["errors"]["correo"][0]["code"] == "invalid"
    assert Centro.objects.get(pk=faro.pk).correo == "c@example.com"


def test_missing_centre_is_404_for_edit_and_delete():
    client = _client(_user("gestor", "role_cdf_sse"))
    for url in (f"{ROOT}999999/editar/", f"{ROOT}999999/eliminar/"):
        assert client.get(url).status_code == 404
        assert client.post(url).status_code == 404


# --- Delete -----------------------------------------------------------------


def test_delete_previews_and_soft_deletes_in_cascade(faro):
    actividad = ActividadCentro.objects.create(
        centro=faro,
        actividad=Actividad.objects.create(
            nombre="Fútbol", categoria=Categoria.objects.create(nombre="Deportes")
        ),
        cantidad_personas=5,
        horariosdesde=time(9, 0),
    )
    client = _client(_user("gestor", "role_cdf_sse"))

    previa = client.get(f"{ROOT}{faro.pk}/eliminar/").json()
    assert previa["nombre"] == "Faro Uno"
    assert previa["preview"]["total_afectados"] >= 2
    assert previa["cancel_text"] == "Cancelar"
    assert previa["urls"]["cancel"] == f"/centrodefamilia/centros/{faro.pk}/"

    respuesta = client.post(f"{ROOT}{faro.pk}/eliminar/")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "message": "Centro dado de baja correctamente.",
        "redirect": "list",
        "url": "/centrodefamilia/centros/",
    }
    borrado = Centro.all_objects.get(pk=faro.pk)
    assert borrado.deleted_at is not None and borrado.activo is False
    assert ActividadCentro.all_objects.get(pk=actividad.pk).deleted_at is not None
    assert _flash(client) == ["Centro dado de baja correctamente."]
    assert client.post(f"{ROOT}{faro.pk}/eliminar/").status_code == 404


def test_superuser_and_fk_referente_may_delete(provincia, referente):
    propio = _centro("Propio", provincia, referente=referente)
    ajeno = _centro("Ajeno", provincia)

    assert _client(referente).post(f"{ROOT}{propio.pk}/eliminar/").status_code == 200
    superuser = _user("root_cdf", view=False, superuser=True)
    assert _client(superuser).post(f"{ROOT}{ajeno.pk}/eliminar/").status_code == 200


# --- G1 and methods ---------------------------------------------------------


def test_anonymous_gets_401_and_methods_are_closed(client, faro):
    for metodo, url in (
        ("get", f"{ROOT}options/"),
        ("post", f"{ROOT}crear/"),
        ("post", f"{ROOT}{faro.pk}/editar/"),
        ("post", f"{ROOT}{faro.pk}/eliminar/"),
    ):
        respuesta = getattr(client, metodo)(url)
        assert respuesta.status_code == 401, url
        assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    gestor = _client(_user("gestor", "role_cdf_sse"))
    assert gestor.get(f"{ROOT}crear/").status_code == 405
    assert gestor.post(f"{ROOT}options/").status_code == 405
    assert gestor.put(f"{ROOT}{faro.pk}/editar/").status_code == 405
    assert gestor.delete(f"{ROOT}{faro.pk}/eliminar/").status_code == 405


def test_without_view_centro_every_action_is_403(provincia, referente, faro):
    client = _client(_user("sin_view", "role_cdf_sse", view=False))
    for metodo, url in (
        ("get", f"{ROOT}options/"),
        ("post", f"{ROOT}crear/"),
        ("get", f"{ROOT}{faro.pk}/editar/"),
        ("post", f"{ROOT}{faro.pk}/eliminar/"),
    ):
        assert getattr(client, metodo)(url).status_code == 403, url
    assert Centro.objects.filter(pk=faro.pk).exists()
