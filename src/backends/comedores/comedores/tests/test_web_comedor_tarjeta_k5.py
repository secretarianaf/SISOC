"""Web API (G1 v1) of the comedor card holder (CO07.03).

The endpoint runs the native ``ResponsableTarjetaComedorUpdateView``; these tests
check the guard chain (route permission, exact group, program, object scope), the
projection of the real chained form, the persisted effects and that every
rejection leaves the comedor unchanged.
"""

import pytest
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client

from comedores.models import Comedor, Programas
from core.models import Localidad, Municipio, Provincia
from duplas.models import Dupla

pytestmark = pytest.mark.django_db
User = get_user_model()
ROOT = "/api/web/comedores/comedores/"
GRUPO = "Tecnico Comedor"
CAMPOS = (
    "responsable_tarjeta_nombre",
    "responsable_tarjeta_mail",
    "responsable_tarjeta_dni",
    "responsable_tarjeta_cuit",
    "responsable_tarjeta_domicilio",
    "responsable_tarjeta_provincia",
    "responsable_tarjeta_municipio",
    "responsable_tarjeta_localidad",
    "responsable_tarjeta_telefono",
)


@pytest.fixture(name="comedor_fixture", autouse=True)
def sin_dobles_del_conftest():
    """Same name as the folder's autouse double: these tests run the real services."""


def _perm(user, code):
    app, codename = code.split(".")
    permiso = Permission.objects.get_or_create(
        codename=codename,
        content_type=ContentType.objects.get_for_model(User),
        defaults={"name": codename},
    )[0]
    assert app == "auth"
    user.user_permissions.add(permiso)


def _user(username, *, permiso=True, grupo=True, **flags):
    user = User.objects.create_user(username, password="x", **flags)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    if permiso:
        _perm(user, "auth.role_tecnico_comedor")
    if grupo:
        user.groups.add(Group.objects.get_or_create(name=GRUPO)[0])
    return user


def _client(user, enforce_csrf=False):
    client = Client(enforce_csrf_checks=enforce_csrf)
    client.force_login(user)
    return client


def _url(comedor):
    return f"{ROOT}{comedor.pk}/responsable-tarjeta/"


def _estado(comedor):
    comedor.refresh_from_db()
    return {c.name: getattr(comedor, c.attname) for c in Comedor._meta.concrete_fields}


def _mensajes(respuesta):
    return [str(m) for m in messages.get_messages(respuesta.wsgi_request)]


@pytest.fixture(name="geo")
def geo_fixture():
    sur = Provincia.objects.create(nombre="Sur Tarjeta")
    norte = Provincia.objects.create(nombre="Norte Tarjeta")
    muni_sur = Municipio.objects.create(nombre="Municipio Sur", provincia=sur)
    muni_norte = Municipio.objects.create(nombre="Municipio Norte", provincia=norte)
    return {
        "sur": sur,
        "norte": norte,
        "muni_sur": muni_sur,
        "muni_norte": muni_norte,
        "loc_sur": Localidad.objects.create(nombre="Localidad Sur", municipio=muni_sur),
        "loc_norte": Localidad.objects.create(
            nombre="Localidad Norte", municipio=muni_norte
        ),
    }


@pytest.fixture(name="escenario")
def escenario_fixture():
    tecnico = _user("tecnico_k5tar")
    abogado = _user("abogado_k5tar", permiso=False, grupo=False)
    dupla = Dupla.objects.create(
        nombre="Dupla Tarjeta", estado="Activo", abogado=abogado
    )
    dupla.tecnico.add(tecnico)
    programa = Programas.objects.create(nombre="Alimentar Comunidad")
    comedor = Comedor.objects.create(
        nombre="Comedor Tarjeta", programa=programa, dupla=dupla
    )
    return {"tecnico": tecnico, "comedor": comedor, "programa": programa}


def test_access_anonymous_401_permission_403_and_csrf_403(escenario):
    comedor = escenario["comedor"]
    sin_permiso = _client(_user("sinperm_k5tar", permiso=False, grupo=False))
    estricto = _client(_user("estricto_k5tar"), enforce_csrf=True)

    assert Client().get(_url(comedor)).status_code == 401
    assert Client().post(_url(comedor), {}).status_code == 401
    assert sin_permiso.get(_url(comedor)).status_code == 403
    assert sin_permiso.post(_url(comedor), {}).status_code == 403
    assert estricto.post(_url(comedor), {}).status_code == 403


def test_the_group_is_required_even_when_the_permission_passes(escenario):
    comedor = escenario["comedor"]
    antes = _estado(comedor)
    sin_grupo = _client(_user("singrupo_k5tar", grupo=False))
    root = _client(_user("root_k5tar", permiso=False, grupo=False, is_superuser=True))

    assert sin_grupo.get(_url(comedor)).status_code == 404
    assert (
        sin_grupo.post(_url(comedor), {"responsable_tarjeta_nombre": "X"}).status_code
        == 404
    )
    assert root.get(_url(comedor)).status_code == 404
    assert _estado(comedor) == antes


def test_other_programs_and_comedores_outside_the_scope_are_404(escenario):
    comedor = escenario["comedor"]
    otro_programa = Comedor.objects.create(
        nombre="Otro programa",
        programa=Programas.objects.create(nombre="Otro"),
        dupla=comedor.dupla,
    )
    ajeno = Comedor.objects.create(nombre="Ajeno", programa=escenario["programa"])
    web = _client(escenario["tecnico"])
    antes = _estado(ajeno)

    assert web.get(_url(otro_programa)).status_code == 404
    assert web.get(_url(ajeno)).status_code == 404
    assert web.post(_url(ajeno), {"responsable_tarjeta_nombre": "X"}).status_code == 404
    assert _estado(ajeno) == antes


def test_get_projects_the_nine_fields_in_template_order_with_the_chained_options(
    escenario, geo
):
    comedor = escenario["comedor"]
    comedor.responsable_tarjeta_nombre = "Ana"
    comedor.responsable_tarjeta_provincia = geo["sur"]
    comedor.responsable_tarjeta_municipio = geo["muni_sur"]
    comedor.responsable_tarjeta_localidad = geo["loc_sur"]
    comedor.save()

    datos = _client(escenario["tecnico"]).get(_url(comedor)).json()["form"]

    assert [f["name"] for f in datos["fields"]] == [
        "responsable_tarjeta_nombre",
        "responsable_tarjeta_mail",
        "responsable_tarjeta_dni",
        "responsable_tarjeta_cuit",
        "responsable_tarjeta_telefono",
        "responsable_tarjeta_domicilio",
        "responsable_tarjeta_provincia",
        "responsable_tarjeta_municipio",
        "responsable_tarjeta_localidad",
    ]
    campos = {f["name"]: f for f in datos["fields"]}
    assert campos["responsable_tarjeta_nombre"]["value"] == "Ana"
    assert campos["responsable_tarjeta_nombre"]["attrs"]["maxlength"] == "255"
    assert campos["responsable_tarjeta_mail"]["type"] == "email"
    assert campos["responsable_tarjeta_dni"]["attrs"]["maxlength"] == "20"
    assert all(not f["required"] for f in datos["fields"])
    provincias = [
        o["label"] for o in campos["responsable_tarjeta_provincia"]["options"]
    ]
    assert provincias[1:] == list(
        Provincia.objects.order_by("nombre").values_list("nombre", flat=True)
    )
    assert campos["responsable_tarjeta_provincia"]["value"] == str(geo["sur"].pk)
    assert [o["label"] for o in campos["responsable_tarjeta_municipio"]["options"]][
        1:
    ] == ["Municipio Sur"]
    assert [o["label"] for o in campos["responsable_tarjeta_localidad"]["options"]][
        1:
    ] == ["Localidad Sur"]
    assert datos["urls"]["ficha"] == f"/comedores/{comedor.pk}"
    assert datos["urls"]["municipios"] and datos["urls"]["localidades"]


def test_get_derives_the_municipio_of_a_legacy_localidad_without_municipio(
    escenario, geo
):
    comedor = escenario["comedor"]
    comedor.responsable_tarjeta_provincia = geo["sur"]
    comedor.responsable_tarjeta_localidad = geo["loc_sur"]
    comedor.save()

    campos = {
        f["name"]: f
        for f in _client(escenario["tecnico"])
        .get(_url(comedor))
        .json()["form"]["fields"]
    }

    assert campos["responsable_tarjeta_municipio"]["value"] == str(geo["muni_sur"].pk)
    assert campos["responsable_tarjeta_localidad"]["value"] == str(geo["loc_sur"].pk)


def test_without_municipio_the_localidades_fall_back_to_the_provincia(escenario, geo):
    comedor = escenario["comedor"]
    Localidad.objects.create(nombre="Otra Sur", municipio=geo["muni_sur"])
    comedor.responsable_tarjeta_provincia = geo["sur"]
    comedor.save()

    campos = {
        f["name"]: f
        for f in _client(escenario["tecnico"])
        .get(_url(comedor))
        .json()["form"]["fields"]
    }

    assert sorted(
        o["label"] for o in campos["responsable_tarjeta_localidad"]["options"][1:]
    ) == ["Localidad Sur", "Otra Sur"]


def test_post_saves_only_the_nine_fields_and_goes_to_the_ficha(escenario, geo):
    comedor = escenario["comedor"]
    antes = _estado(comedor)

    respuesta = _client(escenario["tecnico"]).post(
        _url(comedor),
        {
            "responsable_tarjeta_nombre": "Ana Pérez",
            "responsable_tarjeta_mail": "ana@example.org",
            "responsable_tarjeta_dni": "30111222",
            "responsable_tarjeta_cuit": "27301112229",
            "responsable_tarjeta_domicilio": "Calle 1",
            "responsable_tarjeta_provincia": geo["sur"].pk,
            "responsable_tarjeta_municipio": geo["muni_sur"].pk,
            "responsable_tarjeta_localidad": geo["loc_sur"].pk,
            "responsable_tarjeta_telefono": "1155550000",
            # Not rendered by the native page: must stay untouched.
            "nombre": "Cambiado",
            "estado_validacion": "Validado",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"redirect": f"/comedores/{comedor.pk}"}
    assert _mensajes(respuesta) == []
    despues = _estado(comedor)
    cambios = {k for k in despues if despues[k] != antes[k]}
    assert cambios == {
        "responsable_tarjeta_nombre",
        "responsable_tarjeta_mail",
        "responsable_tarjeta_dni",
        "responsable_tarjeta_cuit",
        "responsable_tarjeta_domicilio",
        "responsable_tarjeta_provincia",
        "responsable_tarjeta_municipio",
        "responsable_tarjeta_localidad",
        "responsable_tarjeta_telefono",
    }
    assert despues["nombre"] == "Comedor Tarjeta"
    assert despues["estado_validacion"] == antes["estado_validacion"]


def test_a_partial_load_is_accepted(escenario):
    comedor = escenario["comedor"]

    respuesta = _client(escenario["tecnico"]).post(
        _url(comedor), {"responsable_tarjeta_nombre": "Solo nombre"}
    )

    assert respuesta.status_code == 200
    comedor.refresh_from_db()
    assert comedor.responsable_tarjeta_nombre == "Solo nombre"


@pytest.mark.parametrize(
    ("datos", "campo", "mensaje"),
    [
        (
            {"responsable_tarjeta_mail": "no-es-un-mail"},
            "responsable_tarjeta_mail",
            "Introduzca una dirección de correo electrónico válida.",
        ),
        (
            {"responsable_tarjeta_dni": "1" * 21},
            "responsable_tarjeta_dni",
            None,
        ),
        (
            {"responsable_tarjeta_nombre": "x" * 256},
            "responsable_tarjeta_nombre",
            None,
        ),
    ],
)
def test_invalid_text_fields_are_rejected_and_change_nothing(
    escenario, datos, campo, mensaje
):
    comedor = escenario["comedor"]
    antes = _estado(comedor)

    respuesta = _client(escenario["tecnico"]).post(_url(comedor), datos)

    assert respuesta.status_code == 400
    errores = respuesta.json()["errors"][campo]
    assert errores and (mensaje is None or errores == [mensaje])
    assert _estado(comedor) == antes


def test_a_municipio_of_another_provincia_is_rejected_and_changes_nothing(
    escenario, geo
):
    comedor = escenario["comedor"]
    antes = _estado(comedor)

    respuesta = _client(escenario["tecnico"]).post(
        _url(comedor),
        {
            "responsable_tarjeta_provincia": geo["sur"].pk,
            "responsable_tarjeta_municipio": geo["muni_norte"].pk,
        },
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["errors"]["responsable_tarjeta_municipio"]
    assert _estado(comedor) == antes


def test_a_localidad_of_another_municipio_is_rejected_and_changes_nothing(
    escenario, geo
):
    comedor = escenario["comedor"]
    antes = _estado(comedor)

    respuesta = _client(escenario["tecnico"]).post(
        _url(comedor),
        {
            "responsable_tarjeta_provincia": geo["sur"].pk,
            "responsable_tarjeta_municipio": geo["muni_sur"].pk,
            "responsable_tarjeta_localidad": geo["loc_norte"].pk,
        },
    )

    assert respuesta.status_code == 400
    cuerpo = respuesta.json()
    assert cuerpo["errors"]["responsable_tarjeta_localidad"]
    assert [
        o["label"]
        for f in cuerpo["form"]["fields"]
        if f["name"] == "responsable_tarjeta_localidad"
        for o in f["options"][1:]
    ] == ["Localidad Sur"]
    assert _estado(comedor) == antes


def test_a_rejected_post_echoes_what_was_sent(escenario, geo):
    comedor = escenario["comedor"]

    cuerpo = (
        _client(escenario["tecnico"])
        .post(
            _url(comedor),
            {
                "responsable_tarjeta_nombre": "Ana",
                "responsable_tarjeta_mail": "no-es-un-mail",
                "responsable_tarjeta_provincia": geo["sur"].pk,
            },
        )
        .json()
    )

    campos = {f["name"]: f for f in cuerpo["form"]["fields"]}
    assert campos["responsable_tarjeta_nombre"]["value"] == "Ana"
    assert campos["responsable_tarjeta_mail"]["value"] == "no-es-un-mail"
    assert campos["responsable_tarjeta_provincia"]["value"] == str(geo["sur"].pk)
    assert [o["label"] for o in campos["responsable_tarjeta_municipio"]["options"]][
        1:
    ] == ["Municipio Sur"]


def test_only_get_head_and_post_are_served(escenario):
    web = _client(escenario["tecnico"])

    assert web.put(_url(escenario["comedor"]), {}).status_code == 405
    assert web.delete(_url(escenario["comedor"])).status_code == 405
