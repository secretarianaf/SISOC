"""Contrato y autorización de INET React sobre la misma lógica de VAT."""

from datetime import date, timedelta

import pytest
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient

from VAT.models import (
    AsistenciaSesion,
    Centro,
    ComisionCurso,
    ComisionHorario,
    Curso,
    Inscripcion,
    InstitucionUbicacion,
    ModalidadCursada,
    PlanVersionCurricular,
    Sector,
    SesionComision,
)
from ciudadanos.models import Ciudadano
from core.models import Dia, Localidad, Municipio, Provincia

pytestmark = pytest.mark.django_db


@pytest.fixture
def data():
    province = Provincia.objects.create(nombre="Buenos Aires")
    city = Municipio.objects.create(nombre="La Plata", provincia=province)
    locality = Localidad.objects.create(nombre="Tolosa", municipio=city)
    center = Centro.objects.create(
        nombre="CFP 401",
        codigo="060144900",
        provincia=province,
        municipio=city,
        localidad=locality,
    )
    sector = Sector.objects.create(nombre="Industria")
    mode = ModalidadCursada.objects.create(nombre="Presencial")
    plan = PlanVersionCurricular.objects.create(
        nombre="Electricidad",
        provincia=province,
        sector=sector,
        modalidad_cursada=mode,
        horas_reloj=100,
    )
    course = Curso.objects.create(
        nombre="Electricidad básica",
        centro=center,
        plan_estudio=plan,
        modalidad=mode,
        inscripcion_libre=True,
    )
    location = InstitucionUbicacion.objects.create(
        centro=center,
        localidad=locality,
        rol_ubicacion="sede_principal",
        domicilio="7 123",
    )
    commission = ComisionCurso.objects.create(
        curso=course,
        ubicacion=location,
        cupo_total=2,
        fecha_inicio=date.today() + timedelta(days=1),
        fecha_fin=date.today() + timedelta(days=40),
    )
    day = Dia.objects.create(nombre="Lunes")
    return {
        "center": center,
        "province": province,
        "city": city,
        "locality": locality,
        "sector": sector,
        "mode": mode,
        "plan": plan,
        "course": course,
        "location": location,
        "commission": commission,
        "day": day,
    }


@pytest.fixture
def api(superuser):
    client = APIClient()
    client.force_login(superuser)
    return client


def grant(user, *codes):
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="VAT", codename__in=codes)
    )


def test_session_requires_authentication_and_sets_csrf(api):
    anonymous = APIClient()
    assert anonymous.get("/api/inet/session/").status_code == 401
    response = api.get("/api/inet/session/")
    assert response.status_code == 200
    assert "csrftoken" in response.cookies
    assert "add_centro" in response.data["permissions"]


def test_session_enforces_csrf(superuser, data):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(superuser)
    assert (
        client.post("/api/inet/planes/", {"campos": {}}, format="json").status_code
        == 403
    )


def test_no_permission_is_403(user):
    client = APIClient()
    client.force_login(user)
    assert client.get("/api/inet/centros/").status_code == 403


@pytest.mark.parametrize(
    "street,number,expected",
    [("7", 123, "7 123"), ("", None, "Calle de actividad 456")],
)
def test_center_map_address_uses_street_or_activity_address(
    api, data, street, number, expected
):
    center = data["center"]
    center.calle = street
    center.numero = number
    center.domicilio_actividad = "Calle de actividad 456"
    center.save()
    response = api.get(f"/api/inet/centros/{center.pk}/")
    assert response.status_code == 200
    fields = {field["label"]: field["value"] for field in response.data["detalle"]}
    assert fields["Domicilio mapa"] == expected


@pytest.mark.parametrize(
    "resource",
    [
        "centros",
        "cursos",
        "comisiones",
        "contactos",
        "ubicaciones",
        "planes",
        "inscripciones",
        "sesiones",
    ],
)
def test_lists_are_paginated_and_contract_is_serializable(api, data, resource):
    response = api.get(f"/api/inet/{resource}/", {"page_size": 999})
    assert response.status_code == 200
    assert set(response.data) == {"count", "next", "previous", "results"}
    assert isinstance(response.json()["results"], list)


def test_referente_cannot_read_or_write_another_center(user, data):
    from django.contrib.auth.models import Group

    role, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Group),
        codename="role_centroreferentevat",
        defaults={"name": "Referente"},
    )
    user.user_permissions.add(role)
    grant(user, "view_centro", "view_curso", "add_curso", "change_curso")
    data["center"].referentes.add(user)
    other = Centro.objects.create(
        nombre="Otro CFP",
        codigo="060144901",
        provincia=data["province"],
        municipio=data["city"],
        localidad=data["locality"],
    )
    client = APIClient()
    client.force_login(user)
    response = client.get("/api/inet/centros/")
    assert [row["id"] for row in response.data["results"]] == [data["center"].pk]
    assert response.data["results"][0]["puede_gestionar"] is True
    assert response.data["results"][0]["puede_editar"] is False
    assert (
        client.get("/api/inet/cursos/form/", {"centro": data["center"].pk}).status_code
        == 200
    )
    assert client.get(f"/api/inet/centros/{other.pk}/").status_code == 404
    assert (
        client.post(
            "/api/inet/cursos/", {"campos": {"centro": other.pk}}, format="json"
        ).status_code
        == 404
    )


def test_course_reuses_plan_and_modality_validation(api, data):
    payload = {
        "centro": data["center"].pk,
        "nombre": "Curso nuevo",
        "plan_estudio": data["plan"].pk,
        "estado": "activo",
        "inscripcion_libre": True,
    }
    response = api.post("/api/inet/cursos/", {"campos": payload}, format="json")
    assert response.status_code == 201, response.data
    course = Curso.objects.get(pk=response.data["id"])
    assert course.modalidad == data["mode"]
    assert course.inscripcion_libre is True
    payload["plan_estudio"] = ""
    response = api.post("/api/inet/cursos/", {"campos": payload}, format="json")
    assert response.status_code == 400
    assert "plan_estudio" in response.data


def test_commission_validates_location_and_schedule_atomically(api, data):
    payload = {
        "curso": data["course"].pk,
        "ubicacion": data["location"].pk,
        "cupo_total": 5,
        "fecha_inicio": str(date.today() + timedelta(days=1)),
        "fecha_fin": str(date.today() + timedelta(days=40)),
        "estado": "planificada",
    }
    rows = [
        {
            "dia_semana": data["day"].pk,
            "hora_desde": "09:00",
            "hora_hasta": "09:30",
            "vigente": "1",
        }
    ]
    response = api.post(
        "/api/inet/comisiones/", {"campos": payload, "horarios": rows}, format="json"
    )
    assert response.status_code == 400
    assert ComisionCurso.objects.count() == 1
    rows[0]["hora_hasta"] = "12:00"
    response = api.post(
        "/api/inet/comisiones/", {"campos": payload, "horarios": rows}, format="json"
    )
    assert response.status_code == 201, response.data
    assert SesionComision.objects.filter(comision_curso_id=response.data["id"]).exists()


def test_enrollment_uses_capacity_and_rolls_back_citizen_on_failure(api, data):
    url = f'/api/inet/comisiones/{data["commission"].pk}/inscribir/'
    for index in range(2):
        response = api.post(
            url,
            {
                "ciudadano": {
                    "nombre": "Ana",
                    "apellido": "Perez",
                    "fecha_nacimiento": "1990-01-01",
                    "tipo_documento": "DNI",
                    "documento": str(30111222 + index),
                }
            },
            format="json",
        )
        assert response.status_code == 201, response.data
    response = api.post(
        url,
        {
            "ciudadano": {
                "nombre": "Sin cupo",
                "apellido": "Perez",
                "fecha_nacimiento": "1990-01-01",
                "tipo_documento": "DNI",
                "documento": "30111230",
            }
        },
        format="json",
    )
    assert response.status_code == 400
    assert Ciudadano.objects.count() == 2
    assert Inscripcion.objects.count() == 2


def test_sin_dni_uses_kernel_identity_and_required_reason(api, data):
    url = f'/api/inet/comisiones/{data["commission"].pk}/inscribir/'
    payload = {
        "tipo_registro_identidad": "SIN_DNI",
        "nombre": "Ana",
        "apellido": "Perez",
        "fecha_nacimiento": "1990-01-01",
        "telefono": "1122334455",
        "motivo_sin_dni": "DOCUMENTO_EXTRAVIADO",
    }
    response = api.post(url, {"ciudadano": payload}, format="json")
    assert response.status_code == 201, response.data
    citizen = Ciudadano.objects.get()
    assert citizen.documento is None
    assert citizen.tipo_registro_identidad == "SIN_DNI"
    assert response.data["identidad_pendiente"] is True


def test_attendance_rejects_foreign_or_incomplete_roster(api, data):
    citizen = Ciudadano.objects.create(
        nombre="Ana",
        apellido="Perez",
        documento=30111222,
        fecha_nacimiento="1990-01-01",
    )
    enrollment = Inscripcion.objects.create(
        ciudadano=citizen, comision_curso=data["commission"], estado="inscripta"
    )
    horario = ComisionHorario.objects.create(
        comision_curso=data["commission"],
        dia_semana=data["day"],
        hora_desde="09:00",
        hora_hasta="12:00",
    )
    session = SesionComision.objects.create(
        horario=horario,
        comision_curso=data["commission"],
        numero_sesion=1,
        fecha=date.today(),
    )
    url = f"/api/inet/sesiones/{session.pk}/asistencia/"
    assert api.get(url).data["filas"][0]["presente"] is None
    response = api.put(
        url, {"filas": [{"inscripcion_id": 999999, "presente": True}]}, format="json"
    )
    assert response.status_code == 400
    assert AsistenciaSesion.objects.count() == 0
    response = api.put(
        url,
        {"filas": [{"inscripcion_id": enrollment.pk, "presente": True}]},
        format="json",
    )
    assert response.status_code == 204
    session.refresh_from_db()
    assert session.estado == "realizada"
    assert AsistenciaSesion.objects.get().presente


def test_plans_forms_share_curricular_validation(api, data):
    response = api.get("/api/inet/planes/form/")
    assert response.status_code == 200
    assert {row["name"] for row in response.data["fields"]} >= {
        "nombre",
        "sector",
        "horas_reloj",
    }
    response = api.post(
        "/api/inet/planes/",
        {"campos": {"nombre": " ", "sector": data["sector"].pk}},
        format="json",
    )
    assert response.status_code == 400
    assert PlanVersionCurricular.objects.count() == 1


def test_options_are_paginated_and_cfp_parent_is_not_injectable(api, data):
    response = api.get(
        "/api/inet/cursos/options/plan_estudio/", {"centro": data["center"].pk}
    )
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["value"] == str(data["plan"].pk)
    assert (
        api.get(
            "/api/inet/cursos/options/plan_estudio/", {"centro": "invalid"}
        ).status_code
        == 400
    )


def test_center_creation_preserves_identifier_and_main_location(api, data, superuser):
    from VAT.tests import _build_centro_payload

    payload = _build_centro_payload(
        superuser, data["province"], data["city"], data["locality"], codigo="060144902"
    )
    superuser.groups.add(Group.objects.get_or_create(name="CFP")[0])
    payload["referentes"] = [superuser.pk]
    response = api.post("/api/inet/centros/", {"campos": payload}, format="json")
    assert response.status_code == 201, response.data
    center = Centro.objects.get(pk=response.data["id"])
    assert center.identificadores_hist.get().valor_identificador == "060144902"
    assert center.ubicaciones.get().es_principal


def test_schedule_update_preserves_completed_sessions(api, data):
    response = api.post(
        "/api/inet/horarios/",
        {
            "campos": {
                "comision": data["commission"].pk,
                "dia_semana": data["day"].pk,
                "hora_desde": "09:00",
                "hora_hasta": "12:00",
                "vigente": True,
            }
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    schedule = ComisionHorario.objects.get(pk=response.data["id"])
    completed = schedule.sesiones.first()
    completed.estado = "realizada"
    completed.save()
    response = api.put(
        f"/api/inet/horarios/{schedule.pk}/",
        {
            "campos": {
                "dia_semana": data["day"].pk,
                "hora_desde": "10:00",
                "hora_hasta": "13:00",
                "vigente": True,
            }
        },
        format="json",
    )
    assert response.status_code == 200, response.data
    assert SesionComision.objects.filter(pk=completed.pk, estado="realizada").exists()
    assert api.delete(f"/api/inet/horarios/{schedule.pk}/").status_code == 400
    assert SesionComision.objects.filter(pk=completed.pk).exists()


def test_delete_preview_and_course_soft_delete(api, data):
    url = f'/api/inet/cursos/{data["course"].pk}/'
    response = api.get(url + "delete-preview/")
    assert response.status_code == 200
    assert response.data["total_afectados"] >= 2
    assert api.delete(url).status_code == 204
    assert not Curso.objects.filter(pk=data["course"].pk).exists()
    assert Curso.all_objects.filter(pk=data["course"].pk).exists()


def test_curricular_plan_create_edit_and_delete_preserve_legacy_rules(
    api, data, superuser
):
    from users.models import Profile

    Profile.objects.update_or_create(
        user=superuser,
        defaults={"es_usuario_provincial": True, "provincia": data["province"]},
    )
    values = {
        "nombre": "Plan industrial inicial",
        "sector": data["sector"].pk,
        "modalidad_cursada": data["mode"].pk,
        "normativa_tipo": "Resolución",
        "normativa_numero": "123",
        "normativa_anio": "2026",
        "horas_reloj": 120,
        "nivel_requerido": "sin_requisito",
        "nivel_certifica": "nivel_1",
        "activo": True,
    }
    response = api.post("/api/inet/planes/", {"campos": values}, format="json")
    assert response.status_code == 201, response.data
    plan = PlanVersionCurricular.objects.get(pk=response.data["id"])
    assert plan.provincia_id == data["province"].pk
    assert plan.normativa == "Resolución 123/2026"
    assert plan.titulo_referencia.nombre == values["nombre"]
    values["nombre"] = "Plan industrial actualizado"
    response = api.put(
        f"/api/inet/planes/{plan.pk}/", {"campos": values}, format="json"
    )
    assert response.status_code == 200, response.data
    plan.refresh_from_db()
    assert plan.nombre == values["nombre"]
    assert plan.provincia_id == data["province"].pk
    assert api.delete(f"/api/inet/planes/{plan.pk}/").status_code == 204
    assert api.get(f"/api/inet/planes/{plan.pk}/").status_code == 404


def test_optional_form_values_accept_null():
    from VAT.api_inet_serializers import InetFormInputSerializer

    serializer = InetFormInputSerializer(
        data={"campos": {"sitio_web": None, "referentes": []}}
    )
    assert serializer.is_valid(), serializer.errors


def test_model_multiple_choices_are_serialized_as_multiselect():
    from django import forms
    from django.contrib.auth import get_user_model
    from VAT.services.inet_forms import serialize_form

    class ReferenceForm(forms.Form):
        referentes = forms.ModelMultipleChoiceField(
            queryset=get_user_model().objects.none(), required=False
        )

    field = serialize_form(ReferenceForm())["fields"][0]
    assert field["kind"] == "multiselect"
    assert field["value"] == []


def test_commission_edit_preserves_historical_times_and_attendance(
    api, data, superuser
):
    from VAT.services.sesion_comision_service.impl import SesionComisionService

    commission = data["commission"]
    old = ComisionHorario.objects.create(
        comision_curso=commission,
        dia_semana=data["day"],
        hora_desde="09:00",
        hora_hasta="12:00",
        vigente=True,
    )
    SesionComisionService.generar_para_horario(old)
    completed = old.sesiones.order_by("fecha").first()
    completed.estado = "realizada"
    completed.save()
    citizen = Ciudadano.objects.create(
        nombre="Prueba",
        apellido="Historial",
        documento=99001122,
        fecha_nacimiento=date(1990, 1, 1),
    )
    enrollment = Inscripcion.objects.create(
        ciudadano=citizen, comision_curso=commission, estado="inscripta"
    )
    attendance = AsistenciaSesion.objects.create(
        sesion=completed,
        inscripcion=enrollment,
        presente=True,
        registrado_por=superuser,
    )
    url = f"/api/inet/comisiones/{commission.pk}/"
    fields = {
        field["name"]: field["value"] for field in api.get(url + "form/").data["fields"]
    }
    fields["cupo_total"] = 3
    rows = [
        {
            "dia_semana": data["day"].pk,
            "hora_desde": "10:00",
            "hora_hasta": "13:00",
            "vigente": "1",
        }
    ]
    result = api.put(url, {"campos": fields, "horarios": rows}, format="json")
    assert result.status_code == 200, result.data
    old.refresh_from_db()
    assert not old.vigente
    assert str(old.hora_desde) == "09:00:00"
    assert AsistenciaSesion.objects.get(pk=attendance.pk).presente
    assert SesionComision.objects.get(pk=completed.pk).horario_id == old.pk
    assert commission.sesiones.filter(fecha=completed.fecha).count() == 1
    assert commission.horarios.filter(vigente=True).count() == 1
    active_id = commission.horarios.get(vigente=True).pk
    assert (
        api.put(url, {"campos": fields, "horarios": rows}, format="json").status_code
        == 200
    )
    assert commission.horarios.get(vigente=True).pk == active_id
    fields["cupo_total"] = 4
    rows[0]["hora_hasta"] = "10:10"
    assert (
        api.put(url, {"campos": fields, "horarios": rows}, format="json").status_code
        == 400
    )
    commission.refresh_from_db()
    assert commission.cupo_total == 3
    assert commission.horarios.get(vigente=True).pk == active_id


def test_commission_schedule_edit_requires_schedule_permissions(user, data):
    role, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Group),
        codename="role_centroreferentevat",
        defaults={"name": "Referente"},
    )
    user.user_permissions.add(role)
    grant(user, "view_comisioncurso", "change_comisioncurso")
    data["center"].referentes.add(user)
    client = APIClient()
    client.force_login(user)
    url = f'/api/inet/comisiones/{data["commission"].pk}/'
    fields = {
        field["name"]: field["value"]
        for field in client.get(url + "form/").data["fields"]
    }
    fields["cupo_total"] = 5
    result = client.put(
        url,
        {
            "campos": fields,
            "horarios": [
                {
                    "dia_semana": data["day"].pk,
                    "hora_desde": "09:00",
                    "hora_hasta": "12:00",
                    "vigente": "1",
                }
            ],
        },
        format="json",
    )
    assert result.status_code == 403
    data["commission"].refresh_from_db()
    assert data["commission"].cupo_total == 2
    assert not data["commission"].horarios.exists()
