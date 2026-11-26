"""Web API (G1 v1) of the comedor observation screens (CO06).

``/api/web/comedores/observaciones/`` runs the native views of
``comedores.views.observacion``: scoped comedor, server-side author and date, soft
delete. A rejected request must write nothing.
"""

import json
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from django.utils import timezone
from django.utils.html import escape

from comedores.models import Comedor, Observacion
from duplas.models import Dupla
from users.services import UserPermissionService

ROOT = "/api/web/comedores/observaciones/"
CODIGOS = [
    "comedores.add_observacion",
    "comedores.view_observacion",
    "comedores.change_observacion",
    "comedores.delete_observacion",
]

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _tecnico_sin_coordinacion(monkeypatch):
    """The scope of a technician: only the comedores of its own dupla."""
    monkeypatch.setattr(
        UserPermissionService,
        "es_tecnico_o_abogado",
        staticmethod(lambda _user: True),
    )
    monkeypatch.setattr(
        UserPermissionService,
        "get_coordinador_duplas",
        staticmethod(lambda _user: (False, [])),
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
        usuario.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    return usuario


def _cliente(usuario, **kwargs):
    client = Client(**kwargs)
    client.force_login(usuario)
    return client


@pytest.fixture(name="tecnico")
def tecnico_fixture():
    return _usuario("tecnico_k4", *CODIGOS, first_name="Ana", last_name="Pérez")


@pytest.fixture(name="web")
def web_fixture(tecnico):
    return _cliente(tecnico)


@pytest.fixture(name="comedor")
def comedor_fixture(tecnico):
    dupla = Dupla.objects.create(
        nombre="Dupla K4", estado="Activo", abogado=_usuario("abogado_k4")
    )
    dupla.tecnico.add(tecnico)
    return Comedor.objects.create(nombre="Comedor K4", dupla=dupla)


@pytest.fixture(name="ajeno")
def ajeno_fixture():
    otra = Dupla.objects.create(
        nombre="Otra dupla", estado="Activo", abogado=_usuario("abogado_otra_k4")
    )
    return Comedor.objects.create(nombre="Fuera del alcance", dupla=otra)


def _observacion(comedor, **extra):
    datos = {
        "comedor": comedor,
        "observador": "Luis Gómez",
        "observacion": "Texto original",
        "fecha_visita": timezone.now() - timedelta(days=30),
    }
    datos.update(extra)
    return Observacion.objects.create(**datos)


def _urls(comedor, observacion):
    return {
        "crear": f"{ROOT}comedor/{comedor.pk}/crear/",
        "detalle": f"{ROOT}{observacion.pk}/",
        "editar": f"{ROOT}{observacion.pk}/editar/",
        "eliminar": f"{ROOT}{observacion.pk}/eliminar/",
    }


# --- Access --------------------------------------------------------------------


def test_each_endpoint_keeps_the_native_permission_and_requires_a_session(comedor):
    observacion = _observacion(comedor)
    urls = _urls(comedor, observacion)
    permiso = {
        "crear": "comedores.add_observacion",
        "detalle": "comedores.view_observacion",
        "editar": "comedores.change_observacion",
        "eliminar": "comedores.delete_observacion",
    }

    for nombre, url in urls.items():
        assert Client().get(url).status_code in (401, 403), nombre
        asignado = _usuario(f"con_{nombre}_k4", permiso[nombre])
        resto = _usuario(
            f"sin_{nombre}_k4", *(c for c in CODIGOS if c != permiso[nombre])
        )
        assert _cliente(resto).get(url).status_code == 403, nombre
        # The user is not in the dupla: the native scope answers 404, after the permission.
        assert _cliente(asignado).get(url).status_code == 404, nombre
    assert Observacion.objects.count() == 1


# --- Create --------------------------------------------------------------------


def test_create_form_projects_the_native_page(web, comedor, ajeno):
    data = web.get(f"{ROOT}comedor/{comedor.pk}/crear/").json()

    assert data["comedor"] == {
        "id": comedor.pk,
        "nombre": "Comedor K4",
        "url": f"/comedores/{comedor.pk}",
    }
    assert data["observacion_id"] is None
    assert data["field"] == {
        "name": "observacion",
        "label": "Observación",
        "required": True,
        "rows": 4,
        "placeholder": "Describa la observación",
    }
    assert data["value"] == ""
    assert data["errors"] == {}
    assert web.get(f"{ROOT}comedor/{ajeno.pk}/crear/").status_code == 404


def test_create_sets_the_server_side_fields_and_redirects_to_the_detail(
    web, comedor, tecnico
):
    antes = timezone.now()

    respuesta = web.post(
        f"{ROOT}comedor/{comedor.pk}/crear/",
        {"observacion": "Nueva observación", "observador": "Falso", "comedor": "999"},
    )

    creada = Observacion.objects.get()
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/comedores/observacion/{creada.pk}",
    }
    assert creada.comedor_id == comedor.pk
    assert creada.observacion == "Nueva observación"
    assert creada.observador == "Ana Pérez"
    assert antes <= creada.fecha_visita <= timezone.now()


def test_create_follows_a_local_next_and_ignores_an_external_one(web, comedor):
    url = f"{ROOT}comedor/{comedor.pk}/crear/"

    local = web.post(f"{url}?next=/comedores/{comedor.pk}", {"observacion": "a"})
    externo = web.post(f"{url}?next=https://externo.example/x", {"observacion": "b"})

    assert local.json()["redirect"] == f"/comedores/{comedor.pk}"
    assert externo.json()["redirect"].startswith("/comedores/observacion/")
    assert Observacion.objects.count() == 2


def test_create_rejects_an_invalid_form_and_writes_nothing(web, comedor):
    respuesta = web.post(f"{ROOT}comedor/{comedor.pk}/crear/", {"observacion": ""})

    assert respuesta.status_code == 400
    assert respuesta.json()["errors"]["observacion"][0]["code"] == "required"
    assert Observacion.objects.count() == 0


def test_create_refuses_other_scope_json_and_missing_csrf_without_writing(
    web, tecnico, comedor, ajeno
):
    json_body = web.post(
        f"{ROOT}comedor/{comedor.pk}/crear/",
        json.dumps({"observacion": "x"}),
        content_type="application/json",
    )
    sin_csrf = _cliente(tecnico, enforce_csrf_checks=True).post(
        f"{ROOT}comedor/{comedor.pk}/crear/", {"observacion": "x"}
    )

    assert (
        web.post(f"{ROOT}comedor/{ajeno.pk}/crear/", {"observacion": "x"}).status_code
        == 404
    )
    assert json_body.status_code == 415
    assert sin_csrf.status_code == 403
    assert Observacion.objects.count() == 0


# --- Detail --------------------------------------------------------------------


def test_detail_projects_the_native_card(web, comedor, ajeno):
    observacion = _observacion(comedor)
    fuera = _observacion(ajeno)

    data = web.get(f"{ROOT}{observacion.pk}/").json()

    assert data["id"] == observacion.pk
    assert data["comedor"]["nombre"] == "Comedor K4"
    assert data["observador"] == "Luis Gómez"
    assert data["observacion"] == "Texto original"
    assert data["urls"] == {
        "comedores": "/comedores/listar",
        "editar": f"/comedores/observacion/{observacion.pk}/editar",
        "eliminar": f"/comedores/observacion/{observacion.pk}/eliminar",
    }
    # The date is the one the native template prints (localized, local time).
    nativo = web.get(f"/comedores/observacion/{observacion.pk}")
    assert escape(data["fecha"]) in nativo.content.decode()
    assert web.get(f"{ROOT}{fuera.pk}/").status_code == 404
    assert web.get(f"{ROOT}999999/").status_code == 404


# --- Edit ----------------------------------------------------------------------


def test_edit_form_projects_the_instance(web, comedor, ajeno):
    observacion = _observacion(comedor)
    fuera = _observacion(ajeno)

    data = web.get(f"{ROOT}{observacion.pk}/editar/").json()

    assert data["observacion_id"] == observacion.pk
    assert data["value"] == "Texto original"
    assert data["comedor"]["id"] == comedor.pk
    assert web.get(f"{ROOT}{fuera.pk}/editar/").status_code == 404


def test_edit_changes_the_visible_author_and_date_like_the_native_view(web, comedor):
    observacion = _observacion(comedor)
    antes = timezone.now()

    respuesta = web.post(
        f"{ROOT}{observacion.pk}/editar/", {"observacion": "Texto editado"}
    )

    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/comedores/observacion/{observacion.pk}",
    }
    observacion.refresh_from_db()
    assert observacion.observacion == "Texto editado"
    assert observacion.observador == "Ana Pérez"
    assert observacion.fecha_visita >= antes
    assert observacion.comedor_id == comedor.pk


def test_edit_rejections_leave_the_row_untouched(web, tecnico, comedor, ajeno):
    observacion = _observacion(comedor)
    fuera = _observacion(ajeno)

    vacia = web.post(f"{ROOT}{observacion.pk}/editar/", {"observacion": ""})
    ajena = web.post(f"{ROOT}{fuera.pk}/editar/", {"observacion": "Hack"})
    sin_csrf = _cliente(tecnico, enforce_csrf_checks=True).post(
        f"{ROOT}{observacion.pk}/editar/", {"observacion": "Hack"}
    )

    assert vacia.status_code == 400
    assert ajena.status_code == 404
    assert sin_csrf.status_code == 403
    for fila in (observacion, fuera):
        fila.refresh_from_db()
        assert (fila.observacion, fila.observador) in (
            ("Texto original", "Luis Gómez"),
        )


# --- Delete --------------------------------------------------------------------


def test_delete_confirmation_and_soft_delete_with_the_native_message(
    web, comedor, tecnico
):
    observacion = _observacion(comedor)

    confirmacion = web.get(f"{ROOT}{observacion.pk}/eliminar/").json()

    assert confirmacion["object_name"] == str(observacion).upper()
    assert confirmacion["confirm_text"] == "Dar de baja"
    assert confirmacion["cancel_url"] == f"/comedores/observacion/{observacion.pk}"
    assert confirmacion["comedor"]["nombre"] == "Comedor K4"
    assert Observacion.objects.count() == 1

    respuesta = web.post(f"{ROOT}{observacion.pk}/eliminar/")

    assert respuesta.json() == {"ok": True, "redirect": f"/comedores/{comedor.pk}"}
    assert not Observacion.objects.filter(pk=observacion.pk).exists()
    fila = Observacion.all_objects.get(pk=observacion.pk)
    assert fila.deleted_at is not None
    assert fila.deleted_by_id == tecnico.pk
    assert web.get(f"{ROOT}{observacion.pk}/eliminar/").status_code == 404


def test_delete_rejections_leave_the_row_untouched(tecnico, comedor, ajeno):
    observacion = _observacion(comedor)
    fuera = _observacion(ajeno)
    web = _cliente(tecnico)
    sin_csrf = _cliente(tecnico, enforce_csrf_checks=True)

    assert web.post(f"{ROOT}{fuera.pk}/eliminar/").status_code == 404
    assert web.post(f"{ROOT}999999/eliminar/").status_code == 404
    assert sin_csrf.post(f"{ROOT}{observacion.pk}/eliminar/").status_code == 403
    assert Observacion.objects.count() == 2
    assert Observacion.all_objects.filter(deleted_at__isnull=False).count() == 0
