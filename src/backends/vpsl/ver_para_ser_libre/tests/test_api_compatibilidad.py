"""La API React conserva las excepciones históricas del backend oficial."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from ver_para_ser_libre.models import RegistroNominalVPSL, ResultadoAtencion
from ver_para_ser_libre.tests.test_jornadas_previas_al_flujo_ubicacion import (
    _crear_itinerario,
    _crear_jornada_previa,
    _crear_sede,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def jornada_historica(client, settings):
    settings.ROOT_URLCONF = "config.urls_all"
    client.force_login(
        get_user_model().objects.create_superuser(username="api-compatibilidad")
    )
    jornada = _crear_jornada_previa(_crear_itinerario(), _crear_sede())
    jornada.estado = "habilitada"
    jornada.save(update_fields=["estado"])
    return jornada


def campos(client, kind, pk):
    response = client.get(reverse("vpsl_api_form", args=[kind, pk]))
    assert response.status_code == 200, response.content
    return {field["name"]: field for field in response.json()["fields"]}


def test_api_conserva_localidad_y_campos_opcionales_de_jornada_previa(
    client, jornada_historica
):
    response = client.get(
        reverse("vpsl_api_jornada_detail", args=[jornada_historica.pk])
    )
    assert response.status_code == 200
    assert response.json()["localidad"] == "Berazategui"
    editar = campos(client, "jornada-edit", jornada_historica.pk)
    crear = campos(client, "jornada-create", jornada_historica.itinerario_id)
    for name in ("localidad", "ubicacion_url"):
        assert editar[name]["required"] is False
        assert crear[name]["required"] is True


@pytest.mark.parametrize(
    "resultado, opcional",
    [(ResultadoAtencion.ENTREGADO_DIA, True), (ResultadoAtencion.NO_REQUIERE, False)],
)
def test_api_identifica_excepcion_de_graduacion_solo_en_registros_previos(
    client, jornada_historica, resultado, opcional
):
    registro = RegistroNominalVPSL.objects.create(
        jornada=jornada_historica,
        dni="30111222",
        nombre="Ana",
        apellido="Perez",
        numero_acta="1",
        resultado=resultado,
        cantidad_lentes=1 if opcional else 0,
    )
    editar = campos(client, "registro-edit", registro.pk)
    crear = campos(client, "registro-create", jornada_historica.pk)
    for name in ("graduacion_izquierda", "graduacion_derecha"):
        assert editar[name]["graduacion_opcional"] is opcional
        assert crear[name]["graduacion_opcional"] is False
