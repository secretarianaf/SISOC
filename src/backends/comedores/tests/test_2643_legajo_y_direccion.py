"""#2643 (feedback de QA del 8 y 9/10): legajo del comedor y dirección completa.

1. Solo el relevamiento inicial actualiza el legajo del comedor. El PATCH de un
   seguimiento con un bloque ``comedor`` no cambia nada (antes lo aplicaba).
2. La API territorial expone la dirección completa del comedor (piso,
   departamento, manzana, lote, partido): la app precarga con ella el
   domicilio del PNUD y le faltaban esos campos.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from comedores.models import Comedor, Referente
from core.models import Provincia
from relevamientos.models import PrimerSeguimiento, Relevamiento
from users.models import TerritorialComedorProvincia

pytestmark = pytest.mark.django_db

SEGUIMIENTO_URL = "/api/relevamiento/primer-seguimiento"

DIRECCION = {
    "calle": "Choele Choel",
    "numero": 831,
    "entre_calle_1": "Alsina",
    "entre_calle_2": "Mitre",
    "piso": "2",
    "departamento": "B",
    "manzana": "12",
    "lote": "4",
    "partido": "Lanús",
    "barrio": "Valentín Alsina",
    "codigo_postal": 1822,
}


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


def test_el_seguimiento_no_actualiza_el_legajo_del_comedor():
    provincia = Provincia.objects.create(nombre="Prov legajo 2643")
    comedor = Comedor.objects.create(
        nombre="Comedor legajo 2643", provincia=provincia, **DIRECCION
    )
    user, client = _territorial("legajo_2643", provincia)
    relevamiento = Relevamiento.objects.create(
        comedor=comedor, estado="Finalizado", territorial_user=user
    )
    seguimiento = PrimerSeguimiento.objects.create(
        id_relevamiento=relevamiento, estado=PrimerSeguimiento.ESTADO_ASIGNADO
    )

    response = client.patch(
        SEGUIMIENTO_URL,
        {
            "sisoc_id": seguimiento.id,
            "estado": PrimerSeguimiento.ESTADO_COMPLETO,
            "comedor": {"calle": "Pisada", "numero": "742", "barrio": "Centro"},
        },
        format="json",
    )

    assert response.status_code == 200, response.data
    seguimiento.refresh_from_db()
    assert seguimiento.estado == PrimerSeguimiento.ESTADO_COMPLETO
    comedor.refresh_from_db()
    for campo, valor in DIRECCION.items():
        assert getattr(comedor, campo) == valor, campo


def test_la_api_territorial_expone_la_direccion_completa():
    provincia = Provincia.objects.create(nombre="Prov direccion 2643")
    comedor = Comedor.objects.create(
        nombre="Comedor direccion 2643", provincia=provincia, **DIRECCION
    )
    _, client = _territorial("direccion_2643", provincia)

    # El listado asignado usa el mismo serializer que el detalle; la zona tiene
    # el suyo y también precarga altas (N18), así que se verifica aparte.
    detalle = client.get(f"/api/territorial/comedores/{comedor.id}/")
    zona = client.get("/api/territorial/comedores-zona/")

    assert detalle.status_code == 200, detalle.data
    for campo, valor in DIRECCION.items():
        assert detalle.data[campo] == valor, campo
    assert zona.status_code == 200, zona.data
    items = zona.data["results"] if isinstance(zona.data, dict) else zona.data
    en_zona = next(c for c in items if c["id"] == comedor.id)
    for campo, valor in DIRECCION.items():
        assert en_zona[campo] == valor, campo


@pytest.mark.parametrize("url", [SEGUIMIENTO_URL, "/api/relevamiento/seguimiento"])
@pytest.mark.parametrize("referente_de_otro_comedor", [False, True])
def test_el_seguimiento_no_modifica_un_referente_del_legajo(
    url, referente_de_otro_comedor
):
    provincia = Provincia.objects.create(nombre="Prov referente 2643")
    referente = Referente.objects.create(
        documento=30555777,
        nombre="Ana",
        apellido="Lopez",
        mail="original@example.com",
        celular=1144556677,
        funcion="Coordinadora",
    )
    comedor = Comedor.objects.create(
        nombre="Comedor referente 2643", provincia=provincia
    )
    legajo = comedor
    if referente_de_otro_comedor:
        legajo = Comedor.objects.create(
            nombre="Otro comedor referente 2643", provincia=provincia
        )
    legajo.referente = referente
    legajo.save(update_fields=["referente"])
    user, client = _territorial("referente_2643", provincia)
    relevamiento = Relevamiento.objects.create(
        comedor=comedor, estado="Finalizado", territorial_user=user
    )
    seguimiento = PrimerSeguimiento.objects.create(
        id_relevamiento=relevamiento,
        referente=referente,
        estado=PrimerSeguimiento.ESTADO_ASIGNADO,
    )

    for mail in ("visita@example.com", "corregido@example.com"):
        response = client.patch(
            url,
            {
                "sisoc_id": seguimiento.id,
                "referente": {"documento": "30.555.777", "mail": mail},
            },
            format="json",
        )
        assert response.status_code == 200, response.data
        referente.refresh_from_db()
        legajo.refresh_from_db()
        assert legajo.referente_id == referente.id
        assert referente.mail == "original@example.com"
        seguimiento.refresh_from_db()
        assert seguimiento.referente_id != referente.id
        assert seguimiento.referente.mail == mail
        assert seguimiento.referente.documento == referente.documento
        assert seguimiento.referente.nombre == referente.nombre
        assert seguimiento.referente.apellido == referente.apellido
        assert seguimiento.referente.celular == referente.celular
        assert seguimiento.referente.funcion == referente.funcion
        assert Referente.objects.filter(documento=referente.documento).count() == 2
