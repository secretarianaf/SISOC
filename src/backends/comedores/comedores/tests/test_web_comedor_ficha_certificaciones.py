"""Certifications card and capacitaciones review of the comedor ficha web API (CO07.01).

The card is a projection of the native context; the review POST runs the native
``review_certificate``. These tests check the persisted effect of each outcome and
that a refused or rejected request leaves the certificate unchanged.
"""

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client

from comedores.models import (
    CapacitacionComedorCertificado,
    Comedor,
    PrestacionAlimentariaConformidad,
)
from core import web_gate

pytestmark = pytest.mark.django_db
ROOT = "/api/web/comedores/comedores/"


@pytest.fixture(name="comedor_fixture", autouse=True)
def sin_dobles_del_conftest():
    """Same name as the folder's autouse double: the ficha runs the real services."""


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _client(username, *codenames):
    usuario = _ready(get_user_model().objects.create_user(username, password="x"))
    for codename in codenames:
        usuario.user_permissions.add(Permission.objects.get(codename=codename))
    client = Client()
    client.force_login(usuario)
    client.usuario = usuario
    return client


@pytest.fixture(name="lector")
def lector_fixture():
    return _client("lector_cert", "view_comedor")


@pytest.fixture(name="revisor")
def revisor_fixture():
    return _client("revisor_cert", "view_comedor", "change_comedor")


@pytest.fixture(name="comedor")
def comedor_fixture():
    return Comedor.objects.create(nombre="Comedor Norte")


def _ficha(client, comedor):
    return client.get(f"{ROOT}{comedor.pk}/").json()


def test_certificaciones_card_is_empty_without_records(lector, comedor):
    card = _ficha(lector, comedor)["certificaciones"]

    assert card["items"] == []
    assert card["historial"] == f"/comedores/{comedor.pk}/certificaciones-prestaciones/"


def test_certificaciones_card_projects_the_native_cells_and_keeps_six(lector, comedor):
    autor = get_user_model().objects.create_user(
        "autor_cert", first_name="Ana", last_name="Gómez", password="x"
    )
    sin_nombre = get_user_model().objects.create_user("solo_usuario", password="x")
    for mes in range(1, 8):
        PrestacionAlimentariaConformidad.objects.create(
            comedor=comedor,
            periodo=date(2026, mes, 1),
            conforme=mes % 2 == 0,
            usuario=autor if mes == 7 else (sin_nombre if mes == 6 else None),
        )

    items = _ficha(lector, comedor)["certificaciones"]["items"]

    assert [i["periodo"] for i in items] == [
        "07/2026",
        "06/2026",
        "05/2026",
        "04/2026",
        "03/2026",
        "02/2026",
    ]
    assert items[0]["usuario"] == "Ana Gómez"
    assert items[1]["usuario"] == "solo_usuario"
    assert items[2]["usuario"] == "-"
    assert [i["conforme"] for i in items[:3]] == [False, True, False]
    assert items[0]["pdf"] is None
    assert len(items[0]["creado"]) == len("01/01/2026 10:00")


def _certificado(comedor, **campos):
    certificado, _ = CapacitacionComedorCertificado.objects.get_or_create(
        comedor=comedor, capacitacion="seguridad_cocina"
    )
    CapacitacionComedorCertificado.objects.filter(pk=certificado.pk).update(**campos)
    certificado.refresh_from_db()
    return certificado


def _estado(client, comedor, certificado, **datos):
    return client.post(
        f"{ROOT}{comedor.pk}/capacitaciones/{certificado.pk}/estado/", datos
    )


def test_accepting_a_presented_certificate_persists_the_review(revisor, comedor):
    certificado = _certificado(comedor, estado="presentado", observacion="viejo")

    respuesta = _estado(revisor, comedor, certificado, estado="aceptado")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["success"] is True
    assert cuerpo["item"]["estado"] == "aceptado"
    certificado.refresh_from_db()
    assert certificado.estado == "aceptado"
    assert certificado.observacion is None
    assert certificado.revisado_por == revisor.usuario
    assert certificado.fecha_revision is not None


def test_rejecting_with_an_observation_persists_it(revisor, comedor):
    certificado = _certificado(comedor, estado="presentado")

    respuesta = _estado(
        revisor, comedor, certificado, estado="rechazado", observacion="  Ilegible  "
    )

    assert respuesta.status_code == 200
    certificado.refresh_from_db()
    assert certificado.estado == "rechazado"
    assert certificado.observacion == "Ilegible"
    assert certificado.revisado_por == revisor.usuario


@pytest.mark.parametrize(
    "datos, mensaje",
    [
        ({"estado": "rechazado"}, "Debe ingresar una observación para rechazar."),
        (
            {"estado": "rechazado", "observacion": "   "},
            "Debe ingresar una observación para rechazar.",
        ),
        ({"estado": "inexistente"}, "Estado inválido."),
        ({}, "Estado inválido."),
    ],
)
def test_a_refused_review_is_400_and_leaves_the_certificate_unchanged(
    revisor, comedor, datos, mensaje
):
    certificado = _certificado(comedor, estado="presentado", observacion="previa")

    respuesta = _estado(revisor, comedor, certificado, **datos)

    assert respuesta.status_code == 400
    assert respuesta.json() == {"success": False, "error": [mensaje]}
    certificado.refresh_from_db()
    assert certificado.estado == "presentado"
    assert certificado.observacion == "previa"
    assert certificado.revisado_por is None
    assert certificado.fecha_revision is None


def test_a_reviewed_certificate_cannot_change_state(revisor, comedor):
    certificado = _certificado(comedor, estado="aceptado")

    respuesta = _estado(
        revisor, comedor, certificado, estado="rechazado", observacion="Tarde"
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["error"] == [
        "El certificado ya fue revisado y no puede cambiar de estado."
    ]
    certificado.refresh_from_db()
    assert certificado.estado == "aceptado"
    assert certificado.revisado_por is None


def test_a_certificate_of_another_comedor_or_a_missing_one_is_404(revisor, comedor):
    otro = Comedor.objects.create(nombre="Comedor Sur")
    ajeno = _certificado(otro, estado="presentado")

    assert _estado(revisor, comedor, ajeno, estado="aceptado").status_code == 404
    ajeno.refresh_from_db()
    assert ajeno.estado == "presentado"
    assert _estado(revisor, otro, ajeno, estado="aceptado").status_code == 200
    faltante = revisor.post(
        f"{ROOT}{comedor.pk}/capacitaciones/999999/estado/", {"estado": "aceptado"}
    )
    assert faltante.status_code == 404
    sin_comedor = revisor.post(
        f"{ROOT}999999/capacitaciones/{ajeno.pk}/estado/", {"estado": "aceptado"}
    )
    assert sin_comedor.status_code == 404


def test_review_access_methods_and_csrf(lector, revisor, comedor):
    certificado = _certificado(comedor, estado="presentado")
    url = f"{ROOT}{comedor.pk}/capacitaciones/{certificado.pk}/estado/"

    assert Client().post(url, {"estado": "aceptado"}).status_code == 401
    # Seeing the ficha is not enough: the native route asks for change_comedor.
    assert _estado(lector, comedor, certificado, estado="aceptado").status_code == 403
    assert revisor.get(url).status_code == 405
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(revisor.usuario)
    assert csrf.post(url, {"estado": "aceptado"}).status_code == 403
    certificado.refresh_from_db()
    assert certificado.estado == "presentado"


def test_pending_web_requirement_and_forged_header(comedor):
    usuario = get_user_model().objects.create_superuser("pendiente_cert", password="x")
    usuario.profile.acceso_web = True
    usuario.profile.must_change_password = True
    usuario.profile.save()
    certificado = _certificado(comedor, estado="presentado")
    client = Client()
    client.force_login(usuario)
    url = f"{ROOT}{comedor.pk}/capacitaciones/{certificado.pk}/estado/"
    falso = web_gate.sign(
        audience="comedores",
        user_pk=usuario.pk,
        session_key=client.cookies["sessionid"].value,
        method="POST",
        target=url,
    )

    respuesta = client.post(
        url, {"estado": "aceptado"}, HTTP_X_SISOC_WEB_GATE=falso, RAW_URI=url
    )

    assert respuesta.status_code == 403
    certificado.refresh_from_db()
    assert certificado.estado == "presentado"
