"""Web API (G1 v1) of the CDF centre activity create and edit form (CDF-B).

The endpoints run ``ActividadCentroCreateView`` / ``ActividadCentroUpdateView``
(``ActividadCentroForm``); the tests pin the persisted effects, the native
messages verbatim, the unchanged data after a rejection, the dependent activity
queryset, the FARO price rule and that the access chain stays the current one
(login and ``view_centro``; nothing else is added).
"""

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client

from centrodefamilia.models import Actividad, ActividadCentro, Categoria, Centro
from core.models import Dia, Provincia, Sexo

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
    return _actor("cdf_actividad_form")


def _centro(tipo, codigo):
    return Centro.objects.create(
        nombre=f"Centro {tipo}",
        tipo=tipo,
        codigo=codigo,
        provincia=Provincia.objects.get_or_create(nombre="Provincia Form")[0],
        domicilio_actividad="Domicilio",
        telefono="011",
        celular="15",
        correo="c@example.com",
        nombre_referente="Lia",
        apellido_referente="Paz",
        telefono_referente="012",
        correo_referente="lia@example.com",
    )


@pytest.fixture(name="datos")
def datos_fixture():
    deportes = Categoria.objects.create(nombre="Deportes")
    arte = Categoria.objects.create(nombre="Arte")
    return {
        "faro": _centro("faro", "FARO1"),
        "adherido": _centro("adherido", "ADH1"),
        "deportes": deportes,
        "futbol": Actividad.objects.create(nombre="Futbol", categoria=deportes),
        "pintura": Actividad.objects.create(nombre="Pintura", categoria=arte),
        "lunes": Dia.objects.create(nombre="Lunes"),
        "martes": Dia.objects.create(nombre="Martes"),
        "mujer": Sexo.objects.create(sexo="Mujer"),
    }


def _crear(centro):
    return f"/api/web/cdf/centros/{centro.pk}/actividades/nueva/"


def _editar(actividad):
    return f"/api/web/cdf/actividades/{actividad.pk}/editar/"


def _datos(datos, **over):
    base = {
        "categoria": datos["deportes"].pk,
        "actividad": datos["futbol"].pk,
        "cantidad_personas": "12",
        "sexoact": [datos["mujer"].pk],
        "dias": [datos["lunes"].pk, datos["martes"].pk],
        "horariosdesde": "09:00",
        "horarioshasta": "10:30",
        "precio": "800",
        "estado": "en_curso",
    }
    base.update(over)
    return base


def _existente(datos, centro="adherido", **over):
    actividad = ActividadCentro.objects.create(
        centro=datos[centro],
        actividad=datos["futbol"],
        cantidad_personas=5,
        horariosdesde="08:00",
        horarioshasta="09:00",
        precio=300,
        estado="planificada",
        **over,
    )
    actividad.dias.set([datos["lunes"]])
    actividad.sexoact.set([datos["mujer"]])
    return actividad


# --- Create -------------------------------------------------------------------


def test_create_get_lists_the_native_fields_in_order(actor, datos):
    respuesta = _client(actor).get(_crear(datos["adherido"]))

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    assert data["centro"] == {
        "id": datos["adherido"].pk,
        "nombre": "Centro adherido",
        "tipo": "adherido",
    }
    campos = {f["name"]: f for f in data["fields"]}
    assert list(campos) == [
        "categoria",
        "actividad",
        "cantidad_personas",
        "sexoact",
        "dias",
        "horariosdesde",
        "horarioshasta",
        "precio",
        "estado",
    ]
    assert campos["categoria"]["choices"][0] == {
        "value": "",
        "label": "Seleccione una categoría",
    }
    assert [c["label"] for c in campos["actividad"]["choices"]] == ["---------"]
    assert campos["sexoact"]["widget"] == "selectmultiple"
    assert campos["sexoact"]["label"] == "Actividad dirigida a..."
    assert campos["dias"]["choices"][0]["label"] == "Lunes"
    assert campos["horariosdesde"]["html"]["class"] == "form-control timepicker"
    assert campos["horariosdesde"]["html"]["placeholder"] == "Seleccione una hora"
    assert campos["precio"]["widget"] == "number"
    assert [c["value"] for c in campos["estado"]["choices"]] == [
        "planificada",
        "en_curso",
        "finalizada",
    ]


def test_create_get_hides_the_price_of_a_faro_centre(actor, datos):
    data = _client(actor).get(_crear(datos["faro"])).json()

    precio = {f["name"]: f for f in data["fields"]}["precio"]
    assert precio["widget"] == "hidden" and precio["required"] is False


def test_create_post_saves_the_activity_and_keeps_the_message_queued(actor, datos):
    client = _client(actor)

    respuesta = client.post(_crear(datos["adherido"]), _datos(datos))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "url": f"/centrodefamilia/centros/{datos['adherido'].pk}/",
        "message": "La actividad fue creada correctamente.",
        "level": "success",
    }
    actividad = ActividadCentro.objects.get()
    assert (actividad.centro, actividad.actividad) == (
        datos["adherido"],
        datos["futbol"],
    )
    assert (actividad.cantidad_personas, actividad.precio, actividad.estado) == (
        12,
        800,
        "en_curso",
    )
    assert actividad.horariosdesde.strftime("%H:%M") == "09:00"
    assert actividad.horarioshasta.strftime("%H:%M") == "10:30"
    assert sorted(actividad.dias.values_list("nombre", flat=True)) == [
        "Lunes",
        "Martes",
    ]
    assert list(actividad.sexoact.all()) == [datos["mujer"]]
    siguiente = client.get(_crear(datos["adherido"])).json()["messages"]
    assert siguiente == [
        {"message": "La actividad fue creada correctamente.", "level": "success"}
    ]


def test_create_post_invalid_is_a_400_with_errors_and_creates_nothing(actor, datos):
    respuesta = _client(actor).post(
        _crear(datos["adherido"]),
        {"categoria": datos["deportes"].pk, "cantidad_personas": "-3"},
    )

    assert respuesta.status_code == 400
    errores = respuesta.json()["errors"]
    assert {"actividad", "cantidad_personas", "horariosdesde", "horarioshasta"} <= set(
        errores
    )
    assert errores["horariosdesde"][0]["message"] == "Este campo es requerido."
    valores = {f["name"]: f["value"] for f in respuesta.json()["fields"]}
    assert valores["categoria"] == str(datos["deportes"].pk)
    assert ActividadCentro.objects.count() == 0


def test_create_post_activity_must_belong_to_the_chosen_category(actor, datos):
    respuesta = _client(actor).post(
        _crear(datos["adherido"]), _datos(datos, actividad=datos["pintura"].pk)
    )

    assert respuesta.status_code == 400
    assert "actividad" in respuesta.json()["errors"]
    assert ActividadCentro.objects.count() == 0


def test_create_post_faro_rejects_a_price_but_accepts_zero(actor, datos):
    client = _client(actor)

    rechazada = client.post(_crear(datos["faro"]), _datos(datos, precio="500"))
    aceptada = client.post(_crear(datos["faro"]), _datos(datos, precio="0"))

    assert rechazada.status_code == 400
    assert rechazada.json()["non_field_errors"] == [
        "Un centro de tipo FARO no debe tener un precio asignado."
    ]
    assert aceptada.status_code == 200
    assert ActividadCentro.objects.get().precio == 0


def test_create_missing_centre_is_404_and_saves_nothing(actor, datos):
    client = _client(actor)

    assert (
        client.get("/api/web/cdf/centros/999999/actividades/nueva/").status_code == 404
    )
    assert (
        client.post(
            "/api/web/cdf/centros/999999/actividades/nueva/", _datos(datos)
        ).status_code
        == 404
    )
    assert ActividadCentro.objects.count() == 0


# --- Edit ---------------------------------------------------------------------


def test_edit_get_shows_the_current_values(actor, datos):
    actividad = _existente(datos)

    data = _client(actor).get(_editar(actividad)).json()

    campos = {f["name"]: f for f in data["fields"]}
    assert campos["categoria"]["value"] == str(datos["deportes"].pk)
    assert campos["actividad"]["value"] == str(datos["futbol"].pk)
    assert [c["label"] for c in campos["actividad"]["choices"]] == [
        "---------",
        "Futbol",
    ]
    assert campos["dias"]["value"] == [str(datos["lunes"].pk)]
    assert campos["sexoact"]["value"] == [str(datos["mujer"].pk)]
    assert campos["horariosdesde"]["value"] == "08:00:00"
    assert campos["precio"]["value"] == "300"
    assert campos["estado"]["value"] == "planificada"


def test_edit_post_updates_the_activity_and_keeps_the_message_queued(actor, datos):
    actividad = _existente(datos)
    client = _client(actor)

    respuesta = client.post(
        _editar(actividad),
        _datos(
            datos,
            cantidad_personas="20",
            estado="finalizada",
            dias=[datos["martes"].pk],
        ),
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "url": f"/centrodefamilia/centros/{datos['adherido'].pk}/",
        "message": "La actividad fue actualizada correctamente.",
        "level": "success",
    }
    actividad.refresh_from_db()
    assert (actividad.cantidad_personas, actividad.estado, actividad.precio) == (
        20,
        "finalizada",
        800,
    )
    assert list(actividad.dias.values_list("nombre", flat=True)) == ["Martes"]
    assert ActividadCentro.objects.count() == 1
    assert client.get(_editar(actividad)).json()["messages"][0]["message"] == (
        "La actividad fue actualizada correctamente."
    )


def test_edit_post_invalid_changes_nothing(actor, datos):
    actividad = _existente(datos)

    respuesta = _client(actor).post(
        _editar(actividad), _datos(datos, cantidad_personas="", horariosdesde="")
    )

    assert respuesta.status_code == 400
    actividad.refresh_from_db()
    assert (actividad.cantidad_personas, actividad.estado) == (5, "planificada")
    assert list(actividad.dias.values_list("nombre", flat=True)) == ["Lunes"]


def test_edit_faro_price_rule_and_missing_activity(actor, datos):
    actividad = _existente(datos, centro="faro")
    client = _client(actor)

    respuesta = client.post(_editar(actividad), _datos(datos, precio="100"))

    assert respuesta.status_code == 400
    assert respuesta.json()["non_field_errors"] == [
        "Un centro de tipo FARO no debe tener un precio asignado."
    ]
    actividad.refresh_from_db()
    assert actividad.precio == 300
    assert client.get("/api/web/cdf/actividades/999999/editar/").status_code == 404


# --- Access -------------------------------------------------------------------


def test_access_chain_and_csrf(datos):
    actividad = _existente(datos)
    sin_permiso = _client(_actor("cdf_sin_permiso", view=False))
    antes = ActividadCentro.objects.count()

    assert Client().get(_crear(datos["adherido"])).status_code == 401
    assert Client().get(_editar(actividad)).status_code == 401
    assert sin_permiso.get(_crear(datos["adherido"])).status_code == 403
    assert sin_permiso.post(_crear(datos["adherido"]), _datos(datos)).status_code == 403
    assert sin_permiso.post(_editar(actividad), _datos(datos)).status_code == 403
    con_csrf = _client(_actor("cdf_csrf"), csrf=True)
    assert con_csrf.post(_crear(datos["adherido"]), _datos(datos)).status_code == 403
    assert con_csrf.post(_editar(actividad), _datos(datos)).status_code == 403
    actividad.refresh_from_db()
    assert ActividadCentro.objects.count() == antes
    assert (actividad.cantidad_personas, actividad.estado) == (5, "planificada")
