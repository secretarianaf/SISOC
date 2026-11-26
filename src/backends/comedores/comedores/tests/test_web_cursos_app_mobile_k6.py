"""Web API (G1 v1) of the global app-mobile course catalog (CO04.01).

``/api/web/comedores/cursos-app-mobile/`` runs the native views of
``comedores.views.cursos_app_mobile``: 20 per page, ``CursoAppMobileForm`` with the image
upload, the actor stamps and the soft delete. A rejected request must write nothing.
"""

from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image

from comedores.models import CursoAppMobile

ROOT = "/api/web/comedores/cursos-app-mobile/"

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


def _permiso(app, codename):
    """Role codes are not model permissions: they live on the ``Group`` content type."""
    existente = Permission.objects.filter(
        content_type__app_label=app, codename=codename
    ).first()
    return existente or Permission.objects.create(
        content_type=ContentType.objects.get_for_model(Group),
        codename=codename,
        name=codename,
    )


def _usuario(nombre, *codes, **extra):
    usuario = get_user_model().objects.create_user(nombre, **extra)
    profile = usuario.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    for code in codes:
        app, codename = code.split(".")
        usuario.user_permissions.add(_permiso(app, codename))
    return usuario


def _cliente(usuario, **kwargs):
    client = Client(**kwargs)
    client.force_login(usuario)
    return client


@pytest.fixture(name="admin")
def admin_fixture():
    return _usuario("admin_k6k", "auth.role_admin", first_name="Ana", last_name="Pérez")


@pytest.fixture(name="web")
def web_fixture(admin):
    return _cliente(admin)


def _curso(**extra):
    datos = {
        "nombre": "Curso de cocina",
        "link": "https://cursos.example/cocina",
        "programa_objetivo": "pnud",
        "orden": 1,
    }
    datos.update(extra)
    return CursoAppMobile.objects.create(**datos)


def _datos(**extra):
    datos = {
        "nombre": "Curso nuevo",
        "link": "https://cursos.example/nuevo",
        "descripcion": "Texto corto",
        "programa_objetivo": "ambos",
        "es_recomendado": "on",
        "orden": "4",
        "activo": "on",
    }
    datos.update(extra)
    return datos


def _png(nombre="curso.png"):
    buffer = BytesIO()
    Image.new("RGB", (4, 4), "red").save(buffer, "PNG")
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type="image/png")


def _estado():
    return list(
        CursoAppMobile.all_objects.order_by("pk").values_list(
            "pk",
            "nombre",
            "link",
            "imagen",
            "descripcion",
            "programa_objetivo",
            "es_recomendado",
            "activo",
            "orden",
            "deleted_at",
            "modificado_por_id",
        )
    )


def _campos(data):
    return {campo["name"]: campo for campo in data["fields"]}


# --- Access --------------------------------------------------------------------


def test_each_endpoint_keeps_the_native_permission_and_requires_a_session(admin):
    curso = _curso()
    urls = [
        ROOT,
        f"{ROOT}crear/",
        f"{ROOT}{curso.pk}/editar/",
        f"{ROOT}{curso.pk}/eliminar/",
    ]
    sin_rol = _cliente(_usuario("sin_rol_k6k"))

    for url in urls:
        assert Client().get(url).status_code in (401, 403), url
        assert sin_rol.get(url).status_code == 403, url
        assert _cliente(admin).get(url).status_code == 200, url
    for url in urls[1:]:
        assert Client().post(url, {}).status_code in (401, 403), url
        assert sin_rol.post(url, _datos()).status_code == 403, url
    assert CursoAppMobile.objects.count() == 1


def test_write_requires_csrf_and_a_form_content_type(admin):
    curso = _curso()
    antes = _estado()

    estricto = _cliente(admin, enforce_csrf_checks=True)
    assert estricto.post(f"{ROOT}crear/", _datos()).status_code == 403
    assert estricto.post(f"{ROOT}{curso.pk}/eliminar/").status_code == 403
    assert (
        _cliente(admin)
        .post(f"{ROOT}crear/", data="{}", content_type="application/json")
        .status_code
        == 415
    )
    assert _estado() == antes


# --- List ----------------------------------------------------------------------


def test_list_is_global_20_per_page_and_projects_the_native_columns(web):
    for numero in range(21):
        _curso(nombre=f"Curso {numero:02d}", orden=numero)
    ultimo = CursoAppMobile.objects.order_by("-pk").first()
    ultimo.activo = False
    ultimo.es_recomendado = True
    ultimo.imagen = "comedores/cursos_app_mobile/x.png"
    ultimo.programa_objetivo = "alimentar_comunidad"
    ultimo.save()

    primera = web.get(ROOT).json()
    segunda = web.get(f"{ROOT}?page=2").json()

    assert len(primera["results"]) == 20
    assert len(segunda["results"]) == 1
    assert primera["page"]["count"] == 21
    assert primera["page"]["is_paginated"] is True
    assert primera["page"]["next"] == 2
    assert segunda["page"]["previous"] == 1
    assert primera["urls"] == {
        "crear": "/comedores/configuracion/cursos-app-mobile/crear/"
    }
    fila = next(
        f for f in primera["results"] + segunda["results"] if f["id"] == ultimo.pk
    )
    assert fila == {
        "id": ultimo.pk,
        "nombre": ultimo.nombre,
        "programa": "Alimentar Comunidad",
        "link": "https://cursos.example/cocina",
        "orden": ultimo.orden,
        "es_recomendado": True,
        "activo": False,
        "tiene_imagen": True,
        "urls": {
            "editar": f"/comedores/configuracion/cursos-app-mobile/{ultimo.pk}/editar/",
            "eliminar": f"/comedores/configuracion/cursos-app-mobile/{ultimo.pk}/eliminar/",
        },
    }
    assert web.get(f"{ROOT}?page=3").status_code == 404


def test_empty_list_and_soft_deleted_courses_are_not_listed(web):
    assert web.get(ROOT).json()["results"] == []
    curso = _curso()
    curso.delete()

    assert web.get(ROOT).json()["results"] == []
    assert CursoAppMobile.all_objects.count() == 1


# --- Create --------------------------------------------------------------------


def test_create_form_projects_the_native_form_as_p(web):
    data = web.get(f"{ROOT}crear/").json()

    assert data["edit_mode"] is False
    assert [c["name"] for c in data["fields"]] == [
        "nombre",
        "link",
        "imagen",
        "descripcion",
        "programa_objetivo",
        "es_recomendado",
        "orden",
        "activo",
    ]
    campos = _campos(data)
    assert campos["nombre"]["label"] == "Nombre"
    assert (campos["nombre"]["type"], campos["nombre"]["max_length"]) == ("text", 255)
    assert campos["nombre"]["html_required"] is True
    assert (campos["link"]["type"], campos["link"]["max_length"]) == ("url", 500)
    assert (campos["imagen"]["type"], campos["imagen"]["accept"]) == ("file", "image/*")
    assert campos["imagen"]["html_required"] is False
    assert campos["descripcion"]["max_length"] == 300
    assert campos["programa_objetivo"]["choices"] == [
        {"value": "", "label": "Seleccionar programa"},
        {"value": "pnud", "label": "PNUD"},
        {"value": "alimentar_comunidad", "label": "Alimentar Comunidad"},
        {"value": "ambos", "label": "PNUD y Alimentar Comunidad"},
    ]
    assert (
        campos["orden"]["type"],
        campos["orden"]["min"],
        campos["orden"]["value"],
    ) == (
        "number",
        "0",
        "0",
    )
    assert campos["es_recomendado"]["value"] is False
    assert campos["activo"]["value"] is True
    assert data["urls"] == {"list": "/comedores/configuracion/cursos-app-mobile/"}


def test_create_persists_the_course_the_image_the_actor_and_the_message(web, admin):
    respuesta = web.post(f"{ROOT}crear/", {**_datos(), "imagen": _png()})

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": "/comedores/configuracion/cursos-app-mobile/",
    }
    curso = CursoAppMobile.objects.get()
    assert curso.nombre == "Curso nuevo"
    assert curso.programa_objetivo == "ambos"
    assert (curso.es_recomendado, curso.activo, curso.orden) == (True, True, 4)
    assert curso.imagen.name.startswith("comedores/cursos_app_mobile/")
    assert curso.creado_por == admin
    assert curso.modificado_por == admin
    assert [m["message"] for m in web.get(ROOT).json()["messages"]] == [
        "Curso para app mobile creado correctamente."
    ]


def test_create_without_image_or_flags_keeps_the_native_defaults(web):
    web.post(
        f"{ROOT}crear/",
        {
            "nombre": "Mínimo",
            "link": "https://cursos.example/min",
            "programa_objetivo": "pnud",
            "orden": "0",
        },
    )

    curso = CursoAppMobile.objects.get()
    assert not curso.imagen
    assert (curso.es_recomendado, curso.activo) == (False, False)


def test_create_rejections_are_the_native_ones_and_write_nothing(web):
    antes = _estado()
    casos = [
        ({"nombre": ""}, "nombre", "Este campo es requerido."),
        ({"link": ""}, "link", "Este campo es requerido."),
        ({"link": "no-es-url"}, "link", None),
        ({"programa_objetivo": ""}, "programa_objetivo", "Este campo es requerido."),
        ({"programa_objetivo": "otro"}, "programa_objetivo", None),
        ({"orden": "-1"}, "orden", None),
        ({"orden": ""}, "orden", "Este campo es requerido."),
        ({"nombre": "x" * 256}, "nombre", None),
        ({"descripcion": "y" * 301}, "descripcion", None),
        ({"imagen": SimpleUploadedFile("no.png", b"no es imagen")}, "imagen", None),
    ]
    for cambios, campo, mensaje in casos:
        respuesta = web.post(f"{ROOT}crear/", _datos(**cambios))
        assert respuesta.status_code == 400, cambios
        errores = _campos(respuesta.json())[campo]["errors"]
        assert errores, cambios
        if mensaje:
            assert errores == [mensaje], cambios
        # The bound values come back so nothing typed is lost.
        assert _campos(respuesta.json())["descripcion"]["value"] == cambios.get(
            "descripcion", "Texto corto"
        )
        assert _estado() == antes, cambios
    assert not list(CursoAppMobile.all_objects.all())


# --- Edit ----------------------------------------------------------------------


def test_edit_shows_the_stored_course_and_updates_it_with_the_actor(web, admin):
    otro = _usuario("otro_k6k")
    curso = _curso(creado_por=otro, modificado_por=otro, es_recomendado=True)

    campos = _campos(web.get(f"{ROOT}{curso.pk}/editar/").json())
    assert web.get(f"{ROOT}{curso.pk}/editar/").json()["edit_mode"] is True
    assert campos["nombre"]["value"] == "Curso de cocina"
    assert campos["programa_objetivo"]["value"] == "pnud"
    assert campos["es_recomendado"]["value"] is True

    respuesta = web.post(
        f"{ROOT}{curso.pk}/editar/",
        _datos(nombre="Editado", orden="9", imagen=_png("nueva.png")),
    )

    assert respuesta.json()["ok"] is True
    curso.refresh_from_db()
    assert (curso.nombre, curso.orden, curso.programa_objetivo) == (
        "Editado",
        9,
        "ambos",
    )
    assert curso.imagen.name.startswith("comedores/cursos_app_mobile/")
    assert curso.modificado_por == admin
    assert curso.creado_por == otro
    assert [m["message"] for m in web.get(ROOT).json()["messages"]] == [
        "Curso para app mobile actualizado correctamente."
    ]


def test_edit_rejection_and_missing_course_leave_everything_unchanged(web):
    curso = _curso()
    antes = _estado()

    rechazo = web.post(f"{ROOT}{curso.pk}/editar/", _datos(nombre=""))

    assert rechazo.status_code == 400
    assert _campos(rechazo.json())["nombre"]["errors"] == ["Este campo es requerido."]
    assert _campos(rechazo.json())["link"]["value"] == "https://cursos.example/nuevo"
    assert web.get(f"{ROOT}999999/editar/").status_code == 404
    assert web.post(f"{ROOT}999999/editar/", _datos()).status_code == 404
    curso.delete()
    antes = _estado()
    assert web.get(f"{ROOT}{curso.pk}/editar/").status_code == 404
    assert web.post(f"{ROOT}{curso.pk}/editar/", _datos()).status_code == 404
    assert _estado() == antes


# --- Delete --------------------------------------------------------------------


def test_delete_confirmation_shows_the_course_and_the_post_is_a_soft_delete(web, admin):
    curso = _curso()
    otro = _curso(nombre="Se queda")

    confirmacion = web.get(f"{ROOT}{curso.pk}/eliminar/").json()
    assert confirmacion["nombre"] == "Curso de cocina"
    assert confirmacion["cancel_url"] == "/comedores/configuracion/cursos-app-mobile/"
    assert CursoAppMobile.objects.count() == 2

    respuesta = web.post(f"{ROOT}{curso.pk}/eliminar/")

    assert respuesta.json() == {
        "ok": True,
        "redirect": "/comedores/configuracion/cursos-app-mobile/",
    }
    fila = CursoAppMobile.all_objects.get(pk=curso.pk)
    assert fila.deleted_at is not None
    assert fila.deleted_by == admin
    assert CursoAppMobile.all_objects.count() == 2
    assert CursoAppMobile.all_objects.get(pk=otro.pk).deleted_at is None
    # Both native messages wait for the list.
    assert [m["message"] for m in web.get(ROOT).json()["messages"]] == [
        "Baja lógica realizada correctamente.",
        "Curso para app mobile eliminado correctamente.",
    ]
    assert [f["id"] for f in web.get(ROOT).json()["results"]] == [otro.pk]
    assert web.get(f"{ROOT}{curso.pk}/eliminar/").status_code == 404
    assert web.post(f"{ROOT}{curso.pk}/eliminar/").status_code == 404
    assert web.post(f"{ROOT}999999/eliminar/").status_code == 404
