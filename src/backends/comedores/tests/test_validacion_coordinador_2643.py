"""#2643: la validación del coordinador solo la decide el coordinador.

1. El PATCH de la app no puede escribir los campos de la revisión: un
   territorial con un registro "Pendiente validación coordinador" podía mandar
   ``estado_validacion: "Validado"`` y autovalidarse.
2. Un relevamiento o un seguimiento PAC asignado y todavía no enviado no tiene
   nada que revisar (igual que las actas y los PNUD ``sin_cargar``): validarlo
   lo bloquearía para siempre en la app.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from comedores.models import Comedor
from core.models import Provincia
from relevamientos.models import PrimerSeguimiento, Relevamiento
from users.models import TerritorialComedorProvincia

pytestmark = pytest.mark.django_db

PENDIENTE = Relevamiento.ESTADO_VALIDACION_PENDIENTE
A_SUBSANAR = Relevamiento.ESTADO_VALIDACION_A_SUBSANAR
VALIDADO = Relevamiento.ESTADO_VALIDACION_VALIDADO
BOTON_REVISAR = 'data-bs-target="#modalRevisionCoordinador"'
BOTON_REVISAR_SEGUIMIENTO = 'data-bs-target="#modalRevisionSeguimiento"'


def _territorial(nombre, provincia):
    user = get_user_model().objects.create_user(
        username=f"terr_{nombre}", password="testpass123"
    )
    user.profile.es_territorial_comedor = True
    user.profile.save(update_fields=["es_territorial_comedor"])
    TerritorialComedorProvincia.objects.create(
        profile=user.profile, provincia=provincia
    )
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return user, client


def _relevamiento(nombre, **kwargs):
    provincia = Provincia.objects.create(nombre=f"Prov {nombre}")
    comedor = Comedor.objects.create(nombre=f"Comedor {nombre}", provincia=provincia)
    return provincia, Relevamiento.objects.create(comedor=comedor, **kwargs)


def _coordinador(client):
    user = get_user_model().objects.create_user(
        username="coord_2643", password="testpass123"
    )
    for codename in ("review_relevamiento", "view_relevamiento"):
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="relevamientos", codename=codename
            )
        )
    client.force_login(user)
    return user


# ------------------------------------------------------------ autovalidación


@pytest.mark.parametrize("previo", [None, PENDIENTE, A_SUBSANAR])
def test_patch_relevamiento_no_escribe_la_revision(previo):
    provincia, relevamiento = _relevamiento(
        f"auto_{previo}", estado="Visita pendiente", estado_validacion=previo
    )
    user, client = _territorial(f"auto_rel_{previo}", provincia)
    relevamiento.territorial_user = user
    relevamiento.save(update_fields=["territorial_user"])

    response = client.patch(
        "/api/relevamiento",
        {
            "sisoc_id": relevamiento.id,
            "estado": "Finalizado",
            "estado_validacion": VALIDADO,
            "observaciones_coordinador": "Me autovalido",
            "coordinador": user.id,
        },
        format="json",
    )

    assert response.status_code == 200, response.data
    relevamiento.refresh_from_db()
    assert relevamiento.estado == "Finalizado"
    assert relevamiento.estado_validacion == PENDIENTE
    assert relevamiento.observaciones_coordinador is None
    assert relevamiento.coordinador_id is None


def test_patch_seguimiento_no_escribe_la_revision():
    provincia, relevamiento = _relevamiento("auto_seg", estado="Finalizado")
    user, client = _territorial("auto_seg", provincia)
    relevamiento.territorial_user = user
    relevamiento.save(update_fields=["territorial_user"])
    seguimiento = PrimerSeguimiento.objects.create(
        id_relevamiento=relevamiento,
        estado=PrimerSeguimiento.ESTADO_ASIGNADO,
        estado_validacion=PENDIENTE,
    )

    response = client.patch(
        "/api/relevamiento/primer-seguimiento",
        {
            "sisoc_id": seguimiento.id,
            "estado": PrimerSeguimiento.ESTADO_COMPLETO,
            "estado_validacion": VALIDADO,
            "observaciones_coordinador": "Me autovalido",
        },
        format="json",
    )

    assert response.status_code == 200, response.data
    seguimiento.refresh_from_db()
    assert seguimiento.estado == PrimerSeguimiento.ESTADO_COMPLETO
    assert seguimiento.estado_validacion == PENDIENTE
    assert seguimiento.observaciones_coordinador is None


# ------------------------------------------------- nada que revisar todavía


def _url_detalle(relevamiento):
    return reverse(
        "relevamiento_detalle",
        kwargs={"comedor_pk": relevamiento.comedor_id, "pk": relevamiento.id},
    )


def _url_revision(relevamiento):
    return reverse(
        "relevamiento_revision_coordinador",
        kwargs={"comedor_pk": relevamiento.comedor_id, "pk": relevamiento.id},
    )


@pytest.mark.parametrize("estado", ["Pendiente", "Visita pendiente", "En Proceso"])
def test_relevamiento_sin_enviar_no_se_puede_revisar(client, estado):
    _, relevamiento = _relevamiento(f"sin_enviar_{estado}", estado=estado)
    _coordinador(client)

    detalle = client.get(_url_detalle(relevamiento))
    client.post(_url_revision(relevamiento), {"estado_validacion": VALIDADO})

    assert BOTON_REVISAR not in detalle.content.decode()
    relevamiento.refresh_from_db()
    assert relevamiento.estado_validacion is None


@pytest.mark.parametrize(
    "estado,estado_validacion",
    [
        # Histórico de GESTIONAR: finalizado antes del circuito de validación.
        ("Finalizado", None),
        ("Finalizado/Excepciones", None),
        ("Finalizado", PENDIENTE),
        ("Finalizado", A_SUBSANAR),
    ],
)
def test_relevamiento_enviado_se_puede_revisar(client, estado, estado_validacion):
    _, relevamiento = _relevamiento(
        f"enviado_{estado}_{estado_validacion}",
        estado=estado,
        estado_validacion=estado_validacion,
    )
    _coordinador(client)

    detalle = client.get(_url_detalle(relevamiento))
    client.post(_url_revision(relevamiento), {"estado_validacion": VALIDADO})

    assert BOTON_REVISAR in detalle.content.decode()
    relevamiento.refresh_from_db()
    assert relevamiento.estado_validacion == VALIDADO


def _url_seguimiento(seguimiento, sufijo=""):
    nombre = "seguimiento_revision_coordinador" if sufijo else "seguimiento_detalle"
    return reverse(
        nombre,
        kwargs={
            "comedor_pk": seguimiento.id_relevamiento.comedor_id,
            "relevamiento_pk": seguimiento.id_relevamiento_id,
            "pk": seguimiento.id,
        },
    )


@pytest.mark.parametrize(
    "estado,estado_validacion,revisable",
    [
        (PrimerSeguimiento.ESTADO_ASIGNADO, None, False),
        (PrimerSeguimiento.ESTADO_EN_PROCESO, None, False),
        (PrimerSeguimiento.ESTADO_COMPLETO, None, True),
        (PrimerSeguimiento.ESTADO_COMPLETO, PENDIENTE, True),
    ],
)
def test_seguimiento_solo_se_revisa_una_vez_enviado(
    client, estado, estado_validacion, revisable
):
    _, relevamiento = _relevamiento(
        f"seg_{estado}_{estado_validacion}", estado="Finalizado"
    )
    seguimiento = PrimerSeguimiento.objects.create(
        id_relevamiento=relevamiento, estado=estado, estado_validacion=estado_validacion
    )
    _coordinador(client)

    detalle = client.get(_url_seguimiento(seguimiento))
    client.post(
        _url_seguimiento(seguimiento, "revision"), {"estado_validacion": VALIDADO}
    )

    assert (BOTON_REVISAR_SEGUIMIENTO in detalle.content.decode()) is revisable
    seguimiento.refresh_from_db()
    assert (seguimiento.estado_validacion == VALIDADO) is revisable
