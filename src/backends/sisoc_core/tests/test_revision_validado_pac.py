"""H12 (QA 28/9): un registro PAC ``Validado`` no admite otra revisión.

Mismo criterio que el seguimiento PNUD: el coordinador no puede volver a
"A subsanar" un acompañamiento territorial o un seguimiento ya validado, y el
botón "Revisar" no se muestra.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.urls import reverse

from comedores.models import Comedor
from core.models import Provincia
from relevamientos.models import PrimerSeguimiento, Relevamiento

pytestmark = pytest.mark.django_db

A_SUBSANAR = Relevamiento.ESTADO_VALIDACION_A_SUBSANAR
VALIDADO = Relevamiento.ESTADO_VALIDACION_VALIDADO
PENDIENTE = Relevamiento.ESTADO_VALIDACION_PENDIENTE


def _coordinador(client):
    user = get_user_model().objects.create_user(
        username="coord_h12", password="testpass123"
    )
    for codename in ("review_relevamiento", "view_relevamiento"):
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="relevamientos", codename=codename
            )
        )
    client.force_login(user)
    return user


def _relevamiento(estado_validacion):
    provincia = Provincia.objects.create(nombre="Prov H12")
    comedor = Comedor.objects.create(nombre="Comedor H12", provincia=provincia)
    return Relevamiento.objects.create(
        comedor=comedor,
        estado="Visita pendiente",
        estado_validacion=estado_validacion,
    )


def _seguimiento(estado_validacion):
    relevamiento = _relevamiento(None)
    return PrimerSeguimiento.objects.create(
        id_relevamiento=relevamiento,
        estado=PrimerSeguimiento.ESTADO_COMPLETO,
        estado_validacion=estado_validacion,
    )


def _mensajes(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


def test_relevamiento_validado_no_vuelve_a_subsanar(client):
    relevamiento = _relevamiento(VALIDADO)
    _coordinador(client)

    response = client.post(
        reverse(
            "relevamiento_revision_coordinador",
            kwargs={"comedor_pk": relevamiento.comedor_id, "pk": relevamiento.id},
        ),
        {"estado_validacion": A_SUBSANAR, "observaciones_coordinador": "Volver"},
    )

    assert response.status_code == 302
    relevamiento.refresh_from_db()
    assert relevamiento.estado_validacion == VALIDADO
    assert relevamiento.observaciones_coordinador is None
    assert relevamiento.coordinador_id is None
    assert _mensajes(response) == [
        "El acompañamiento territorial ya está validado: no admite otra revisión."
    ]


def test_seguimiento_validado_no_vuelve_a_subsanar(client):
    seguimiento = _seguimiento(VALIDADO)
    _coordinador(client)

    response = client.post(
        reverse(
            "seguimiento_revision_coordinador",
            kwargs={
                "comedor_pk": seguimiento.id_relevamiento.comedor_id,
                "relevamiento_pk": seguimiento.id_relevamiento_id,
                "pk": seguimiento.id,
            },
        ),
        {"estado_validacion": A_SUBSANAR, "observaciones_coordinador": "Volver"},
    )

    assert response.status_code == 302
    seguimiento.refresh_from_db()
    assert seguimiento.estado_validacion == VALIDADO
    assert seguimiento.observaciones_coordinador is None
    assert _mensajes(response) == [
        "El seguimiento ya está validado: no admite otra revisión."
    ]


def test_seguimiento_a_subsanar_sigue_admitiendo_revision(client):
    seguimiento = _seguimiento(A_SUBSANAR)
    _coordinador(client)

    client.post(
        reverse(
            "seguimiento_revision_coordinador",
            kwargs={
                "comedor_pk": seguimiento.id_relevamiento.comedor_id,
                "relevamiento_pk": seguimiento.id_relevamiento_id,
                "pk": seguimiento.id,
            },
        ),
        {"estado_validacion": VALIDADO},
    )

    seguimiento.refresh_from_db()
    assert seguimiento.estado_validacion == VALIDADO


@pytest.mark.parametrize("estado, visible", [(PENDIENTE, True), (VALIDADO, False)])
def test_boton_revisar_del_relevamiento_se_oculta_si_esta_validado(
    client, estado, visible
):
    relevamiento = _relevamiento(estado)
    _coordinador(client)

    response = client.get(
        reverse(
            "relevamiento_detalle",
            kwargs={"comedor_pk": relevamiento.comedor_id, "pk": relevamiento.id},
        )
    )

    assert response.status_code == 200
    assert (
        'data-bs-target="#modalRevisionCoordinador"' in response.content.decode()
    ) is visible


@pytest.mark.parametrize("estado, visible", [(PENDIENTE, True), (VALIDADO, False)])
def test_boton_revisar_del_seguimiento_se_oculta_si_esta_validado(
    client, estado, visible
):
    seguimiento = _seguimiento(estado)
    _coordinador(client)

    response = client.get(
        reverse(
            "seguimiento_detalle",
            kwargs={
                "comedor_pk": seguimiento.id_relevamiento.comedor_id,
                "relevamiento_pk": seguimiento.id_relevamiento_id,
                "pk": seguimiento.id,
            },
        )
    )

    assert response.status_code == 200
    assert (
        'data-bs-target="#modalRevisionSeguimiento"' in response.content.decode()
    ) is visible
