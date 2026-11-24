"""V06.01: web API de modalidades institucionales (``/api/web/vat/modalidades-institucionales/``). Datos sintéticos."""

import itertools

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

from VAT.models import ModalidadInstitucional

pytestmark = pytest.mark.django_db

ROOT = "/api/web/vat/modalidades-institucionales/"
_COUNTER = itertools.count()


def _client(*codes, csrf=False):
    user = get_user_model().objects.create_user(f"mi{next(_COUNTER)}")
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="VAT", codename__in=codes)
    )
    client = APIClient(enforce_csrf_checks=csrf)
    client.force_login(user)
    return client


@pytest.fixture(name="modalidad")
def modalidad_fixture():
    return ModalidadInstitucional.objects.create(
        nombre="Presencial",
        descripcion="uno dos tres cuatro cinco seis siete ocho nueve diez once doce",
    )


def test_access_follows_each_native_route_rule(modalidad):
    rutas = {
        ROOT: "view",
        f"{ROOT}{modalidad.pk}/": "view",
        f"{ROOT}nueva/": "add",
        f"{ROOT}{modalidad.pk}/editar/": "change",
        f"{ROOT}{modalidad.pk}/eliminar/": "delete",
    }
    for url, accion in rutas.items():
        assert APIClient().get(url).status_code == 401
        for otra in {"view", "add", "change", "delete"} - {accion}:
            assert _client(f"{otra}_modalidadinstitucional").get(url).status_code == 403
        assert _client(f"{accion}_modalidadinstitucional").get(url).status_code == 200
    assert (
        _client("view_modalidadinstitucional").get(f"{ROOT}999999/").status_code == 404
    )


def test_list_projects_the_native_rows_and_filters(modalidad):
    inactiva = ModalidadInstitucional.objects.create(nombre="Virtual", activo=False)
    client = _client("view_modalidadinstitucional", "delete_modalidadinstitucional")
    data = client.get(ROOT).json()
    assert data["permisos"] == {"editar": False, "eliminar": True}
    assert data["urls"] == {
        "list": "/vat/modalidades-institucionales/",
        "create": "/vat/modalidades-institucionales/nueva/",
    }
    por_id = {r["id"]: r for r in data["results"]}
    assert [r["nombre"] for r in data["results"]] == ["Presencial", "Virtual"]
    assert por_id[modalidad.pk]["descripcion"] == (
        "uno dos tres cuatro cinco seis siete ocho nueve diez …"
    )
    assert (
        por_id[inactiva.pk]["descripcion"] == "None"
    )  # native quirk: truncatewords(None)
    assert por_id[inactiva.pk]["activo"] is False
    assert por_id[modalidad.pk]["delete_url"] == (
        f"/vat/modalidades-institucionales/{modalidad.pk}/eliminar/"
    )
    activas = client.get(ROOT, {"activo": "true"}).json()["results"]
    assert [r["id"] for r in activas] == [modalidad.pk]
    inactivas = client.get(ROOT, {"activo": "false"}).json()["results"]
    assert [r["id"] for r in inactivas] == [inactiva.pk]
    assert client.get(ROOT, {"page": 9}).status_code == 404


def test_detail_projects_the_native_context(modalidad):
    data = _client("view_modalidadinstitucional").get(f"{ROOT}{modalidad.pk}/").json()
    assert data["nombre"] == "Presencial"
    assert data["activo"] is True
    assert data["urls"]["update"] == (
        f"/vat/modalidades-institucionales/{modalidad.pk}/editar/"
    )
    assert data["messages"] == []


def test_form_projects_the_native_widgets(modalidad):
    data = (
        _client("change_modalidadinstitucional")
        .get(f"{ROOT}{modalidad.pk}/editar/")
        .json()
    )
    assert data["editing"] is True
    por_nombre = {f["name"]: f for f in data["fields"]}
    assert list(por_nombre) == ["nombre", "descripcion", "activo"]
    assert por_nombre["nombre"]["value"] == "Presencial"
    assert por_nombre["nombre"]["attrs"]["class"] == "form-control"
    assert por_nombre["descripcion"]["tag"] == "textarea"
    assert por_nombre["activo"]["value"] is True
    vacio = _client("add_modalidadinstitucional").get(f"{ROOT}nueva/").json()
    assert vacio["editing"] is False
    assert vacio["urls"] == {"list": "/vat/modalidades-institucionales/"}


def test_create_persists_and_queues_the_native_message_and_rejection_keeps_data():
    client = _client("add_modalidadinstitucional", "view_modalidadinstitucional")
    rechazo = client.post(f"{ROOT}nueva/", {"nombre": ""}, format="multipart")
    assert rechazo.status_code == 400
    assert rechazo.json()["fields"][0]["errors"] == ["Este campo es requerido."]
    assert ModalidadInstitucional.objects.count() == 0
    respuesta = client.post(
        f"{ROOT}nueva/",
        {"nombre": "Virtual", "descripcion": "Texto", "activo": "on"},
        format="multipart",
    )
    nueva = ModalidadInstitucional.objects.get()
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/vat/modalidades-institucionales/{nueva.pk}/",
    }
    assert (nueva.nombre, nueva.descripcion, nueva.activo) == ("Virtual", "Texto", True)
    assert client.get(f"{ROOT}{nueva.pk}/").json()["messages"] == [
        {"message": "Modalidad institucional creada correctamente.", "level": "success"}
    ]


def test_update_persists_and_unchecked_activo_deactivates(modalidad):
    client = _client("change_modalidadinstitucional")
    url = f"{ROOT}{modalidad.pk}/editar/"
    assert client.post(url, {"nombre": ""}, format="multipart").status_code == 400
    modalidad.refresh_from_db()
    assert modalidad.nombre == "Presencial"
    assert client.post(url, {"nombre": "Mixta"}, format="multipart").status_code == 200
    modalidad.refresh_from_db()
    assert (modalidad.nombre, modalidad.activo) == ("Mixta", False)


def test_delete_shows_the_summary_and_removes_through_the_native_view(modalidad):
    client = _client("delete_modalidadinstitucional", "view_modalidadinstitucional")
    url = f"{ROOT}{modalidad.pk}/eliminar/"
    assert client.get(url).json() == {
        "nombre": "Presencial",
        "urls": {"detail": f"/vat/modalidades-institucionales/{modalidad.pk}/"},
    }
    assert ModalidadInstitucional.objects.count() == 1
    assert client.post(url).json() == {
        "ok": True,
        "redirect": "/vat/modalidades-institucionales/",
    }
    assert ModalidadInstitucional.objects.count() == 0
    assert client.post(url).status_code == 404


def test_writes_require_csrf_and_the_write_permission(modalidad):
    todos = (
        "add_modalidadinstitucional",
        "change_modalidadinstitucional",
        "delete_modalidadinstitucional",
    )
    sin_csrf = _client(*todos, csrf=True)
    assert sin_csrf.post(f"{ROOT}nueva/", {"nombre": "X"}).status_code == 403
    assert sin_csrf.post(f"{ROOT}{modalidad.pk}/eliminar/").status_code == 403
    lector = _client("view_modalidadinstitucional")
    assert lector.post(f"{ROOT}nueva/", {"nombre": "X"}).status_code == 403
    assert lector.post(f"{ROOT}{modalidad.pk}/eliminar/").status_code == 403
    assert (
        lector.post(f"{ROOT}{modalidad.pk}/editar/", {"nombre": "X"}).status_code == 403
    )
    assert ModalidadInstitucional.objects.get().nombre == "Presencial"
