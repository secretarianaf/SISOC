"""Web API (G1 v1) of the CDF attendance sheet (CDF-D).

The endpoint runs ``AsistenciaActividadView``; the tests pin the native check
order (``view_centro`` 403, missing activity 404, attendance permission 403),
the sheet (only the enrolled, apellido/nombre order, None/True/False), the
persisted effects of the save (unmarked becomes absent, ``update_or_create``
per participant and date) and the native texts verbatim.
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
    AsistenciaActividad,
    Categoria,
    Centro,
    ParticipanteActividad,
)
from ciudadanos.models import Ciudadano
from core.models import Provincia, Sexo

pytestmark = pytest.mark.django_db


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
    return _actor("cdf_asistencia")


@pytest.fixture(name="actividad")
def actividad_fixture(actor):
    centro = Centro.objects.create(
        nombre="CDF Asistencia",
        tipo="faro",
        codigo="CDFASIS",
        provincia=Provincia.objects.create(nombre="Provincia Asistencia"),
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
    base = Actividad.objects.create(
        nombre="Futbol", categoria=Categoria.objects.create(nombre="Deportes")
    )
    return ActividadCentro.objects.create(
        centro=centro,
        actividad=base,
        cantidad_personas=10,
        horariosdesde="09:00",
        horarioshasta="10:30",
        estado="en_curso",
    )


def _participante(actividad, documento, nombre, apellido, estado="inscrito"):
    ciudadano = Ciudadano.objects.create(
        nombre=nombre,
        apellido=apellido,
        documento=documento,
        sexo=Sexo.objects.get_or_create(sexo="Mujer")[0],
    )
    return ParticipanteActividad.objects.create(
        actividad_centro=actividad, ciudadano=ciudadano, estado=estado
    )


def _url(actividad):
    return f"/api/web/cdf/actividades/{actividad.pk}/asistencia/"


def _marcas(fecha=None):
    return AsistenciaActividad.objects.filter(fecha=fecha or timezone.localdate())


# --- Access chain -------------------------------------------------------------


def test_access_chain_is_login_view_centro_object_then_attendance_permission(
    actor, actividad
):
    sin_permiso = _actor("cdf_sin_permiso", view=False)
    sin_asistencia = _actor("cdf_sin_asistencia")
    _participante(actividad, 30111220, "Ana", "Paz")

    assert Client().get(_url(actividad)).status_code == 401
    assert _client(sin_permiso).get(_url(actividad)).status_code == 403
    assert (
        _client(actor).get("/api/web/cdf/actividades/999999/asistencia/").status_code
        == 404
    )
    assert _client(sin_asistencia).get(_url(actividad)).status_code == 403
    assert _client(actor).get(_url(actividad)).status_code == 200


def test_denied_posts_save_nothing(actividad):
    participante = _participante(actividad, 30111220, "Ana", "Paz")
    datos = {
        "fecha": timezone.localdate().isoformat(),
        f"presente_{participante.pk}": "1",
    }

    assert (
        _client(_actor("sin_asistencia")).post(_url(actividad), datos).status_code
        == 403
    )
    assert (
        _client(_actor("sin_permiso", view=False))
        .post(_url(actividad), datos)
        .status_code
        == 403
    )
    assert Client().post(_url(actividad), datos).status_code in (401, 403)
    assert AsistenciaActividad.objects.count() == 0


def test_post_requires_csrf(actor, actividad):
    participante = _participante(actividad, 30111220, "Ana", "Paz")

    respuesta = _client(actor, csrf=True).post(
        _url(actividad), {f"presente_{participante.pk}": "1"}
    )

    assert respuesta.status_code == 403
    assert AsistenciaActividad.objects.count() == 0


# --- Sheet --------------------------------------------------------------------


def test_get_lists_only_the_enrolled_ordered_with_their_marks(actor, actividad):
    zeta = _participante(actividad, 30111221, "Zoe", "Zeta")
    alfa = _participante(actividad, 30111222, "Ana", "Alfa")
    sin_marca = _participante(actividad, 30111223, "Beto", "Beta")
    espera = _participante(actividad, 30111224, "Lis", "Espera", "lista_espera")
    baja = _participante(actividad, 30111225, "Bea", "Baja", "dado_baja")
    hoy = timezone.localdate()
    AsistenciaActividad.objects.create(
        participante=alfa, fecha=hoy, presente=True, registrado_por=actor
    )
    AsistenciaActividad.objects.create(
        participante=zeta, fecha=hoy, presente=False, registrado_por=actor
    )
    AsistenciaActividad.objects.create(
        participante=espera, fecha=hoy, presente=True, registrado_por=actor
    )
    AsistenciaActividad.objects.create(
        participante=baja, fecha=hoy, presente=True, registrado_por=actor
    )

    respuesta = _client(actor).get(_url(actividad))

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    assert data["fecha"] == hoy.strftime("%Y-%m-%d")
    assert data["fecha_display"] == hoy.strftime("%d/%m/%Y")
    assert data["fecha_error"] is None and data["ya_tomada"] is True
    assert [(f["id"], f["presente"]) for f in data["filas"]] == [
        (alfa.pk, True),
        (sin_marca.pk, None),
        (zeta.pk, False),
    ]
    assert data["totales"] == {"presentes": 1, "ausentes": 1, "sin_marcar": 1}
    assert data["actividad"]["nombre"] == "Futbol"
    assert data["urls"]["detalle"] == (
        f"/centrodefamilia/centros/actividades/{actividad.pk}/detalle/"
    )


def test_get_without_enrolled_has_no_rows_and_a_fresh_sheet(actor, actividad):
    data = _client(actor).get(_url(actividad)).json()

    assert data["filas"] == [] and data["ya_tomada"] is False
    assert data["totales"] == {"presentes": 0, "ausentes": 0, "sin_marcar": 0}


def test_get_past_date_is_kept_and_invalid_or_future_fall_back_to_today(
    actor, actividad
):
    client = _client(actor)
    hoy = timezone.localdate()
    pasada = (hoy - timedelta(days=3)).isoformat()
    futura = (hoy + timedelta(days=2)).isoformat()

    assert client.get(_url(actividad) + f"?fecha={pasada}").json()["fecha"] == pasada
    for raw, error in (
        ("no-es-fecha", "La fecha indicada no es válida."),
        (futura, "No se puede tomar asistencia para una fecha futura."),
    ):
        data = client.get(_url(actividad) + f"?fecha={raw}").json()
        assert data["fecha"] == hoy.isoformat()
        assert data["fecha_error"] == error


# --- Save ---------------------------------------------------------------------


def test_post_saves_the_marks_and_turns_the_unmarked_into_absent(actor, actividad):
    presente = _participante(actividad, 30111220, "Ana", "Alfa")
    ausente = _participante(actividad, 30111221, "Beto", "Beta")
    sin_marca = _participante(actividad, 30111222, "Cami", "Gama")
    espera = _participante(actividad, 30111223, "Lis", "Espera", "lista_espera")
    fecha = (timezone.localdate() - timedelta(days=1)).isoformat()
    client = _client(actor)

    respuesta = client.post(
        _url(actividad),
        {
            "fecha": fecha,
            f"presente_{presente.pk}": "1",
            f"presente_{ausente.pk}": "0",
            f"presente_{espera.pk}": "1",
        },
    )

    assert respuesta.status_code == 200
    dia = fecha[8:10] + "/" + fecha[5:7] + "/" + fecha[:4]
    assert respuesta.json() == {
        "url": f"/centrodefamilia/centros/actividades/{actividad.pk}/asistencia/?fecha={fecha}",
        "message": f"Asistencia del {dia} registrada para 3 participante(s).",
        "level": "success",
    }
    marcas = {
        a.participante_id: (a.presente, a.registrado_por_id)
        for a in AsistenciaActividad.objects.all()
    }
    assert marcas == {
        presente.pk: (True, actor.pk),
        ausente.pk: (False, actor.pk),
        sin_marca.pk: (False, actor.pk),
    }
    assert client.get(_url(actividad) + f"?fecha={fecha}").json()["messages"] == [
        {
            "message": f"Asistencia del {dia} registrada para 3 participante(s).",
            "level": "success",
        }
    ]


def test_post_twice_updates_the_mark_and_the_author_without_duplicating(
    actor, actividad
):
    participante = _participante(actividad, 30111220, "Ana", "Alfa")
    otro = _actor("cdf_otro_asistencia")
    fecha = timezone.localdate().isoformat()

    _client(actor).post(_url(actividad), {"fecha": fecha})
    assert _marcas().get().presente is False
    actividad.centro.referente = otro
    actividad.centro.save()
    _client(otro).post(
        _url(actividad), {"fecha": fecha, f"presente_{participante.pk}": "1"}
    )

    marca = _marcas().get()
    assert (marca.presente, marca.registrado_por) == (True, otro)
    assert AsistenciaActividad.objects.count() == 1


def test_post_defaults_to_today_when_the_date_is_missing(actor, actividad):
    _participante(actividad, 30111220, "Ana", "Alfa")

    respuesta = _client(actor).post(_url(actividad), {})

    assert respuesta.json()["url"].endswith(f"?fecha={timezone.localdate():%Y-%m-%d}")
    assert _marcas().count() == 1


@pytest.mark.parametrize(
    ("dias", "raw", "mensaje"),
    [
        (0, "31/12/2026", "La fecha indicada no es válida."),
        (2, None, "No se puede tomar asistencia para una fecha futura."),
    ],
)
def test_post_with_an_invalid_date_saves_nothing_and_returns_to_the_sheet(
    actor, actividad, dias, raw, mensaje
):
    participante = _participante(actividad, 30111220, "Ana", "Alfa")
    fecha = raw or (timezone.localdate() + timedelta(days=dias)).isoformat()

    respuesta = _client(actor).post(
        _url(actividad), {"fecha": fecha, f"presente_{participante.pk}": "1"}
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "url": f"/centrodefamilia/centros/actividades/{actividad.pk}/asistencia/",
        "message": mensaje,
        "level": "error",
    }
    assert AsistenciaActividad.objects.count() == 0
