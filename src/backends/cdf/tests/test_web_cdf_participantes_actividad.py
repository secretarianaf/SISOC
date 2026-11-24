"""Web API (G1 v1) of the CDF activity page and its participant circuit (CDF-C).

The endpoints run the native views (``ActividadCentroDetailView`` and the
``ParticipanteActividad*`` views); the tests pin the persisted effects, the
native messages verbatim, that a rejected or denied request leaves the data
unchanged and that the access chain stays exactly the current one (login and
``view_centro``; nothing else is added).
"""

from datetime import timedelta

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.utils import timezone

from centrodefamilia.models import (
    Actividad,
    ActividadCentro,
    Categoria,
    Centro,
    ParticipanteActividad,
    ParticipanteActividadHistorial,
)
from ciudadanos.models import Ciudadano
from core.models import Dia, Provincia, Sexo

pytestmark = pytest.mark.django_db

BAJA = "Participante dado de baja correctamente."


def _actor(username, *, view=True):
    user = User.objects.create_user(username)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    if view:
        user.user_permissions.add(
            Permission.objects.get(
                content_type=ContentType.objects.get_for_model(Centro),
                codename="view_centro",
            )
        )
    return User.objects.get(pk=user.pk)


def _client(user, csrf=False):
    client = Client(enforce_csrf_checks=csrf)
    client.force_login(user)
    return client


@pytest.fixture(name="actor")
def actor_fixture():
    return _actor("cdf_participantes")


@pytest.fixture(name="mujer")
def mujer_fixture():
    return Sexo.objects.create(sexo="Mujer")


@pytest.fixture(name="varon")
def varon_fixture():
    return Sexo.objects.create(sexo="Varon")


@pytest.fixture(name="actividad")
def actividad_fixture(actor, mujer):
    provincia = Provincia.objects.create(nombre="Provincia Participantes")
    centro = Centro.objects.create(
        nombre="CDF Participantes",
        tipo="faro",
        codigo="CDFPART",
        provincia=provincia,
        domicilio_actividad="Domicilio",
        telefono="011",
        celular="15",
        correo="c@example.com",
        nombre_referente="Lia",
        apellido_referente="Paz",
        telefono_referente="012",
        correo_referente="lia@example.com",
        referente=actor,
    )
    categoria = Categoria.objects.create(nombre="Deportes")
    base = Actividad.objects.create(nombre="Futbol", categoria=categoria)
    actividad = ActividadCentro.objects.create(
        centro=centro,
        actividad=base,
        cantidad_personas=2,
        horariosdesde="09:00",
        horarioshasta="10:30",
        precio=1500,
        estado="en_curso",
    )
    actividad.sexoact.add(mujer)
    actividad.dias.add(Dia.objects.create(nombre="Lunes"))
    return actividad


def _ciudadano(documento, sexo, nombre="Ana", apellido="Paz"):
    return Ciudadano.objects.create(
        nombre=nombre, apellido=apellido, documento=documento, sexo=sexo
    )


def _inscribir(actividad, ciudadano, estado="inscrito", dias_atras=0):
    participante = ParticipanteActividad.objects.create(
        actividad_centro=actividad, ciudadano=ciudadano, estado=estado
    )
    ParticipanteActividad.objects.filter(pk=participante.pk).update(
        fecha_registro=timezone.now() - timedelta(days=dias_atras)
    )
    return participante


def _detail(actividad):
    return f"/api/web/cdf/actividades/{actividad.pk}/"


def _crear(actividad):
    return (
        f"/api/web/cdf/centros/{actividad.centro_id}/actividades/{actividad.pk}"
        "/participantes/"
    )


def _eliminar(actividad, participante):
    return f"{_crear(actividad)}{participante.pk}/eliminar/"


def _promover(actividad, participante):
    return (
        f"/api/web/cdf/centros/{actividad.centro_id}/actividades/{actividad.pk}"
        f"/lista-espera/{participante.pk}/promover/"
    )


def _estados(actividad):
    return sorted(
        ParticipanteActividad.objects.filter(actividad_centro=actividad).values_list(
            "estado", flat=True
        )
    )


def _historial():
    return ParticipanteActividadHistorial.objects.count()


# --- Detail -------------------------------------------------------------------


def test_detail_projects_the_native_context(actor, actividad, mujer):
    ana = _inscribir(actividad, _ciudadano(30111222, mujer, "Ana", "Paz"))
    espera = _inscribir(
        actividad, _ciudadano(30111223, mujer, "Eva", "Gil"), "lista_espera"
    )
    _inscribir(actividad, _ciudadano(30111224, mujer, "Baja", "Dada"), "dado_baja")

    respuesta = _client(actor).get(_detail(actividad))

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    assert data["actividad"]["nombre"] == "Futbol"
    assert data["actividad"]["categoria"] == "Deportes"
    assert data["actividad"]["estado_display"] == "En curso"
    assert data["actividad"]["horariosdesde"] == "09:00"
    assert data["actividad"]["horarioshasta"] == "10:30"
    assert data["actividad"]["sexos"] == ["Mujer"]
    assert data["actividad"]["dias"] == ["Lunes"]
    assert data["centro"] == {"id": actividad.centro_id, "nombre": "CDF Participantes"}
    assert [p["id"] for p in data["participantes"]] == [ana.pk]
    assert data["participantes"][0]["sexo"] == "Mujer"
    assert data["participantes"][0]["fecha_registro"] == timezone.localdate().strftime(
        "%d/%m/%Y"
    )
    assert data["participantes"][0]["urls"]["delete"] == (
        f"/centrodefamilia/centros/{actividad.centro_id}/actividades/{actividad.pk}"
        f"/participantes/{ana.pk}/eliminar/"
    )
    assert [p["id"] for p in data["lista_espera"]] == [espera.pk]
    assert data["lista_espera"][0]["urls"]["promover"].endswith(
        f"/lista-espera/{espera.pk}/promover/"
    )
    assert data["promo_error"] is False
    assert data["puede_tomar_asistencia"] is True
    assert data["urls"]["asistencia"] == (
        f"/centrodefamilia/centros/actividades/{actividad.pk}/asistencia/"
    )


def test_detail_total_cost_is_the_price_times_the_enrolled(actor, actividad, mujer):
    _inscribir(actividad, _ciudadano(30111222, mujer, "Ana"))
    _inscribir(actividad, _ciudadano(30111223, mujer, "Eva"))
    _inscribir(actividad, _ciudadano(30111224, mujer, "Lis"), "lista_espera")

    data = _client(actor).get(_detail(actividad)).json()

    assert data["actividad"]["precio_total"] == "3000"


def test_detail_flags_promo_error_and_hides_attendance_from_others(actividad):
    otro = _actor("cdf_otro")

    data = _client(otro).get(_detail(actividad) + "?promo_error=1").json()

    assert data["promo_error"] is True
    assert data["puede_tomar_asistencia"] is False


def test_detail_access_chain_is_login_then_view_centro_then_object(actividad):
    sin_permiso = _actor("cdf_sin_permiso", view=False)

    assert Client().get(_detail(actividad)).status_code == 401
    assert _client(sin_permiso).get(_detail(actividad)).status_code == 403
    assert (
        _client(_actor("cdf_ok")).get("/api/web/cdf/actividades/999999/").status_code
        == 404
    )


# --- Search and form ----------------------------------------------------------


def test_create_get_searches_by_document_with_the_native_threshold(
    actor, actividad, mujer
):
    _ciudadano(30111222, mujer)
    client = _client(actor)

    corta = client.get(_crear(actividad) + "?query=301112").json()
    larga = client.get(_crear(actividad) + "?query=3011122").json()
    sin_query = client.get(_crear(actividad)).json()

    assert corta["ciudadanos"] == [] and corta["no_resultados"] is True
    assert [c["documento"] for c in larga["ciudadanos"]] == ["30111222"]
    assert larga["no_resultados"] is False and larga["query"] == "3011122"
    assert sin_query["query"] == "" and sin_query["no_resultados"] is True
    campos = {f["name"]: f for f in larga["fields"]}
    assert list(campos) == [
        "nombre",
        "apellido",
        "fecha_nacimiento",
        "tipo_documento",
        "dni",
        "genero",
    ]
    assert campos["fecha_nacimiento"]["widget"] == "date"
    assert campos["tipo_documento"]["choices"][0]["label"] == "DNI"
    assert campos["genero"]["choices"][0]["value"] == ""


def test_create_access_chain_is_unchanged(actividad):
    sin_permiso = _actor("cdf_sin_permiso", view=False)

    assert Client().get(_crear(actividad)).status_code == 401
    assert _client(sin_permiso).get(_crear(actividad)).status_code == 403
    assert (
        _client(sin_permiso).post(_crear(actividad), {"ciudadano_id": "1"}).status_code
        == 403
    )
    assert _estados(actividad) == []


# --- Enrol --------------------------------------------------------------------


def test_post_existing_citizen_enrols_and_keeps_the_message_queued(
    actor, actividad, mujer
):
    ciudadano = _ciudadano(30111222, mujer)
    client = _client(actor)

    respuesta = client.post(_crear(actividad), {"ciudadano_id": ciudadano.pk})

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "url": f"/centrodefamilia/centros/actividades/{actividad.pk}/detalle/",
        "message": "Participante agregado correctamente.",
        "level": "success",
    }
    participante = ParticipanteActividad.objects.get()
    assert (participante.ciudadano_id, participante.estado) == (
        ciudadano.pk,
        "inscrito",
    )
    historial = ParticipanteActividadHistorial.objects.get()
    assert (historial.estado_anterior, historial.estado_nuevo, historial.usuario) == (
        None,
        "inscrito",
        actor,
    )
    siguiente = client.get(_detail(actividad)).json()["messages"]
    assert siguiente == [
        {"message": "Participante agregado correctamente.", "level": "success"}
    ]
    assert client.get(_detail(actividad)).json()["messages"] == []


def test_post_full_activity_goes_to_the_waitlist(actor, actividad, mujer):
    _inscribir(actividad, _ciudadano(30111220, mujer, "Uno"))
    _inscribir(actividad, _ciudadano(30111221, mujer, "Dos"))
    tercero = _ciudadano(30111222, mujer, "Tres")

    respuesta = _client(actor).post(_crear(actividad), {"ciudadano_id": tercero.pk})

    assert respuesta.json()["message"] == (
        "Cupo completo: participante agregado a lista de espera."
    )
    assert _estados(actividad) == ["inscrito", "inscrito", "lista_espera"]


def test_post_allow_waitlist_flag_adds_to_the_waitlist(actor, actividad, mujer):
    _inscribir(actividad, _ciudadano(30111220, mujer, "Uno"))
    _inscribir(actividad, _ciudadano(30111221, mujer, "Dos"))
    tercero = _ciudadano(30111222, mujer, "Tres")

    respuesta = _client(actor).post(
        _crear(actividad), {"ciudadano_id": tercero.pk, "allow_waitlist": "1"}
    )

    assert respuesta.json()["message"] == "Participante agregado a la lista de espera."
    assert _estados(actividad) == ["inscrito", "inscrito", "lista_espera"]


@pytest.mark.parametrize(
    ("caso", "mensaje", "nivel"),
    [
        ("repetido", "Ya está inscrito o en lista de espera.", "warning"),
        ("sexo", "Sexo no permitido para esta actividad.", "warning"),
        ("inexistente", "Ciudadano no encontrado.", "error"),
    ],
)
def test_post_rejections_change_nothing(
    actor, actividad, mujer, varon, caso, mensaje, nivel
):
    if caso == "repetido":
        ciudadano = _ciudadano(30111222, mujer)
        _inscribir(actividad, ciudadano)
        ciudadano_id = ciudadano.pk
    elif caso == "sexo":
        ciudadano_id = _ciudadano(30111222, varon).pk
    else:
        ciudadano_id = 987654
    antes = (_estados(actividad), _historial())

    respuesta = _client(actor).post(_crear(actividad), {"ciudadano_id": ciudadano_id})

    assert respuesta.status_code == 200
    assert respuesta.json()["message"] == mensaje
    assert respuesta.json()["level"] == nivel
    assert (_estados(actividad), _historial()) == antes


def test_post_missing_activity_keeps_the_native_error_and_creates_nothing(actor, mujer):
    ciudadano = _ciudadano(30111222, mujer)

    respuesta = _client(actor).post(
        "/api/web/cdf/centros/1/actividades/999999/participantes/",
        {"ciudadano_id": ciudadano.pk},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["message"] == "Actividad no encontrada."
    assert respuesta.json()["level"] == "error"
    assert ParticipanteActividad.objects.count() == 0


DATOS = {
    "nombre": "Nuevo",
    "apellido": "Ciudadano",
    "fecha_nacimiento": "1990-05-04",
    "tipo_documento": "DNI",
    "dni": "40111222",
}


def test_post_new_citizen_creates_it_and_enrols(actor, actividad, mujer):
    respuesta = _client(actor).post(_crear(actividad), {**DATOS, "genero": mujer.pk})

    assert respuesta.status_code == 200
    assert respuesta.json()["message"] == "Participante agregado correctamente."
    ciudadano = Ciudadano.objects.get(documento=40111222)
    assert (ciudadano.nombre, ciudadano.apellido, ciudadano.sexo) == (
        "Nuevo",
        "Ciudadano",
        mujer,
    )
    assert ParticipanteActividad.objects.get().ciudadano == ciudadano


def test_post_invalid_form_answers_400_with_errors_and_creates_nothing(
    actor, actividad
):
    respuesta = _client(actor).post(_crear(actividad), {"nombre": "Solo"})

    assert respuesta.status_code == 400
    data = respuesta.json()
    assert set(data["errors"]) == {
        "apellido",
        "fecha_nacimiento",
        "tipo_documento",
        "dni",
        "genero",
    }
    assert data["errors"]["apellido"][0]["message"] == "Este campo es requerido."
    assert {f["name"]: f["value"] for f in data["fields"]}["nombre"] == "Solo"
    assert Ciudadano.objects.count() == 0 and _historial() == 0


def test_post_invalid_form_keeps_the_search_of_the_page_url(actor, actividad):
    respuesta = _client(actor).post(
        _crear(actividad) + "?query=9999999", {"nombre": "Solo"}
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["query"] == "9999999"
    assert respuesta.json()["no_resultados"] is True


def test_post_duplicate_document_is_a_form_error_not_a_second_enrolment(
    actor, actividad, mujer
):
    _inscribir(actividad, _ciudadano(40111222, mujer))

    respuesta = _client(actor).post(_crear(actividad), {**DATOS, "genero": mujer.pk})

    assert respuesta.status_code == 400
    assert respuesta.json()["non_field_errors"] == [
        "El ciudadano ya está inscrito o en lista de espera."
    ]
    assert ParticipanteActividad.objects.count() == 1


def test_post_new_citizen_with_a_sex_the_activity_excludes_is_rejected(
    actor, actividad, varon
):
    respuesta = _client(actor).post(_crear(actividad), {**DATOS, "genero": varon.pk})

    assert respuesta.status_code == 200
    assert respuesta.json()["message"] == "Sexo no permitido para esta actividad."
    assert Ciudadano.objects.count() == 0


def test_posts_require_csrf(actor, actividad, mujer):
    participante = _inscribir(actividad, _ciudadano(30111222, mujer))
    client = _client(actor, csrf=True)

    assert client.post(_crear(actividad), {"ciudadano_id": "1"}).status_code == 403
    assert client.post(_eliminar(actividad, participante)).status_code == 403
    assert client.post(_promover(actividad, participante)).status_code == 403
    assert _estados(actividad) == ["inscrito"] and _historial() == 0


# --- Baja ---------------------------------------------------------------------


def test_delete_get_shows_the_participant_and_changes_nothing(actor, actividad, mujer):
    participante = _inscribir(actividad, _ciudadano(30111222, mujer, "Ana", "Paz"))

    respuesta = _client(actor).get(_eliminar(actividad, participante))

    assert respuesta.status_code == 200
    assert respuesta.json()["participante"] == {
        "id": participante.pk,
        "apellido": "Paz",
        "nombre": "Ana",
        "documento": "30111222",
    }
    assert respuesta.json()["urls"]["detail"].endswith(f"/{actividad.pk}/detalle/")
    assert _estados(actividad) == ["inscrito"]
    assert _client(actor).get(f"{_crear(actividad)}999999/eliminar/").status_code == 404


def test_delete_post_records_history_and_promotes_the_first_in_the_waitlist(
    actor, actividad, mujer
):
    baja = _inscribir(actividad, _ciudadano(30111220, mujer, "Uno"))
    _inscribir(actividad, _ciudadano(30111221, mujer, "Dos"))
    tarde = _inscribir(
        actividad, _ciudadano(30111222, mujer, "Tarde"), "lista_espera", dias_atras=1
    )
    primero = _inscribir(
        actividad, _ciudadano(30111223, mujer, "Primero"), "lista_espera", dias_atras=5
    )

    respuesta = _client(actor).post(_eliminar(actividad, baja))

    assert respuesta.status_code == 200
    assert respuesta.json()["message"] == BAJA
    esperados = (
        (baja.pk, "dado_baja"),
        (primero.pk, "inscrito"),
        (tarde.pk, "lista_espera"),
    )
    for pk, estado in esperados:
        assert ParticipanteActividad.objects.get(pk=pk).estado == estado
    historial = list(
        ParticipanteActividadHistorial.objects.order_by("pk").values_list(
            "participante_id", "estado_anterior", "estado_nuevo", "usuario"
        )
    )
    assert historial == [
        (baja.pk, "inscrito", "dado_baja", actor.pk),
        (primero.pk, "lista_espera", "inscrito", actor.pk),
    ]


def test_delete_post_twice_adds_no_history_or_promotion(actor, actividad, mujer):
    baja = _inscribir(actividad, _ciudadano(30111220, mujer, "Uno"))
    client = _client(actor)
    client.post(_eliminar(actividad, baja))
    espera = _inscribir(
        actividad, _ciudadano(30111223, mujer, "Espera"), "lista_espera"
    )
    antes = _historial()

    client.post(_eliminar(actividad, baja))

    assert _historial() == antes
    assert ParticipanteActividad.objects.get(pk=espera.pk).estado == "lista_espera"


def test_delete_post_of_a_missing_participant_is_404_without_effects(actor, actividad):
    assert (
        _client(actor).post(f"{_crear(actividad)}999999/eliminar/").status_code == 404
    )
    assert _historial() == 0


def test_delete_denied_without_permission_changes_nothing(actividad, mujer):
    participante = _inscribir(actividad, _ciudadano(30111222, mujer))

    respuesta = _client(_actor("cdf_sin_permiso", view=False)).post(
        _eliminar(actividad, participante)
    )

    assert respuesta.status_code == 403
    assert _estados(actividad) == ["inscrito"] and _historial() == 0


# --- Promotion ----------------------------------------------------------------


def test_promover_takes_the_first_by_registration_not_the_url_row(
    actor, actividad, mujer
):
    _inscribir(actividad, _ciudadano(30111220, mujer, "Uno"))
    de_url = _inscribir(
        actividad, _ciudadano(30111222, mujer, "Url"), "lista_espera", dias_atras=1
    )
    primero = _inscribir(
        actividad, _ciudadano(30111223, mujer, "Primero"), "lista_espera", dias_atras=9
    )

    respuesta = _client(actor).post(_promover(actividad, de_url))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "url": f"/centrodefamilia/centros/actividades/{actividad.pk}/detalle/",
        "message": "Participante promovido a inscrito correctamente.",
        "level": "success",
        "promo_error": False,
    }
    assert ParticipanteActividad.objects.get(pk=primero.pk).estado == "inscrito"
    assert ParticipanteActividad.objects.get(pk=de_url.pk).estado == "lista_espera"
    historial = ParticipanteActividadHistorial.objects.get()
    assert (historial.participante_id, historial.estado_nuevo) == (
        primero.pk,
        "inscrito",
    )


def test_promover_without_room_flags_promo_error_and_changes_nothing(
    actor, actividad, mujer
):
    _inscribir(actividad, _ciudadano(30111220, mujer, "Uno"))
    _inscribir(actividad, _ciudadano(30111221, mujer, "Dos"))
    espera = _inscribir(
        actividad, _ciudadano(30111222, mujer, "Espera"), "lista_espera"
    )

    respuesta = _client(actor).post(_promover(actividad, espera))

    assert respuesta.status_code == 200
    assert respuesta.json()["promo_error"] is True
    assert respuesta.json()["url"].endswith("/detalle/?promo_error=1")
    assert respuesta.json()["message"] == ""
    assert _estados(actividad) == ["inscrito", "inscrito", "lista_espera"]
    assert _historial() == 0


def test_promover_without_a_waitlist_reports_it(actor, actividad, mujer):
    inscrito = _inscribir(actividad, _ciudadano(30111220, mujer, "Uno"))

    respuesta = _client(actor).post(_promover(actividad, inscrito))

    assert respuesta.json()["message"] == "No hay participantes en lista de espera."
    assert respuesta.json()["level"] == "info"
    assert _estados(actividad) == ["inscrito"] and _historial() == 0


def test_promover_is_post_only_and_denied_without_permission(actividad, mujer):
    espera = _inscribir(actividad, _ciudadano(30111222, mujer), "lista_espera")
    sin_permiso = _client(_actor("cdf_sin_permiso", view=False))

    assert (
        _client(_actor("cdf_ok")).get(_promover(actividad, espera)).status_code == 405
    )
    assert sin_permiso.post(_promover(actividad, espera)).status_code == 403
    assert Client().post(_promover(actividad, espera)).status_code in (401, 403)
    assert _estados(actividad) == ["lista_espera"] and _historial() == 0
