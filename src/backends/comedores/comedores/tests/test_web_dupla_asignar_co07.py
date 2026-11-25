"""Web API (G1 v1) of the comedor technical-team assignment (CO07).

``/api/web/comedores/asignar-dupla/<pk>/`` runs the native ``AsignarDuplaListView``: scoped
comedor, active duplas, native messages. A rejected request must write nothing.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client

from comedores.models import Comedor
from duplas.models import Dupla
from users.services import UserPermissionService

ROOT = "/api/web/comedores/asignar-dupla/"
PERMISO = "duplas.change_dupla"

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
    return _usuario("tecnico_co07_dupla", PERMISO, first_name="Ana", last_name="Pérez")


@pytest.fixture(name="web")
def web_fixture(tecnico):
    return _cliente(tecnico)


@pytest.fixture(name="duplas")
def duplas_fixture(tecnico):
    propia = Dupla.objects.create(
        nombre="Dupla propia",
        estado="Activo",
        coordinador=_usuario("coord_co07", first_name="Luis", last_name="Gómez"),
        abogado=_usuario("abog_co07", first_name="Eva", last_name="Soto"),
    )
    propia.tecnico.add(tecnico)
    nueva = Dupla.objects.create(
        nombre="Dupla nueva", estado="Activo", abogado=_usuario("abog2_co07")
    )
    # The technician also belongs to the new dupla, so the comedor stays in its scope.
    nueva.tecnico.add(tecnico)
    Dupla.objects.create(
        nombre="Dupla inactiva", estado="Inactivo", abogado=_usuario("abog3_co07")
    )
    return propia, nueva


@pytest.fixture(name="comedor")
def comedor_fixture(duplas):
    return Comedor.objects.create(nombre="Comedor CO07", dupla=duplas[0])


def _url(comedor):
    return f"{ROOT}{comedor.pk}/"


def test_get_lists_the_active_duplas_with_the_current_one(web, comedor, duplas):
    datos = web.get(_url(comedor)).json()

    assert datos["comedor"] == {
        "id": comedor.pk,
        "nombre": "Comedor CO07",
        "url": f"/comedores/{comedor.pk}",
    }
    assert datos["dupla_actual_id"] == duplas[0].pk
    assert [fila["nombre"] for fila in datos["duplas"]] == [
        "Dupla propia",
        "Dupla nueva",
    ]
    assert datos["duplas"][0] == {
        "id": duplas[0].pk,
        "nombre": "Dupla propia",
        "coordinador": "Gómez Luis",
        "tecnicos": "Pérez Ana",
        "abogado": "Soto Eva",
    }
    assert datos["duplas"][1]["coordinador"] == "Sin asignar"
    assert datos["urls"] == {"comedores": "/comedores/listar"}
    assert datos["messages"] == []


def test_post_assigns_the_dupla_and_keeps_the_native_message(web, comedor, duplas):
    respuesta = web.post(_url(comedor), {"dupla_id": duplas[1].pk})

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": f"/comedores/{comedor.pk}"}
    comedor.refresh_from_db()
    assert comedor.dupla_id == duplas[1].pk
    assert comedor.estado == "Asignado a Dupla Técnica"
    # The page the redirect lands on consumes the native message.
    assert web.get(_url(comedor)).json()["messages"] == [
        {"message": "Dupla asignada correctamente.", "level": "success"}
    ]


def test_post_without_a_dupla_writes_nothing_and_reports_the_native_error(
    web, comedor, duplas
):
    respuesta = web.post(_url(comedor), {})

    assert respuesta.json() == {"ok": True, "redirect": f"/comedores/{comedor.pk}"}
    comedor.refresh_from_db()
    assert comedor.dupla_id == duplas[0].pk
    assert web.get(_url(comedor)).json()["messages"] == [
        {"message": "No se seleccionó ninguna dupla.", "level": "error"}
    ]


def test_native_permission_scope_and_methods_decide_first(comedor, duplas):
    sin_permiso = _cliente(_usuario("sin_permiso_co07_dupla"))
    ajeno = Comedor.objects.create(nombre="Fuera del alcance")

    assert Client().get(_url(comedor)).status_code in (401, 403)
    assert sin_permiso.get(_url(comedor)).status_code == 403
    assert (
        sin_permiso.post(_url(comedor), {"dupla_id": duplas[1].pk}).status_code == 403
    )
    web = _cliente(_usuario("alcance_co07_dupla", PERMISO))
    assert web.get(_url(ajeno)).status_code == 404
    assert web.post(_url(ajeno), {"dupla_id": duplas[1].pk}).status_code == 404
    assert web.get(f"{ROOT}999999/").status_code == 404
    assert web.delete(_url(comedor)).status_code == 405
    assert (
        web.post(_url(comedor), "{}", content_type="application/json").status_code
        == 415
    )
    comedor.refresh_from_db()
    assert comedor.dupla_id == duplas[0].pk
    ajeno.refresh_from_db()
    assert ajeno.dupla_id is None


def test_post_requires_the_csrf_token(tecnico, comedor, duplas):
    client = _cliente(tecnico, enforce_csrf_checks=True)

    assert client.post(_url(comedor), {"dupla_id": duplas[1].pk}).status_code == 403
    comedor.refresh_from_db()
    assert comedor.dupla_id == duplas[0].pk
