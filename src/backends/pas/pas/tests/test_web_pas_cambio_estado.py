"""State change of a PAS titular through G1 v1 (PAS06.03).

``POST /api/web/pas/personas/<pk>/cambiar-estado/`` runs the native form and
service (``PasCambioEstadoForm`` + ``cambiar_estado``) under the native rule
``permissions_any_required(["pas.change_paspersona"])``.
"""

from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.test import Client, override_settings
from django.utils import timezone

from core import web_gate
from core.models import Municipio, Provincia
from pas.forms import PasCambioEstadoForm
from pas.models import (
    PasAviso,
    PasEstado,
    PasHistorialEstado,
    PasInvitacionDDJJ,
    PasPersona,
)

ROOT = "/api/web/pas/"

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _user(username, *codenames):
    user = _ready(get_user_model().objects.create_user(username))
    for codename in codenames:
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="pas", codename=codename)
        )
    return user


@pytest.fixture(name="editor")
def editor_fixture():
    return _user("edita_estado", "view_paspersona", "change_paspersona")


@pytest.fixture(name="web")
def web_fixture(editor):
    client = Client()
    client.force_login(editor)
    return client


@pytest.fixture(name="mundo")
def mundo_fixture():
    activo = PasEstado.objects.get_or_create(nombre="Activo")[0]
    baja = PasEstado.objects.get_or_create(nombre="Baja")[0]
    alta = PasAviso.objects.create(codigo=8101, descripcion="Alta sintética")
    revision = PasAviso.objects.create(codigo=8102, descripcion="Revisión")
    fallecido = PasAviso.objects.create(codigo=8201, descripcion="Fallecido")
    alta.estados.add(activo)
    revision.estados.add(activo, baja)
    fallecido.estados.add(baja)
    provincia = Provincia.objects.create(nombre="Provincia")
    persona = PasPersona.objects.create(
        id_persona=1,
        apellidos="Apellido",
        nombres="Nombre",
        dni=30000001,
        provincia=provincia,
        municipio=Municipio.objects.create(nombre="Municipio", provincia=provincia),
        estado=activo,
    )
    persona.avisos.set([alta])
    invitacion = PasInvitacionDDJJ.objects.create(persona=persona)
    return {
        "persona": persona,
        "activo": activo,
        "baja": baja,
        "alta": alta,
        "revision": revision,
        "fallecido": fallecido,
        "invitacion": invitacion,
    }


def _url(persona_id):
    return f"{ROOT}personas/{persona_id}/cambiar-estado/"


def test_valid_change_replaces_state_and_notices_with_history(web, editor, mundo):
    persona = mundo["persona"]
    antes = timezone.now() - timedelta(days=1)
    PasPersona.objects.filter(pk=persona.pk).update(fecha_actualizacion=antes)

    respuesta = web.post(
        _url(persona.pk),
        {
            "estado": mundo["baja"].pk,
            "avisos": [mundo["fallecido"].pk, mundo["revision"].pk],
        },
    )

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    assert respuesta.json() == {
        "message": "Estado PAS actualizado correctamente.",
        "persona": {
            "estado": {
                "id": mundo["baja"].pk,
                "nombre": "Baja",
                "css_class": "pas-status-baja",
            },
            "avisos": [
                {"codigo": 8102, "descripcion": "Revisión"},
                {"codigo": 8201, "descripcion": "Fallecido"},
            ],
        },
    }
    persona.refresh_from_db()
    assert persona.estado == mundo["baja"]
    assert persona.fecha_actualizacion > antes
    assert set(persona.avisos.all()) == {mundo["fallecido"], mundo["revision"]}
    historial = PasHistorialEstado.objects.get(persona=persona)
    assert historial.estado_anterior == mundo["activo"]
    assert historial.estado_nuevo == mundo["baja"]
    assert list(historial.avisos_anteriores.all()) == [mundo["alta"]]
    assert set(historial.avisos_nuevos.all()) == {mundo["fallecido"], mundo["revision"]}
    assert historial.usuario == editor
    invitacion = PasInvitacionDDJJ.objects.get(pk=mundo["invitacion"].pk)
    assert invitacion.utilizada is None and invitacion.revocada is None
    # The native view would leave the success message for the next page; the API does not.
    assert list(get_messages(respuesta.wsgi_request)) == []


def test_choosing_the_current_state_is_accepted(web, mundo):
    respuesta = web.post(
        _url(mundo["persona"].pk),
        {"estado": mundo["activo"].pk, "avisos": [mundo["revision"].pk]},
    )

    assert respuesta.status_code == 200
    assert PasHistorialEstado.objects.filter(
        persona=mundo["persona"],
        estado_anterior=mundo["activo"],
        estado_nuevo=mundo["activo"],
    ).exists()


@pytest.mark.parametrize(
    "datos",
    [
        {"estado": "", "avisos": []},
        {"estado": "activo", "avisos": []},
        {"avisos": ["fallecido"], "estado": "activo"},
        {"estado": "activo", "avisos": ["9999"]},
    ],
    ids=["vacio", "sin-avisos", "aviso-de-otro-estado", "aviso-inexistente"],
)
def test_invalid_change_returns_the_native_errors_without_effects(web, mundo, datos):
    def valor(v):
        return str(mundo[v].pk) if v in mundo else v

    data = {
        "estado": valor(datos["estado"]),
        "avisos": [valor(a) for a in datos["avisos"]],
    }
    esperado = PasCambioEstadoForm(data)
    assert not esperado.is_valid()

    respuesta = web.post(_url(mundo["persona"].pk), data)

    assert respuesta.status_code == 400
    assert respuesta.json() == {
        "errors": esperado.errors.get_json_data(),
        "messages": [str(e) for errores in esperado.errors.values() for e in errores],
    }
    assert respuesta.json()["messages"]
    mundo["persona"].refresh_from_db()
    assert mundo["persona"].estado == mundo["activo"]
    assert list(mundo["persona"].avisos.all()) == [mundo["alta"]]
    assert not PasHistorialEstado.objects.exists()


def test_required_messages_are_the_django_texts(web, mundo):
    respuesta = web.post(_url(mundo["persona"].pk), {"estado": "", "avisos": []})

    assert respuesta.json()["messages"] == [
        "Este campo es requerido.",
        "Este campo es requerido.",
    ]


def test_without_change_paspersona_is_403_without_effects(mundo):
    for user in (
        _user("solo_ve", "view_paspersona"),
        _user("sin_nada"),
    ):
        client = Client()
        client.force_login(user)
        respuesta = client.post(
            _url(mundo["persona"].pk),
            {"estado": mundo["baja"].pk, "avisos": [mundo["fallecido"].pk]},
        )
        assert respuesta.status_code == 403
        assert "state" not in respuesta.json()
    assert not PasHistorialEstado.objects.exists()
    superuser = _ready(get_user_model().objects.create_superuser("super_estado"))
    client = Client()
    client.force_login(superuser)
    respuesta = client.post(
        _url(mundo["persona"].pk),
        {"estado": mundo["baja"].pk, "avisos": [mundo["fallecido"].pk]},
    )
    assert respuesta.status_code == 200


def test_unknown_titular_is_404(web, mundo):
    respuesta = web.post(
        _url(999999), {"estado": mundo["baja"].pk, "avisos": [mundo["fallecido"].pk]}
    )

    assert respuesta.status_code == 404


def test_only_post_and_csrf_is_required(editor, web, mundo):
    for metodo in ("get", "put", "delete"):
        assert getattr(web, metodo)(_url(mundo["persona"].pk)).status_code == 405
    client = Client(enforce_csrf_checks=True)
    client.force_login(editor)

    respuesta = client.post(
        _url(mundo["persona"].pk),
        {"estado": mundo["baja"].pk, "avisos": [mundo["fallecido"].pk]},
    )

    assert respuesta.status_code == 403
    assert not PasHistorialEstado.objects.exists()


def test_anonymous_gets_401(client, mundo):
    respuesta = client.post(_url(mundo["persona"].pk), {})

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}


def test_panel_lists_the_modal_options(web, mundo):
    data = web.get(f"{ROOT}panel/{mundo['persona'].pk}/").json()

    assert data["cambio_estado"] == {
        "estados": [
            {"id": e.pk, "nombre": e.nombre}
            for e in PasEstado.objects.order_by("nombre")
        ],
        "avisos_por_estado": {
            str(mundo["activo"].pk): [
                {"id": mundo["alta"].pk, "text": "8101 - Alta sintética"},
                {"id": mundo["revision"].pk, "text": "8102 - Revisión"},
            ],
            str(mundo["baja"].pk): [
                {"id": mundo["revision"].pk, "text": "8102 - Revisión"},
                {"id": mundo["fallecido"].pk, "text": "8201 - Fallecido"},
            ],
        },
    }


def test_native_route_is_unchanged(web, mundo):
    respuesta = web.post(
        f"/pas/{mundo['persona'].pk}/cambiar-estado",
        {"estado": mundo["baja"].pk, "avisos": [mundo["revision"].pk]},
    )

    assert respuesta.status_code == 302
    assert respuesta["Location"] == f"/pas/panel-control/{mundo['persona'].pk}"
    assert [str(m) for m in get_messages(respuesta.wsgi_request)] == [
        "Estado PAS actualizado correctamente."
    ]


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="pas",
        ROOT_URLCONF="pas_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, *, target, method):
    return web_gate.sign(
        audience="pas",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method=method,
        target=target,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_accepts_only_a_post_signed_for_it(web, editor, mundo):
    target = _url(mundo["persona"].pk)
    datos = {"estado": mundo["baja"].pk, "avisos": [mundo["fallecido"].pk]}

    for token in (None, _signed(editor, web, target=target, method="GET")):
        extra = {"RAW_URI": target}
        if token:
            extra["HTTP_X_SISOC_WEB_GATE"] = token
        respuesta = web.post(target, datos, **extra)
        assert respuesta.status_code == 403
        assert respuesta.json() == {"detail": web_gate.DETAIL_REJECTED}
    assert not PasHistorialEstado.objects.exists()

    respuesta = web.post(
        target,
        datos,
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(editor, web, target=target, method="POST"),
    )

    assert respuesta.status_code == 200
    assert PasHistorialEstado.objects.count() == 1


def test_admindocs_head_does_not_bypass_the_state_change(client, mundo):
    client.force_login(
        _ready(get_user_model().objects.create_user("staff_estado", is_staff=True))
    )

    respuesta = client.head(_url(mundo["persona"].pk))

    assert respuesta.status_code == 403
    assert "X-View" not in respuesta
