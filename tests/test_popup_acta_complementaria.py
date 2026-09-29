"""H5 (QA 28/9): el popup de Alimentar Comunidad ofrece el acta complementaria
extraordinaria en lugar del acta de excepción.

El acta de excepción sigue existiendo como instancia del ciclo (la app la
puede cargar y las existentes se siguen viendo); solo deja de ofrecerse en el
backoffice.
"""

import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from comedores.models import Comedor, Programas
from core.models import Provincia
from relevamientos.models import (
    ActaComplementaria,
    ActaExcepcionSeguimiento,
    PrimerSeguimiento,
    Relevamiento,
)
from users.models import TerritorialComedorProvincia

pytestmark = pytest.mark.django_db


@pytest.fixture
def comedor():
    provincia = Provincia.objects.create(nombre="Prov H5")
    return Comedor.objects.create(
        nombre="Comedor H5",
        provincia=provincia,
        programa=Programas.objects.create(nombre="Alimentar comunidad"),
    )


@pytest.fixture
def territorial(comedor):
    user = get_user_model().objects.create_user(username="terr_h5", password="x")
    user.profile.es_territorial_comedor = True
    user.profile.save(update_fields=["es_territorial_comedor"])
    TerritorialComedorProvincia.objects.create(
        profile=user.profile, provincia=comedor.provincia
    )
    return user


def _login(client, *codenames):
    user = get_user_model().objects.create_user(username="bo_h5", password="x")
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="relevamientos", codename__in=codenames
        )
    )
    client.force_login(user)
    return user


def _post(client, comedor, tipo, territorial, **extra):
    return client.post(
        reverse("relevamiento_create_edit_ajax", kwargs={"pk": comedor.pk}),
        {
            "tipo_relevamiento": tipo,
            "territorial": json.dumps(
                {"gestionar_uid": str(territorial.id), "nombre": "Terr"}
            ),
            **extra,
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )


def test_el_popup_ofrece_acta_complementaria_y_no_acta_de_excepcion(client, comedor):
    Relevamiento.objects.create(comedor=comedor, estado="Visita pendiente")
    _login(client, "view_relevamiento", "add_relevamiento")

    html = client.get(
        reverse("relevamientos", kwargs={"comedor_pk": comedor.pk})
    ).content.decode()

    assert 'value="acta_complementaria"' in html
    assert "Acta complementaria extraordinaria" in html
    assert 'value="acta_excepcion"' not in html
    assert "Acta de excepción (visita no realizada)" not in html


def test_crea_el_acta_complementaria_asignada_al_territorial(
    client, comedor, territorial
):
    _login(client, "add_relevamiento", "add_actacomplementaria")

    response = _post(client, comedor, "acta_complementaria", territorial)

    assert response.status_code == 200, response.content
    acta = ActaComplementaria.objects.get()
    assert response.json()["url"] == reverse(
        "acta_complementaria_detalle",
        kwargs={"comedor_pk": comedor.pk, "pk": acta.pk},
    )
    assert acta.comedor_id == comedor.id
    assert acta.tecnico_id == territorial.id
    assert acta.origen == ActaComplementaria.ORIGEN_SISOC
    assert acta.asignado_desde_sisoc is True
    assert not acta.prestaciones.exists()


def test_acta_complementaria_exige_permiso(client, comedor, territorial):
    _login(client, "add_relevamiento")

    response = _post(client, comedor, "acta_complementaria", territorial)

    assert response.status_code == 403
    assert not ActaComplementaria.objects.exists()


def test_acta_complementaria_no_se_ofrece_en_pnud(client, territorial):
    comedor = Comedor.objects.create(
        nombre="PNUD H5",
        provincia=territorial.profile.territorial_comedor_provincias.first().provincia,
        programa=Programas.objects.create(nombre="Abordaje comunitario - Línea Secos"),
    )
    _login(client, "add_relevamiento", "add_actacomplementaria")

    response = _post(client, comedor, "acta_complementaria", territorial)

    assert response.status_code == 400
    assert not ActaComplementaria.objects.exists()


@pytest.mark.parametrize("con_relevamiento", [False, True])
def test_acta_de_excepcion_ya_no_se_crea_desde_el_popup(
    client, comedor, territorial, con_relevamiento
):
    extra = {}
    if con_relevamiento:
        relevamiento = Relevamiento.objects.create(
            comedor=comedor, estado="Visita pendiente"
        )
        extra["relevamiento_id"] = str(relevamiento.id)
    _login(client, "add_relevamiento")

    response = _post(client, comedor, "acta_excepcion", territorial, **extra)

    assert response.status_code == 400
    assert not PrimerSeguimiento.objects.exists()


def test_actas_de_excepcion_existentes_se_siguen_viendo(client, comedor):
    relevamiento = Relevamiento.objects.create(comedor=comedor, estado="En Proceso")
    seguimiento = PrimerSeguimiento.objects.create(
        id_relevamiento=relevamiento,
        tipo=PrimerSeguimiento.TIPO_ACTA_EXCEPCION,
        numero_orden=1,
        acta_excepcion=ActaExcepcionSeguimiento.objects.create(
            detalle="No abrió el espacio"
        ),
    )
    _login(client, "view_relevamiento")

    response = client.get(
        reverse(
            "seguimiento_detalle",
            kwargs={
                "comedor_pk": comedor.pk,
                "relevamiento_pk": relevamiento.pk,
                "pk": seguimiento.pk,
            },
        )
    )

    assert response.status_code == 200
    assert "No abrió el espacio" in response.content.decode()


def test_el_territorial_ve_el_comedor_del_acta_asignada(client, comedor, territorial):
    _login(client, "add_relevamiento", "add_actacomplementaria")
    _post(client, comedor, "acta_complementaria", territorial)
    token, _ = Token.objects.get_or_create(user=territorial)
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    listado = api.get("/api/territorial/comedores/")
    detalle = api.get(f"/api/territorial/comedores/{comedor.id}/")

    assert comedor.id in [item["id"] for item in listado.json()["results"]]
    actas = detalle.json()["actas_complementarias"]
    assert actas["total"] == 1
    assert actas["items"][0]["origen"] == "sisoc"
