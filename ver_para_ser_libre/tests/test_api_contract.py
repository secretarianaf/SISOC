"""Regresiones del transporte, paridad y paginación de Front v2."""

import json

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from ver_para_ser_libre.models import (
    CasoLaboratorioVPSL,
    ChecklistJornadaVPSL,
    CierreDiarioVPSL,
    EstadoEvaluacionVPSL,
    EstadoItinerario,
    HistorialChecklistSedeVPSL,
    HistorialCierreDiarioVPSL,
    RegistroNominalVPSL,
)
from ver_para_ser_libre.tests.test_jornadas_previas_al_flujo_ubicacion import (
    _crear_itinerario,
    _crear_jornada_previa,
    _crear_sede,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client, settings):
    settings.ROOT_URLCONF = "config.urls"
    client.force_login(
        get_user_model().objects.create_superuser(username="api-contract")
    )
    return client


@pytest.mark.parametrize("encoding", ["json", "multipart"])
def test_ubicacion_acepta_ambos_transportes(admin_client, encoding):
    payload = {"ubicacion_url": "-34.603700, -58.381600"}
    kwargs = {"data": payload}
    if encoding == "json":
        kwargs = {"data": json.dumps(payload), "content_type": "application/json"}
    response = admin_client.post(reverse("vpsl_api_ubicacion"), **kwargs)
    assert response.status_code == 200
    assert response.json()["query"] == "-34.603700,-58.381600"


def test_json_no_acepta_un_array_como_payload(admin_client):
    response = admin_client.post(
        reverse("vpsl_api_ubicacion"), "[]", content_type="application/json"
    )
    assert response.status_code == 400
    assert "detail" in response.json()


def test_subsanacion_muestra_instrucciones_y_guarda_carta_corregida(admin_client):
    item = _crear_itinerario()
    item.estado = EstadoItinerario.EN_SUBSANACION
    item.carta_archivo_estado = EstadoEvaluacionVPSL.SUBSANAR
    item.subsanacion_observaciones = "Reemplazar la carta sin firma."
    item.save()
    endpoint = reverse("vpsl_api_form", args=["itinerario-subsanar", item.pk])
    schema = admin_client.get(endpoint).json()
    assert schema["instrucciones"] == item.subsanacion_observaciones
    response = admin_client.post(
        endpoint, {"carta_archivo": SimpleUploadedFile("corregida.pdf", b"firma")}
    )
    assert response.status_code == 200, response.content
    assert response.json()["ok"] is True
    assert "fields" not in response.json()
    item.refresh_from_db()
    assert item.estado == EstadoItinerario.SUBSANADO


def test_detalle_conserva_evidencias_y_actas_anteriores(admin_client):
    jornada = _crear_jornada_previa(_crear_itinerario(), _crear_sede())
    checklist = ChecklistJornadaVPSL.objects.create(
        jornada=jornada, item="electricidad", cumple=True, evidencia="evidencia.pdf"
    )
    HistorialChecklistSedeVPSL.objects.create(
        checklist=checklist, cumple_nuevo=True, observacion_nueva="Verificado"
    )
    cierre = CierreDiarioVPSL.objects.create(
        jornada=jornada, responsable_cierre="Ana", acta_adjunta="actual.pdf"
    )
    HistorialCierreDiarioVPSL.objects.create(
        cierre=cierre,
        responsable="Ana",
        acta_adjunta="previa.pdf",
        cantidad_atenciones_registradas=1,
        cantidad_lentes_entregados_dia=1,
        cantidad_casos_laboratorio_reportados=0,
    )
    response = admin_client.get(reverse("vpsl_api_jornada_detail", args=[jornada.pk]))
    assert response.status_code == 200, response.content
    data = response.json()
    assert data["checklist"][0]["evidencia_url"].endswith("evidencia.pdf")
    assert data["checklist"][0]["historial"][0]["observacion"] == "Verificado"
    assert data["cierre"]["acta_adjunta_url"].endswith("actual.pdf")
    assert data["cierre"]["historial"][0]["acta_adjunta_url"].endswith("previa.pdf")


def test_colecciones_de_jornada_paginadas_y_sin_carga_duplicada(admin_client):
    jornada = _crear_jornada_previa(_crear_itinerario(), _crear_sede())
    registros = RegistroNominalVPSL.objects.bulk_create(
        [
            RegistroNominalVPSL(
                jornada=jornada,
                dni=str(30000000 + i),
                nombre="Ana",
                apellido="Perez",
                numero_acta=str(i),
            )
            for i in range(27)
        ]
    )
    CasoLaboratorioVPSL.objects.bulk_create(
        [CasoLaboratorioVPSL(registro=item) for item in registros]
    )
    detail = admin_client.get(
        reverse("vpsl_api_jornada_detail", args=[jornada.pk])
    ).json()
    assert detail["registros_total"] == 27
    assert "registros" not in detail and "laboratorio" not in detail
    for name in ("vpsl_api_registros", "vpsl_api_laboratorio"):
        endpoint = reverse(name, args=[jornada.pk])
        first = admin_client.get(endpoint).json()
        assert first["count"] == 27
        assert len(first["results"]) == 25
        assert first["next"]
        second = admin_client.get(endpoint, {"page": 2}).json()
        assert len(second["results"]) == 2
        assert second["previous"] and second["next"] is None


def test_json_exige_csrf_y_conserva_validaciones_del_formulario(settings):
    from django.test import Client

    settings.ROOT_URLCONF = "config.urls"
    client = Client(enforce_csrf_checks=True)
    client.force_login(get_user_model().objects.create_superuser(username="api-csrf"))
    token = client.get(reverse("vpsl_api_session")).cookies["csrftoken"].value
    endpoint = reverse("vpsl_api_form", args=["sede-create", 0])
    missing_token = client.post(endpoint, "{}", content_type="application/json")
    assert missing_token.status_code == 403
    invalid = client.post(
        endpoint, "{}", content_type="application/json", HTTP_X_CSRFTOKEN=token
    )
    assert invalid.status_code == 400
    assert "nombre" in invalid.json()


def test_paginas_respetan_permiso_y_alcance_provincial(client, settings):
    from django.contrib.auth.models import Permission
    from core.models import Provincia
    from ver_para_ser_libre.tests.test_workflow import (
        crear_itinerario,
        crear_jornada,
        crear_sede,
        hacer_usuario_provincial,
    )

    settings.ROOT_URLCONF = "config.urls"
    own_province = Provincia.objects.create(nombre="Buenos Aires")
    other_province = Provincia.objects.create(nombre="Cordoba")
    own = crear_jornada(
        crear_itinerario(provincia=own_province, sedes=[crear_sede(cueanexo="OWN-API")])
    )
    other = crear_jornada(
        crear_itinerario(
            provincia=other_province, sedes=[crear_sede(cueanexo="OTHER-API")]
        )
    )
    user = get_user_model().objects.create_user(username="api-page-provincia")
    hacer_usuario_provincial(user, own_province)
    client.force_login(user)
    for endpoint_name in ("vpsl_api_registros", "vpsl_api_laboratorio"):
        assert client.get(reverse(endpoint_name, args=[own.pk])).status_code == 403
    user.user_permissions.add(Permission.objects.get(codename="view_jornadavpsl"))
    for endpoint_name in ("vpsl_api_registros", "vpsl_api_laboratorio"):
        assert client.get(reverse(endpoint_name, args=[own.pk])).status_code == 200
        assert client.get(reverse(endpoint_name, args=[other.pk])).status_code == 404
