"""Web API (G1 v1) of the comedor create/edit form (CO07.02).

The endpoints run the native ``ComedorCreateView``/``ComedorUpdateView``; these
tests check the projection of the real form and the persisted effects, and that
a rejected request leaves everything unchanged.
"""

from io import BytesIO

import pytest
from PIL import Image
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from comedores.models import (
    Comedor,
    EstadoActividad,
    EstadoDetalle,
    EstadoHistorial,
    EstadoProceso,
    ImagenComedor,
    Referente,
)
from core import web_gate
from core.models import Provincia

pytestmark = pytest.mark.django_db
ROOT = "/api/web/comedores/comedores/"


def _png():
    buffer = BytesIO()
    Image.new("RGB", (2, 2), "red").save(buffer, "PNG")
    return buffer.getvalue()


PNG = _png()


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _client(username, *codenames, **flags):
    usuario = _ready(
        get_user_model().objects.create_user(username, password="x", **flags)
    )
    for codename in codenames:
        usuario.user_permissions.add(Permission.objects.get(codename=codename))
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="estados")
def estados_fixture():
    actividad = EstadoActividad.objects.create(estado="Activo")
    proceso = EstadoProceso.objects.create(
        estado="En ejecución", estado_actividad=actividad
    )
    detalle = EstadoDetalle.objects.create(estado="Sin novedad", estado_proceso=proceso)
    provincia = Provincia.objects.create(nombre="Provincia Form")
    return actividad, proceso, detalle, provincia


@pytest.fixture(name="gestor")
def gestor_fixture():
    return _client("gestor_form_comedor", "add_comedor", "change_comedor")


def _datos(estados, **extra):
    actividad, proceso, detalle, provincia = estados
    datos = {
        "nombre": "Comedor Nuevo",
        "es_caritas": "False",
        "provincia": provincia.pk,
        "estado_general": actividad.pk,
        "subestado": proceso.pk,
        "motivo": detalle.pk,
        "referente-nombre": "Ana",
        "referente-apellido": "Pérez",
        "referente-celular": "1155550000",
    }
    datos.update(extra)
    return datos


def test_create_form_projects_the_real_fields_in_template_order(gestor, estados):
    datos = gestor.get(f"{ROOT}formulario/").json()["form"]

    nombres = [f["name"] for f in datos["fields"]]
    assert nombres[:3] == ["nombre", "id_externo", "tipocomedor"]
    assert nombres[-6:] == [
        f"referente-{n}"
        for n in ("nombre", "apellido", "mail", "celular", "documento", "funcion")
    ]
    assert "estado_validacion" not in nombres
    assert "responsable_tarjeta_nombre" not in nombres
    campos = {f["name"]: f for f in datos["fields"]}
    assert campos["estado_general"]["required"] is True
    assert [o["label"] for o in campos["estado_general"]["options"]] == [
        "Seleccione un estado general",
        "Activo",
    ]
    assert campos["subestado"]["options"] == [
        {"value": "", "label": "Seleccione un subestado"}
    ]
    assert [o["value"] for o in campos["es_caritas"]["options"]] == [
        "",
        "True",
        "False",
    ]
    assert campos["comienzo"]["attrs"]["min"] == "1900"
    assert campos["provincia"]["section"] == "ubicacion"
    assert (
        datos["estado_tree"][str(estados[0].pk)]["procesos"][0]["label"]
        == "En ejecución"
    )
    assert datos["foto_legajo"]["file"] is None and datos["imagenes"] == []
    assert datos["foto_legajo"]["initial_text"] == "Actualmente"
    assert datos["urls"]["cancel"] == "/comedores/listar"


def test_create_saves_comedor_referente_estado_history_and_images(gestor, estados):
    antes = Comedor.objects.count()
    respuesta = gestor.post(
        f"{ROOT}crear/",
        {
            **_datos(estados),
            "imagenes": [SimpleUploadedFile("a.png", PNG, "image/png")],
        },
    )

    assert respuesta.status_code == 201, respuesta.content
    comedor = Comedor.objects.get(nombre="Comedor Nuevo")
    assert respuesta.json() == {"redirect": f"/comedores/{comedor.pk}"}
    assert Comedor.objects.count() == antes + 1
    assert comedor.referente.nombre == "Ana"
    assert comedor.referente.apellido == "Pérez"
    assert comedor.es_caritas is False
    assert EstadoHistorial.objects.filter(comedor=comedor).count() == 1
    assert ImagenComedor.objects.filter(comedor=comedor).count() == 1


def test_a_rejected_create_writes_nothing_and_returns_the_native_errors(
    gestor, estados
):
    antes = (Comedor.objects.count(), Referente.objects.count())

    respuesta = gestor.post(
        f"{ROOT}crear/",
        _datos(
            estados, nombre="", **{"referente-mail": "no-es-un-mail", "latitud": "95"}
        ),
    )

    assert respuesta.status_code == 400
    datos = respuesta.json()
    assert datos["errors"]["nombre"] == ["Este campo es requerido."]
    assert datos["errors"]["latitud"]
    assert datos["errors"]["referente-mail"]
    campos = {f["name"]: f for f in datos["form"]["fields"]}
    assert campos["latitud"]["value"] == "95"
    assert campos["referente-nombre"]["value"] == "Ana"
    assert (Comedor.objects.count(), Referente.objects.count()) == antes


def test_a_subestado_of_another_estado_is_rejected_without_writing(gestor, estados):
    otra = EstadoActividad.objects.create(estado="Otra")
    ajeno = EstadoProceso.objects.create(estado="Ajeno", estado_actividad=otra)
    antes = Comedor.objects.count()

    respuesta = gestor.post(f"{ROOT}crear/", _datos(estados, subestado=ajeno.pk))

    assert respuesta.status_code == 400
    assert respuesta.json()["errors"]["subestado"]
    assert Comedor.objects.count() == antes


def test_fields_the_template_does_not_render_cannot_be_set(gestor, estados):
    respuesta = gestor.post(
        f"{ROOT}crear/",
        _datos(
            estados,
            estado_validacion="Validado",
            responsable_tarjeta_nombre="No debe guardarse",
        ),
    )

    assert respuesta.status_code == 201, respuesta.content
    comedor = Comedor.objects.get(nombre="Comedor Nuevo")
    assert comedor.estado_validacion != "Validado"
    assert not comedor.responsable_tarjeta_nombre


def test_edit_keeps_the_dupla_updates_the_referente_and_deletes_marked_images(
    gestor, estados
):
    gestor.post(
        f"{ROOT}crear/",
        {
            **_datos(estados),
            "imagenes": [SimpleUploadedFile("a.png", PNG, "image/png")],
        },
    )
    comedor = Comedor.objects.get(nombre="Comedor Nuevo")
    imagen = ImagenComedor.objects.get(comedor=comedor)
    formulario = gestor.get(f"{ROOT}{comedor.pk}/formulario/").json()["form"]
    assert formulario["comedor_id"] == comedor.pk
    assert [i["id"] for i in formulario["imagenes"]] == [imagen.pk]
    assert formulario["urls"]["cancel"] == f"/comedores/{comedor.pk}"
    valores = {f["name"]: f["value"] for f in formulario["fields"]}
    assert valores["nombre"] == "Comedor Nuevo"
    assert valores["referente-nombre"] == "Ana"
    assert valores["estado_general"] == str(estados[0].pk)

    respuesta = gestor.post(
        f"{ROOT}{comedor.pk}/editar/",
        {
            **_datos(
                estados, nombre="Comedor Editado", **{"referente-nombre": "Beatriz"}
            ),
            f"imagen_ciudadano-borrar-{imagen.pk}": "on",
        },
    )

    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json() == {"redirect": f"/comedores/{comedor.pk}"}
    comedor.refresh_from_db()
    assert comedor.nombre == "Comedor Editado"
    assert comedor.referente.nombre == "Beatriz"
    assert not ImagenComedor.objects.filter(pk=imagen.pk).exists()
    # The estado did not change: no new history row.
    assert EstadoHistorial.objects.filter(comedor=comedor).count() == 1


def test_a_rejected_edit_leaves_the_comedor_images_and_referente_unchanged(
    gestor, estados
):
    gestor.post(
        f"{ROOT}crear/",
        {
            **_datos(estados),
            "imagenes": [SimpleUploadedFile("a.png", PNG, "image/png")],
        },
    )
    comedor = Comedor.objects.get(nombre="Comedor Nuevo")
    imagen = ImagenComedor.objects.get(comedor=comedor)

    respuesta = gestor.post(
        f"{ROOT}{comedor.pk}/editar/",
        {
            **_datos(estados, nombre="", **{"referente-nombre": "Cambiado"}),
            f"imagen_ciudadano-borrar-{imagen.pk}": "on",
        },
    )

    assert respuesta.status_code == 400
    comedor.refresh_from_db()
    assert comedor.nombre == "Comedor Nuevo"
    assert comedor.referente.nombre == "Ana"
    assert ImagenComedor.objects.filter(pk=imagen.pk).exists()


def test_edit_of_an_unknown_comedor_is_404_and_writes_nothing(gestor, estados):
    antes = Comedor.objects.count()

    assert gestor.get(f"{ROOT}999999/formulario/").status_code == 404
    assert gestor.post(f"{ROOT}999999/editar/", _datos(estados)).status_code == 404
    assert Comedor.objects.count() == antes


def test_each_route_needs_its_native_permission(estados):
    solo_crear = _client("solo_crear_comedor", "add_comedor")
    solo_editar = _client("solo_editar_comedor", "change_comedor")
    existente = Comedor.objects.create(nombre="Existente")
    antes = Comedor.objects.count()

    assert solo_editar.get(f"{ROOT}formulario/").status_code == 403
    assert solo_editar.post(f"{ROOT}crear/", _datos(estados)).status_code == 403
    assert solo_crear.get(f"{ROOT}{existente.pk}/formulario/").status_code == 403
    assert (
        solo_crear.post(f"{ROOT}{existente.pk}/editar/", _datos(estados)).status_code
        == 403
    )
    assert solo_crear.get(f"{ROOT}formulario/").status_code == 200
    assert solo_editar.get(f"{ROOT}{existente.pk}/formulario/").status_code == 200
    assert Comedor.objects.count() == antes
    assert Comedor.objects.get(pk=existente.pk).nombre == "Existente"


def test_methods_csrf_and_anonymous(gestor, estados):
    assert gestor.post(f"{ROOT}formulario/").status_code == 405
    assert gestor.get(f"{ROOT}crear/").status_code == 405
    usuario = _ready(get_user_model().objects.create_user("csrf_form", password="x"))
    usuario.user_permissions.add(Permission.objects.get(codename="add_comedor"))
    client = Client(enforce_csrf_checks=True)
    client.force_login(usuario)
    antes = Comedor.objects.count()

    assert client.post(f"{ROOT}crear/", _datos(estados)).status_code == 403
    anonimo = Client()
    respuesta = anonimo.get(f"{ROOT}formulario/")
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert anonimo.post(f"{ROOT}crear/", _datos(estados)).status_code == 401
    assert Comedor.objects.count() == antes


def test_pending_web_requirement_is_reported_and_a_forged_header_is_ignored(estados):
    usuario = get_user_model().objects.create_superuser("pendiente_form", password="x")
    usuario.profile.acceso_web = True
    usuario.profile.must_change_password = True
    usuario.profile.save()
    client = Client()
    client.force_login(usuario)
    url = f"{ROOT}crear/"
    falso = web_gate.sign(
        audience="comedores",
        user_pk=usuario.pk,
        session_key=client.cookies["sessionid"].value,
        method="POST",
        target=url,
    )
    antes = Comedor.objects.count()

    respuesta = client.post(
        url, _datos(estados), HTTP_X_SISOC_WEB_GATE=falso, RAW_URI=url
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["state"] == "password_change_required"
    assert Comedor.objects.count() == antes


def test_a_failure_while_saving_rolls_back_and_shows_the_native_message(
    gestor, estados, monkeypatch
):
    def falla(*_args, **_kwargs):
        raise RuntimeError("storage caido")

    monkeypatch.setattr("comedores.views.comedor.ComedorService.create_imagenes", falla)
    antes = (Comedor.objects.count(), Referente.objects.count())

    respuesta = gestor.post(
        f"{ROOT}crear/",
        {
            **_datos(estados),
            "imagenes": [SimpleUploadedFile("a.png", PNG, "image/png")],
        },
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["non_field_errors"] == [
        "Error al guardar el comedor: storage caido"
    ]
    assert (Comedor.objects.count(), Referente.objects.count()) == antes


def test_the_photo_can_be_replaced_and_cleared_like_the_native_widget(gestor, estados):
    gestor.post(
        f"{ROOT}crear/",
        {
            **_datos(estados),
            "foto_legajo": SimpleUploadedFile("f.png", PNG, "image/png"),
        },
    )
    comedor = Comedor.objects.get(nombre="Comedor Nuevo")
    assert comedor.foto_legajo
    formulario = gestor.get(f"{ROOT}{comedor.pk}/formulario/").json()["form"]
    assert formulario["foto_legajo"]["file"]["name"] == comedor.foto_legajo.name
    assert formulario["foto_legajo"]["clear_label"] == "Eliminar"

    gestor.post(
        f"{ROOT}{comedor.pk}/editar/", {**_datos(estados), "foto_legajo-clear": "on"}
    )

    comedor.refresh_from_db()
    assert not comedor.foto_legajo
