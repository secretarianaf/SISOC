"""Web API (G1 v1) of the Duplas create, edit and soft delete (DU01.02).

Each POST runs the native view's own ``post()``; every effect is compared with
the native HTML view on the same data (fields, M2M, coordinator signals,
soft delete with its actor, messages and redirects).
"""

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client, override_settings
from django.urls import reverse

from comedores.models import Comedor
from core import web_gate
from duplas.models import Dupla
from duplas.test_web_duplas import _ready, _user

ROOT = "/api/web/comedores/duplas/"

pytestmark = pytest.mark.django_db


def _grupo(nombre, *usuarios):
    grupo, _ = Group.objects.get_or_create(name=nombre)
    for usuario in usuarios:
        usuario.groups.add(grupo)
    return grupo


@pytest.fixture(name="admin")
def admin_fixture():
    return _user("admin_form", "Ada", "Admin", "role_admin")


@pytest.fixture(name="web")
def web_fixture(admin):
    client = Client(enforce_csrf_checks=True)
    client.force_login(admin)
    client.get(reverse("dupla_list"))  # csrftoken cookie, as the React page gets it
    return client


def _csrf(client):
    return client.cookies[settings.CSRF_COOKIE_NAME].value


def _post(client, url, data):
    return client.post(url, {"csrfmiddlewaretoken": _csrf(client), **data})


@pytest.fixture(name="miembros")
def miembros_fixture():
    tecnicos = [
        _user("tec_1", "Ana", "Prueba"),
        _user("tec_2", "", ""),
        _user("tec_3", "Inés", "Otra"),
    ]
    abogados = [_user("abo_1", "Laura", "Legal"), _user("abo_2", "Mario", "Norma")]
    fuera = _user("fuera", "No", "Tecnico")
    _grupo("Tecnico Comedor", *tecnicos)
    _grupo("Abogado Dupla", *abogados)
    coordinador = _user("coord_1", "Clara", "Coordina")
    _grupo("Coordinador Equipo Tecnico", coordinador)
    return {
        "tecnicos": tecnicos,
        "abogados": abogados,
        "fuera": fuera,
        "coordinador": coordinador,
    }


def _estado(dupla):
    dupla = Dupla.all_objects.get(pk=dupla.pk)
    return {
        "nombre": dupla.nombre,
        "estado": dupla.estado,
        "abogado": dupla.abogado_id,
        "tecnicos": sorted(dupla.tecnico.values_list("pk", flat=True)),
        "coordinador": dupla.coordinador_id,
        "coordinadores": sorted(dupla.coordinadores.values_list("pk", flat=True)),
        "borrada": dupla.deleted_at is not None,
        "borrada_por": dupla.deleted_by_id,
    }


def _comedor(comedor):
    manager = getattr(Comedor, "all_objects", Comedor.objects)
    fila = manager.get(pk=comedor.pk)
    return (getattr(fila, "deleted_at", None) is not None, fila.dupla_id is not None)


def test_create_form_lists_the_native_options_and_labels(web, miembros):
    data = web.get(f"{ROOT}crear/").json()
    native = web.get(reverse("dupla_crear")).context["form"]

    assert data["title"] == "Editar Equipo técnico"
    assert list(data["fields"]) == ["nombre", "estado", "tecnico", "abogado"]
    assert data["fields"]["nombre"] == {
        "label": "Nombre",
        "required": True,
        "help_text": "",
        "value": "",
        "max_length": 255,
    }
    assert data["fields"]["estado"]["choices"] == [
        {"value": "", "label": "---------"},
        {"value": "Activo", "label": "Activo"},
        {"value": "Inactivo", "label": "Inactivo"},
    ]
    tecnico = data["fields"]["tecnico"]
    assert tecnico["label"] == "Tecnico"
    assert tecnico["help_text"] == "Un técnico puede integrarse en varias duplas."
    assert tecnico["value"] == []
    assert [c["label"] for c in tecnico["choices"]] == [
        label for _, label in native.fields["tecnico"].choices
    ]
    assert {c["label"] for c in tecnico["choices"]} == {
        "Prueba Ana - tec_1",
        "tec_2",
        "Otra Inés - tec_3",
    }
    abogado = data["fields"]["abogado"]["choices"]
    assert abogado[0] == {"value": "", "label": "---------"}
    assert {c["label"] for c in abogado[1:]} == {
        "Legal Laura - abo_1",
        "Norma Mario - abo_2",
    }
    # The coordinator is not a form field: it is assigned from Usuarios.
    assert "coordinador" not in data["fields"]
    assert data["coordinador"] is None
    assert data["errors"] == {}
    assert data["urls"] == {"cancel": "/equipo-tecnico/"}


def test_missing_groups_give_empty_options(web):
    data = web.get(f"{ROOT}crear/").json()

    assert data["fields"]["tecnico"]["choices"] == []
    assert data["fields"]["abogado"]["choices"] == [{"value": "", "label": "---------"}]


def test_create_saves_like_the_native_form_and_queues_the_message(web, admin, miembros):
    t, a = miembros["tecnicos"], miembros["abogados"]
    datos = {
        "nombre": "Equipo Nuevo",
        "estado": "Activo",
        "tecnico": [t[0].pk, t[2].pk],
        "abogado": a[1].pk,
    }

    respuesta = _post(web, f"{ROOT}crear/", datos)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": "/equipo-tecnico/"}
    api = Dupla.objects.get(nombre="Equipo Nuevo")
    lista = web.get(ROOT).json()
    assert lista["messages"] == [
        {"message": "Equipo técnico creado correctamente.", "level": "success"}
    ]

    nativo = _post(web, reverse("dupla_crear"), {**datos, "nombre": "Equipo Nativo"})
    assert nativo.status_code == 302 and nativo["Location"] == "/equipo-tecnico/"
    native = Dupla.objects.get(nombre="Equipo Nativo")
    assert {**_estado(api), "nombre": None} == {**_estado(native), "nombre": None}
    assert _estado(api)["tecnicos"] == sorted([t[0].pk, t[2].pk])
    assert _estado(api)["coordinador"] is None


def test_invalid_create_returns_the_errors_and_the_general_message(web, miembros):
    datos = {
        "nombre": "",
        "estado": "Activo",
        "tecnico": [miembros["fuera"].pk],
        "abogado": "",
    }

    respuesta = _post(web, f"{ROOT}crear/", datos)

    assert respuesta.status_code == 400
    data = respuesta.json()
    assert set(data["errors"]) == {"nombre", "tecnico", "abogado"}
    assert data["errors"]["nombre"] == [
        {"message": "Este campo es requerido.", "code": "required"}
    ]
    assert data["errors"]["tecnico"][0]["message"] == (
        f"Seleccione una opción válida. {miembros['fuera'].pk} no es una de las opciones disponibles."
    )
    assert data["fields"]["estado"]["value"] == "Activo"
    assert data["fields"]["tecnico"]["value"] == [str(miembros["fuera"].pk)]
    assert data["messages"] == [
        {"message": "Error al crear el Equipo técnico.", "level": "error"}
    ]
    assert Dupla.objects.count() == 0
    # Consumed with the response, like the native page that renders it.
    assert web.get(ROOT).json()["messages"] == []


def test_forged_ids_outside_the_options_are_rejected(web, miembros):
    t = miembros["tecnicos"]
    for datos in (
        {"tecnico": [t[0].pk], "abogado": miembros["fuera"].pk},
        {
            "tecnico": [miembros["coordinador"].pk],
            "abogado": miembros["abogados"][0].pk,
        },
        {"tecnico": [999999], "abogado": miembros["abogados"][0].pk},
    ):
        respuesta = _post(
            web, f"{ROOT}crear/", {"nombre": "X", "estado": "Activo", **datos}
        )
        assert respuesta.status_code == 400, datos
    assert Dupla.objects.count() == 0


def test_edit_keeps_the_coordinator_and_its_signals(web, miembros):
    t, a, c = miembros["tecnicos"], miembros["abogados"], miembros["coordinador"]
    dupla = Dupla.objects.create(
        nombre="Equipo E", estado="Activo", abogado=a[0], coordinador=c
    )
    dupla.tecnico.set([t[0]])
    gemela = Dupla.objects.create(
        nombre="Equipo G", estado="Activo", abogado=a[0], coordinador=c
    )
    gemela.tecnico.set([t[0]])

    form = web.get(f"{ROOT}{dupla.pk}/editar/").json()
    assert form["fields"]["nombre"]["value"] == "Equipo E"
    assert form["fields"]["tecnico"]["value"] == [str(t[0].pk)]
    assert form["fields"]["abogado"]["value"] == str(a[0].pk)
    assert form["coordinador"] == "Clara Coordina"

    datos = {
        "nombre": "Equipo E2",
        "estado": "Inactivo",
        "tecnico": [t[1].pk, t[2].pk],
        "abogado": a[1].pk,
    }
    respuesta = _post(web, f"{ROOT}{dupla.pk}/editar/", datos)
    assert respuesta.json() == {"ok": True, "redirect": "/equipo-tecnico/"}
    assert web.get(ROOT).json()["messages"] == []  # the native edit queues no message
    nativo = _post(
        web, reverse("dupla_editar", args=[gemela.pk]), {**datos, "nombre": "Equipo G2"}
    )
    assert nativo.status_code == 302

    assert {**_estado(dupla), "nombre": None} == {**_estado(gemela), "nombre": None}
    assert _estado(dupla)["coordinador"] == c.pk
    assert _estado(dupla)["coordinadores"] == [c.profile.pk]


def test_invalid_edit_matches_the_native_errors_without_message(web, miembros):
    dupla = Dupla.objects.create(
        nombre="Equipo I", estado="Activo", abogado=miembros["abogados"][0]
    )
    datos = {"nombre": "", "estado": "Activo", "tecnico": [], "abogado": ""}

    respuesta = _post(web, f"{ROOT}{dupla.pk}/editar/", datos)
    native = _post(web, reverse("dupla_editar", args=[dupla.pk]), datos).context["form"]

    assert respuesta.status_code == 400
    assert respuesta.json()["errors"] == {
        name: [{"message": str(e["message"]), "code": e["code"]} for e in errors]
        for name, errors in native.errors.get_json_data().items()
    }
    assert respuesta.json()["messages"] == []
    assert Dupla.objects.get(pk=dupla.pk).nombre == "Equipo I"


def test_native_invalid_create_still_fails_as_today(miembros, admin):
    client = Client(raise_request_exception=False)
    client.force_login(admin)

    respuesta = client.post(reverse("dupla_crear"), {"nombre": ""})

    # Pre-existing: ``DuplaCreateView.post`` never sets ``self.object``.
    assert respuesta.status_code == 500


def test_delete_preview_and_soft_delete_match_the_native_view(web, admin, miembros):
    a = miembros["abogados"][0]
    api = Dupla.objects.create(nombre="Equipo Ñandú", estado="Activo", abogado=a)
    native = Dupla.objects.create(nombre="Equipo Nativo", estado="Activo", abogado=a)
    comedor = Comedor.objects.create(nombre="Comedor de la dupla", dupla=api)
    comedor_nativo = Comedor.objects.create(nombre="Comedor nativo", dupla=native)

    data = web.get(f"{ROOT}{api.pk}/eliminar/").json()
    contexto = web.get(reverse("dupla_eliminar", args=[api.pk])).context
    assert data["object_name"] == "EQUIPO ÑANDÚ"
    assert data["title"] == data["confirm_text"] == "Dar de baja Equipo técnico"
    assert data["cancel_text"] == "Cancelar"
    assert data["cascade_preview"] == contexto["cascade_preview"]
    assert data["urls"] == {"cancel": "/equipo-tecnico/"}

    respuesta = _post(web, f"{ROOT}{api.pk}/eliminar/", {})
    assert respuesta.json() == {"ok": True, "redirect": "/equipo-tecnico/"}
    assert web.get(ROOT).json()["messages"] == [
        {"message": "Equipo técnico dado de baja correctamente.", "level": "success"}
    ]
    nativo = _post(web, reverse("dupla_eliminar", args=[native.pk]), {})
    assert nativo.status_code == 302

    assert _estado(api)["borrada"] is True
    assert _estado(api)["borrada_por"] == admin.pk
    assert {**_estado(api), "nombre": None} == {**_estado(native), "nombre": None}
    assert _comedor(comedor) == _comedor(comedor_nativo)
    # Already soft deleted: the next confirmation and POST are 404, like native.
    assert web.get(f"{ROOT}{api.pk}/eliminar/").status_code == 404
    assert _post(web, f"{ROOT}{api.pk}/eliminar/", {}).status_code == 404
    assert web.get(reverse("dupla_eliminar", args=[api.pk])).status_code == 404


def test_writes_require_csrf_and_role_admin(client, web, miembros):
    dupla = Dupla.objects.create(
        nombre="Equipo C", estado="Activo", abogado=miembros["abogados"][0]
    )
    sin_token = web.post(f"{ROOT}{dupla.pk}/eliminar/", {})
    assert sin_token.status_code == 403
    assert _estado(dupla)["borrada"] is False

    for usuario in (
        _user("sin_rol_form"),
        _user("solo_csv_form", "", "", "role_exportar_a_csv"),
    ):
        client.force_login(usuario)
        for url in (
            f"{ROOT}crear/",
            f"{ROOT}{dupla.pk}/editar/",
            f"{ROOT}{dupla.pk}/eliminar/",
        ):
            assert client.get(url).status_code == 403, (usuario.username, url)
            assert client.post(url, {"nombre": "X"}).status_code == 403, (
                usuario.username,
                url,
            )
    assert _estado(dupla)["borrada"] is False and Dupla.objects.count() == 1


def test_missing_equipo_is_404_and_other_methods_405(web, miembros):
    dupla = Dupla.objects.create(
        nombre="Equipo M", estado="Activo", abogado=miembros["abogados"][0]
    )
    for url in (f"{ROOT}999999/editar/", f"{ROOT}999999/eliminar/"):
        assert web.get(url).status_code == 404
    for url in (
        f"{ROOT}crear/",
        f"{ROOT}{dupla.pk}/editar/",
        f"{ROOT}{dupla.pk}/eliminar/",
    ):
        for metodo in ("put", "patch", "delete"):
            assert (
                getattr(web, metodo)(url, HTTP_X_CSRFTOKEN=_csrf(web)).status_code
                == 405
            ), (url, metodo)
    assert _estado(dupla)["borrada"] is False


def test_admindocs_head_does_not_bypass_the_form_routes(client, miembros):
    staff = _ready(User.objects.create_user("staff_form", is_staff=True))
    client.force_login(staff)
    dupla = Dupla.objects.create(
        nombre="Equipo H", estado="Activo", abogado=miembros["abogados"][0]
    )
    for url in (
        f"{ROOT}crear/",
        f"{ROOT}{dupla.pk}/editar/",
        f"{ROOT}{dupla.pk}/eliminar/",
    ):
        respuesta = client.head(url)
        assert respuesta.status_code in (403, 405), url
        assert "X-View" not in respuesta


@override_settings(
    SISOC_BACKEND="comedores",
    ROOT_URLCONF="comedores_runtime.urls",
    SISOC_BACKENDS={},
    INTERNAL_IPS=[],
)
def test_runtime_post_needs_a_post_attestation(web, admin, miembros):
    dupla = Dupla.objects.create(
        nombre="Equipo R", estado="Activo", abogado=miembros["abogados"][0]
    )
    target = f"{ROOT}{dupla.pk}/eliminar/"
    sesion = web.cookies[settings.SESSION_COOKIE_NAME].value

    def firma(method):
        return web_gate.sign(
            audience="comedores",
            user_pk=admin.pk,
            session_key=sesion,
            method=method,
            target=target,
        )

    datos = {"csrfmiddlewaretoken": _csrf(web)}
    assert (
        web.post(
            target, datos, RAW_URI=target, HTTP_X_SISOC_WEB_GATE=firma("GET")
        ).status_code
        == 403
    )
    assert _estado(dupla)["borrada"] is False
    ok = web.post(target, datos, RAW_URI=target, HTTP_X_SISOC_WEB_GATE=firma("POST"))
    assert ok.status_code == 200
    assert _estado(dupla)["borrada"] is True
