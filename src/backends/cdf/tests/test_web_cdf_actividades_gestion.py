"""Web API (G1 v1) of the CDF activity list and the catalog form (CDF-B).

The endpoints run ``ActividadCentroListView`` and ``ActividadCreateView``; the
tests pin the native list (order, centre filter, no paging, the related manager
text printed when there are no days), the persisted effect of the catalog save,
the unchanged data after a rejection and that the access chain stays the
current one (login and ``view_centro``; the catalog ``test_func`` is not a gate).
"""

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client

from centrodefamilia.models import Actividad, ActividadCentro, Categoria, Centro
from core.models import Dia, Provincia

pytestmark = pytest.mark.django_db

LIST = "/api/web/cdf/actividades/"
CATALOGO = "/api/web/cdf/actividades/nueva/"


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
    return _actor("cdf_actividades")


def _centro(nombre, codigo):
    return Centro.objects.create(
        nombre=nombre,
        tipo="faro",
        codigo=codigo,
        provincia=Provincia.objects.get_or_create(nombre="Provincia Actividades")[0],
        domicilio_actividad="Domicilio",
        telefono="011",
        celular="15",
        correo="c@example.com",
        nombre_referente="Lia",
        apellido_referente="Paz",
        telefono_referente="012",
        correo_referente="lia@example.com",
    )


def _actividad(centro, nombre, categoria, dias=(), estado="planificada"):
    actividad = ActividadCentro.objects.create(
        centro=centro,
        actividad=Actividad.objects.create(nombre=nombre, categoria=categoria),
        cantidad_personas=5,
        horariosdesde="09:00",
        horarioshasta="10:30",
        estado=estado,
    )
    actividad.dias.set([Dia.objects.get_or_create(nombre=d)[0] for d in dias])
    return actividad


@pytest.fixture(name="datos")
def datos_fixture():
    categoria = Categoria.objects.create(nombre="Deportes")
    zeta = _centro("Zeta", "ZETA")
    alfa = _centro("Alfa", "ALFA")
    return {
        "categoria": categoria,
        "zeta": zeta,
        "alfa": alfa,
        "z_futbol": _actividad(zeta, "Futbol", categoria, ("Lunes", "Martes")),
        "a_tenis": _actividad(alfa, "Tenis", categoria, (), "en_curso"),
        "a_ajedrez": _actividad(alfa, "Ajedrez", categoria, ("Viernes",)),
    }


# --- List ---------------------------------------------------------------------


def test_list_is_the_native_unpaged_list_ordered_by_centre_and_activity(actor, datos):
    respuesta = _client(actor).get(LIST)

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    assert [(f["centro"], f["actividad"]) for f in data["results"]] == [
        ("Alfa", "Ajedrez"),
        ("Alfa", "Tenis"),
        ("Zeta", "Futbol"),
    ]
    assert [h["title"] for h in data["headers"]] == [
        "Centro",
        "Actividad",
        "Días",
        "Horario Desde",
        "Horario Hasta",
        "Estado",
    ]
    assert data["headers"][0] == {
        "title": "Centro",
        "sortable": True,
        "sort_key": "centro",
    }
    fila = data["results"][2]
    assert fila["dias"] == ["Lunes", "Martes"]
    assert fila["horariosdesde"] == "09:00" and fila["horarioshasta"] == "10:30"
    assert fila["estado_display"] == "Planificada"
    assert fila["urls"]["detail"] == (
        f"/centrodefamilia/centros/actividades/{datos['z_futbol'].pk}/detalle/"
    )


def test_list_prints_the_manager_text_when_an_activity_has_no_days(actor, datos):
    tenis = next(
        f
        for f in _client(actor).get(LIST).json()["results"]
        if f["actividad"] == "Tenis"
    )

    assert tenis["dias"] == []
    assert tenis["dias_vacio"] == "core.Dia.None"


def test_list_filters_by_centre_and_ignores_an_empty_filter(actor, datos):
    client = _client(actor)

    filtrada = client.get(LIST, {"centro": datos["zeta"].pk}).json()["results"]
    vacia = client.get(LIST, {"centro": ""}).json()["results"]
    otro = client.get(LIST, {"centro": 999999}).json()["results"]

    assert [f["actividad"] for f in filtrada] == ["Futbol"]
    assert len(vacia) == 3 and otro == []


def test_list_access_chain_is_login_then_view_centro(datos):
    assert Client().get(LIST).status_code == 401
    assert _client(_actor("cdf_sin_permiso", view=False)).get(LIST).status_code == 403


# --- Catalog ------------------------------------------------------------------


def test_catalog_get_lists_the_fields_with_the_native_widget_attributes(actor, datos):
    respuesta = _client(actor).get(CATALOGO)

    assert respuesta.status_code == 200
    data = respuesta.json()
    campos = {f["name"]: f for f in data["fields"]}
    assert list(campos) == ["categoria", "nombre"]
    assert campos["categoria"]["label"] == "Categoría"
    assert campos["categoria"]["html"]["class"] == "form-control form-control-sm"
    assert [c["label"] for c in campos["categoria"]["choices"]] == [
        "---------",
        "Deportes",
    ]
    assert campos["nombre"]["html"]["placeholder"] == "Ej. Taller de oficio"
    assert data["urls"]["cancel"] == "/centrodefamilia/centros/"
    assert data["errors"] == {} and data["non_field_errors"] == []


def test_catalog_post_saves_the_activity_and_queues_no_message(actor, datos):
    client = _client(actor)

    respuesta = client.post(
        CATALOGO, {"categoria": datos["categoria"].pk, "nombre": "Natacion"}
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"url": "/centrodefamilia/centros/"}
    creada = Actividad.objects.get(nombre="Natacion")
    assert creada.categoria == datos["categoria"]
    assert client.get(CATALOGO).json()["messages"] == []


def test_catalog_post_without_data_is_a_400_with_errors_and_saves_nothing(actor, datos):
    antes = Actividad.objects.count()

    respuesta = _client(actor).post(CATALOGO, {"nombre": " "})

    assert respuesta.status_code == 400
    errores = respuesta.json()["errors"]
    assert set(errores) == {"categoria", "nombre"}
    assert errores["categoria"][0]["message"] == "Este campo es requerido."
    assert Actividad.objects.count() == antes


def test_catalog_access_is_login_and_view_centro_only(datos):
    plain = _actor("cdf_sin_superuser")
    sin_permiso = _client(_actor("cdf_sin_permiso", view=False))
    datos_post = {"categoria": datos["categoria"].pk, "nombre": "Nuevo"}
    antes = Actividad.objects.count()

    assert Client().get(CATALOGO).status_code == 401
    assert sin_permiso.get(CATALOGO).status_code == 403
    assert sin_permiso.post(CATALOGO, datos_post).status_code == 403
    assert Actividad.objects.count() == antes
    # The native ``test_func`` (superuser) is never evaluated: a plain actor saves.
    assert _client(plain).post(CATALOGO, datos_post).status_code == 200
    assert Actividad.objects.count() == antes + 1


def test_catalog_post_requires_csrf(actor, datos):
    antes = Actividad.objects.count()

    respuesta = _client(actor, csrf=True).post(
        CATALOGO, {"categoria": datos["categoria"].pk, "nombre": "Sin csrf"}
    )

    assert respuesta.status_code == 403
    assert Actividad.objects.count() == antes
