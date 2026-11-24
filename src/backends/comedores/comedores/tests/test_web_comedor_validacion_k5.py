"""Web API (G1 v1) of the comedor validation (CO07.03).

``POST .../<pk>/validar/`` runs the native ``validar_comedor`` view; these tests
check the persisted effects (estado, ``fecha_validado`` and the history row),
that every refusal leaves both unchanged, the access in front of the view and
the capability the modals read from the server.
"""

import pytest
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client

from comedores.models import Comedor, HistorialValidacion
from duplas.models import Dupla

pytestmark = pytest.mark.django_db
User = get_user_model()
ROOT = "/api/web/comedores/comedores/"
VIEW = "comedores.view_comedor"


@pytest.fixture(name="comedor_fixture", autouse=True)
def sin_dobles_del_conftest():
    """Same name as the folder's autouse double: these tests run the real services."""


def _perm(user, code):
    app, codename = code.split(".")
    if app == "auth":
        permiso = Permission.objects.get_or_create(
            codename=codename,
            content_type=ContentType.objects.get_for_model(User),
            defaults={"name": codename},
        )[0]
    else:
        permiso = Permission.objects.get(content_type__app_label=app, codename=codename)
    user.user_permissions.add(permiso)


def _user(username, *codes, **flags):
    user = User.objects.create_user(username, password="x", **flags)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    for code in codes:
        _perm(user, code)
    return user


def _client(user, enforce_csrf=False):
    client = Client(enforce_csrf_checks=enforce_csrf)
    client.force_login(user)
    return client


def _estado(comedor):
    comedor.refresh_from_db()
    return (
        comedor.estado_validacion,
        comedor.fecha_validado,
        HistorialValidacion.objects.filter(comedor=comedor).count(),
    )


def _mensajes(respuesta):
    return [str(m) for m in messages.get_messages(respuesta.wsgi_request)]


@pytest.fixture(name="escenario")
def escenario_fixture():
    abogado = _user("abogado_k5val", VIEW, "auth.role_abogado_dupla")
    tecnico = _user("tecnico_k5val", VIEW, "auth.role_tecnico_comedor")
    ajeno = _user("tecnico_ajeno_k5val", VIEW, "auth.role_tecnico_comedor")
    dupla = Dupla.objects.create(nombre="Dupla K5", estado="Activo", abogado=abogado)
    dupla.tecnico.add(tecnico)
    comedor = Comedor.objects.create(nombre="Comedor K5", dupla=dupla)
    return {
        "comedor": comedor,
        "abogado": abogado,
        "tecnico": tecnico,
        "ajeno": ajeno,
        "validador": _user("validador_k5val", VIEW, "auth.role_validador_comedores"),
        "lector": _user("lector_k5val", VIEW),
    }


def _validar(pk):
    return f"{ROOT}{pk}/validar/"


def _modal(pk):
    return f"{ROOT}{pk}/validacion/"


def test_access_anonymous_401_without_permission_403_and_csrf_403(escenario):
    pk = escenario["comedor"].pk
    sin_permiso = _client(_user("sin_permiso_k5val"))

    assert Client().get(_modal(pk)).status_code == 401
    assert Client().post(_validar(pk), {"accion": "validar"}).status_code == 401
    assert sin_permiso.get(_modal(pk)).status_code == 403
    assert sin_permiso.post(_validar(pk), {"accion": "validar"}).status_code == 403
    estricto = _client(escenario["validador"], enforce_csrf=True)
    assert estricto.post(_validar(pk), {"accion": "validar"}).status_code == 403
    assert _estado(escenario["comedor"])[0] == "Pendiente"


def test_capability_is_computed_by_the_server(escenario):
    pk = escenario["comedor"].pk

    esperado = {
        "validador": True,
        "tecnico": True,
        "abogado": False,
        "lector": False,
    }
    for rol, puede in esperado.items():
        datos = _client(escenario[rol]).get(_modal(pk)).json()
        assert datos["puede_validar"] is puede
        assert [o["value"] for o in datos["opciones"]] == (
            [
                "pac_inexistente_o_no_coincide",
                "sin_movimiento",
                "no_se_reconoce_el_comedor",
                "no_corresponde_a_la_dupla",
                "otro",
            ]
            if puede
            else []
        )
        assert datos["urls"]["ficha"] == f"/comedores/{pk}"
    assert _client(escenario["tecnico"]).get(_modal(pk)).json()["opciones"][-1] == {
        "value": "otro",
        "label": "Otros",
    }


def test_modal_data_outside_the_scope_is_404(escenario):
    assert (
        _client(escenario["ajeno"]).get(_modal(escenario["comedor"].pk)).status_code
        == 404
    )


def test_validar_persists_estado_date_history_and_redirects_to_the_ficha(escenario):
    comedor = escenario["comedor"]

    respuesta = _client(escenario["tecnico"]).post(
        _validar(comedor.pk),
        {"accion": "validar", "next": f"/comedores/{comedor.pk}"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"redirect": f"/comedores/{comedor.pk}"}
    assert _mensajes(respuesta) == ["Comedor validado correctamente."]
    estado, fecha, historial = _estado(comedor)
    assert (estado, historial) == ("Validado", 1) and fecha is not None
    fila = HistorialValidacion.objects.get(comedor=comedor)
    assert fila.usuario == escenario["tecnico"]
    assert fila.estado_validacion == "Validado" and fila.opciones_no_validar is None


def test_no_validar_stores_the_options_and_the_trimmed_free_text(escenario):
    comedor = escenario["comedor"]

    respuesta = _client(escenario["validador"]).post(
        _validar(comedor.pk),
        {
            "accion": "no_validar",
            "opciones": ["sin_movimiento", "otro"],
            "comentario": "  detalle  ",
        },
    )

    assert respuesta.status_code == 200
    assert _mensajes(respuesta) == ["Comedor marcado como no validado."]
    assert _estado(comedor)[0] == "No Validado"
    fila = HistorialValidacion.objects.get(comedor=comedor)
    assert fila.opciones_no_validar == ["sin_movimiento", "otro"]
    assert fila.comentario == "  detalle  "
    assert fila.usuario == escenario["validador"]


@pytest.mark.parametrize(
    ("datos", "mensaje"),
    [
        ({"accion": "no_validar"}, "Debe seleccionar al menos una opción."),
        (
            {"accion": "no_validar", "opciones": ["otro"], "comentario": "   "},
            "El comentario es obligatorio cuando selecciona 'Otro'.",
        ),
        ({"accion": "borrar"}, "Acción no válida."),
        ({}, "Acción no válida."),
    ],
)
def test_refusals_answer_the_native_redirect_and_change_nothing(
    escenario, datos, mensaje
):
    comedor = escenario["comedor"]
    antes = _estado(comedor)

    respuesta = _client(escenario["validador"]).post(_validar(comedor.pk), datos)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"redirect": f"/comedores/{comedor.pk}"}
    assert _mensajes(respuesta) == [mensaje]
    assert _estado(comedor) == antes


def test_a_user_without_the_capability_is_refused_and_nothing_changes(escenario):
    comedor = escenario["comedor"]
    antes = _estado(comedor)

    for rol in ("abogado", "lector"):
        respuesta = _client(escenario[rol]).post(
            _validar(comedor.pk), {"accion": "validar"}
        )
        assert respuesta.status_code == 200
        assert _mensajes(respuesta) == ["No tiene permisos para validar este comedor."]

    assert _estado(comedor) == antes


def test_outside_the_scope_is_404_and_nothing_changes(escenario):
    comedor = escenario["comedor"]
    antes = _estado(comedor)

    respuesta = _client(escenario["ajeno"]).post(
        _validar(comedor.pk), {"accion": "validar"}
    )

    assert respuesta.status_code == 404
    assert _estado(comedor) == antes


def test_external_next_falls_back_to_the_ficha(escenario):
    comedor = escenario["comedor"]

    respuesta = _client(escenario["validador"]).post(
        _validar(comedor.pk),
        {"accion": "validar", "next": "https://example.org/robar"},
    )

    assert respuesta.json() == {"redirect": f"/comedores/{comedor.pk}"}
    assert _estado(comedor)[0] == "Validado"


def test_repeating_adds_a_history_row_and_moves_the_date(escenario):
    comedor = escenario["comedor"]
    web = _client(escenario["validador"])

    web.post(_validar(comedor.pk), {"accion": "validar"})
    primera = _estado(comedor)
    web.post(_validar(comedor.pk), {"accion": "validar"})
    segunda = _estado(comedor)

    assert (primera[2], segunda[2]) == (1, 2)
    assert segunda[1] > primera[1]
    assert (
        list(
            HistorialValidacion.objects.filter(comedor=comedor).values_list(
                "estado_validacion", flat=True
            )
        )
        == ["Validado"] * 2
    )


def test_get_on_the_action_and_post_on_the_data_are_405(escenario):
    web = _client(escenario["validador"])
    pk = escenario["comedor"].pk

    assert web.get(_validar(pk)).status_code == 405
    assert web.post(_modal(pk), {"accion": "validar"}).status_code == 405
