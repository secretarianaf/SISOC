from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from core.models import Localidad, Municipio, Provincia
from ver_para_ser_libre.models import EstadoItinerario, ItinerarioVPSL
from ver_para_ser_libre.tests.test_workflow import (
    crear_itinerario,
    crear_sede,
    hacer_usuario_provincial,
)


pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def vpsl_urls(settings):
    settings.ROOT_URLCONF = "config.urls_all"


def test_api_requiere_sesion(client):
    response = client.get(reverse("vpsl_api_itinerarios"))
    assert response.status_code == 401
    assert response.json()["detail"]


def test_sesion_autenticada_devuelve_json_y_cookie_csrf(client):
    user = get_user_model().objects.create_superuser(
        username="vpsl-api-session",
        email="vpsl-api-session@example.com",
        password="testpass123",
    )
    client.force_login(user)

    response = client.get(reverse("vpsl_api_session"))

    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/json")
    assert response.json()["can_view_itinerarios"] is True
    assert "csrftoken" in response.cookies


def test_itinerarios_aislados_por_provincia(client):
    buenos_aires = Provincia.objects.create(nombre="Buenos Aires")
    cordoba = Provincia.objects.create(nombre="Córdoba")
    own = crear_itinerario(provincia=buenos_aires)
    other = crear_itinerario(
        provincia=cordoba,
        sedes=[crear_sede(cueanexo="API-CORDOBA", jurisdiccion="Córdoba")],
    )
    user = get_user_model().objects.create_user(
        username="vpsl-api-provincial", password="testpass123"
    )
    hacer_usuario_provincial(user, buenos_aires)
    client.force_login(user)

    listing = client.get(reverse("vpsl_api_itinerarios"))
    assert listing.status_code == 403  # permiso explícito requerido además del alcance
    from django.contrib.auth.models import Permission

    user.user_permissions.add(Permission.objects.get(codename="view_itinerariovpsl"))
    listing = client.get(reverse("vpsl_api_itinerarios"))
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()["results"]] == [own.pk]
    assert (
        client.get(reverse("vpsl_api_itinerario_detail", args=[other.pk])).status_code
        == 404
    )


def test_superusuario_puede_crear_itinerario_con_form_existente(client):
    user = get_user_model().objects.create_superuser(
        username="vpsl-api-admin",
        email="vpsl-api-admin@example.com",
        password="testpass123",
    )
    province = Provincia.objects.create(nombre="Buenos Aires")
    client.force_login(user)

    response = client.post(
        reverse("vpsl_api_itinerarios"),
        {
            "provincia": str(province.pk),
            "fecha_inicio": date(2026, 10, 1).isoformat(),
            "fecha_fin": date(2026, 10, 3).isoformat(),
            "referente_nombre": "Ana",
            "referente_telefono": "221111111",
            "referente_email": "ana@example.com",
            "carta_archivo": SimpleUploadedFile(
                "carta.pdf", b"contenido", content_type="application/pdf"
            ),
        },
    )

    assert response.status_code == 201, response.content
    item = ItinerarioVPSL.objects.get(pk=response.json()["id"])
    assert not item.sedes.exists()
    assert item.creado_por == user
    assert (
        client.get(reverse("vpsl_api_itinerario_detail", args=[item.pk])).status_code
        == 200
    )


def test_opciones_devuelven_provincias_sin_sedes_tentativas(client):
    user = get_user_model().objects.create_superuser(
        username="vpsl-api-opciones",
        email="vpsl-api-opciones@example.com",
        password="testpass123",
    )
    province = Provincia.objects.create(nombre="Buenos Aires")
    client.force_login(user)

    response = client.get(reverse("vpsl_api_options"))

    assert response.status_code == 200
    assert {item["id"] for item in response.json()["provincias"]} == {province.pk}
    assert "sedes" not in response.json()


def test_formulario_react_reutiliza_validacion_django(client):
    user = get_user_model().objects.create_superuser(
        username="vpsl-api-form",
        email="vpsl-api-form@example.com",
        password="testpass123",
    )
    client.force_login(user)
    url = reverse("vpsl_api_form", args=["sede-create", 0])

    schema = client.get(url)
    assert schema.status_code == 200
    assert {field["name"] for field in schema.json()["fields"]} >= {
        "provincia",
        "localidad",
        "nombre",
        "domicilio",
    }

    invalid = client.post(url, {})
    assert invalid.status_code == 400
    assert "nombre" in invalid.json()


def test_accion_react_requiere_permiso(client):
    user = get_user_model().objects.create_user(
        username="vpsl-api-action", password="testpass123"
    )
    client.force_login(user)
    response = client.post(reverse("vpsl_api_action", args=["presentar", 123]))
    assert response.status_code == 403


def test_preview_ubicacion_react_valida_coordenadas(client):
    user = get_user_model().objects.create_superuser(
        username="vpsl-api-map",
        email="vpsl-api-map@example.com",
        password="testpass123",
    )
    client.force_login(user)

    response = client.post(
        reverse("vpsl_api_ubicacion"),
        {"ubicacion_url": "-34.603700, -58.381600"},
    )

    assert response.status_code == 200
    assert response.json()["query"] == "-34.603700,-58.381600"


def test_presentacion_desde_react_usa_workflow_existente(client):
    user = get_user_model().objects.create_superuser(
        username="vpsl-api-workflow",
        email="vpsl-api-workflow@example.com",
        password="testpass123",
    )
    itinerary = crear_itinerario()
    client.force_login(user)

    response = client.post(reverse("vpsl_api_action", args=["presentar", itinerary.pk]))

    assert response.status_code == 200, response.content
    itinerary.refresh_from_db()
    assert itinerary.estado == EstadoItinerario.PRESENTADO
    preview = client.get(
        reverse("vpsl_api_action", args=["eliminar-itinerario", itinerary.pk])
    )
    assert preview.status_code == 200
    assert preview.json()["preview"]["total_afectados"] >= 1


def test_crear_jornada_desde_formulario_react(client):
    user = get_user_model().objects.create_superuser(
        username="vpsl-api-jornada",
        email="vpsl-api-jornada@example.com",
        password="testpass123",
    )
    itinerary = crear_itinerario()
    locality = Localidad.objects.create(
        nombre="La Plata",
        municipio=Municipio.objects.create(
            nombre="La Plata", provincia=itinerary.provincia
        ),
    )
    itinerary.estado = EstadoItinerario.APROBADO
    itinerary.save(update_fields=["estado"])
    client.force_login(user)
    create_schema = client.get(
        reverse("vpsl_api_form", args=["jornada-create", itinerary.pk])
    )
    assert create_schema.status_code == 200
    assert (
        next(
            field
            for field in create_schema.json()["fields"]
            if field["name"] == "vehiculos"
        )["value"]
        == []
    )

    response = client.post(
        reverse("vpsl_api_form", args=["jornada-create", itinerary.pk]),
        {
            "fecha": "2026-05-02",
            "sede": "Escuela 1",
            "localidad": str(locality.pk),
            "ubicacion_url": "-34.603700, -58.381600",
            "horario_inicio": "09:00",
            "horario_fin": "18:00",
            "referente_dni": "12345678",
            "referente_sexo": "F",
        },
    )

    assert response.status_code == 200, response.content
    assert response.json()["redirect"].startswith("jornadas/")
    assert itinerary.jornadas.count() == 1
    detail = client.get(
        reverse("vpsl_api_jornada_detail", args=[itinerary.jornadas.get().pk])
    )
    assert detail.status_code == 200
    assert detail.json()["checklist"] == []
    assert detail.json()["localidad"] == "La Plata"
    assert detail.json()["mapa_query"]
    edit = client.get(
        reverse("vpsl_api_form", args=["jornada-edit", itinerary.jornadas.get().pk])
    )
    assert edit.status_code == 200
    assert {field["name"] for field in edit.json()["fields"]} >= {
        "ubicacion_url",
        "vehiculos",
    }
