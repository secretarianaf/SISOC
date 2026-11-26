"""Web API (G1 v1) of the comedor nómina actions: state change and derivation (CO01).

Both endpoints call the native functions; these tests check the persisted effects, that
every rejection leaves the nómina tables untouched, and the access in front of them.
"""

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client

from admisiones.models.admisiones import Admision
from ciudadanos.models import Ciudadano, Sexo
from comedores.models import Comedor, Nomina, NominaDerivacion, Programas

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _client(username, *codenames, enforce_csrf=False):
    usuario = _ready(get_user_model().objects.create_user(username, password="x"))
    for codename in codenames:
        usuario.user_permissions.add(Permission.objects.get(codename=codename))
    client = Client(enforce_csrf_checks=enforce_csrf)
    client.force_login(usuario)
    return client


def _estado(pk):
    return f"/api/web/comedores/comedores/nomina/{pk}/cambiar-estado/"


def _derivar(pk):
    return f"/api/web/comedores/comedores/nomina/{pk}/derivar/"


def _snapshot():
    return (
        list(Nomina.objects.order_by("pk").values_list("pk", "estado", "deleted_at")),
        list(NominaDerivacion.objects.values_list("pk", flat=True)),
    )


@pytest.fixture(name="datos")
def datos_fixture():
    sexo, _ = Sexo.objects.get_or_create(sexo="Femenino")
    programa = Programas.objects.create(
        nombre="Programa directo acciones", usa_admision_para_nomina=False
    )
    origen = Comedor.objects.create(nombre="Origen", programa=programa)
    destino = Comedor.objects.create(nombre="Destino", programa=programa)
    persona = Ciudadano.objects.create(
        nombre="Ana",
        apellido="Gómez",
        documento="30999111",
        sexo=sexo,
        fecha_nacimiento=date(2000, 1, 1),
    )
    activa = Nomina.objects.create(comedor=origen, ciudadano=persona, estado="activo")
    espera = Nomina.objects.create(
        comedor=origen,
        ciudadano=Ciudadano.objects.create(
            nombre="Beto",
            apellido="Ruiz",
            documento="30999222",
            sexo=sexo,
            fecha_nacimiento=date(1990, 1, 1),
        ),
        estado="espera",
    )
    return {"origen": origen, "destino": destino, "activa": activa, "espera": espera}


def test_change_state_persists_only_the_estado(datos):
    web = _client("cambiar_estado_ok", "change_nomina")

    respuesta = web.post(_estado(datos["activa"].pk), {"estado": "baja"})

    assert respuesta.status_code == 200
    assert respuesta.json() == {"success": True, "estado": "baja"}
    datos["activa"].refresh_from_db()
    assert datos["activa"].estado == "baja"
    assert datos["activa"].deleted_at is None
    datos["espera"].refresh_from_db()
    assert datos["espera"].estado == "espera"


def test_change_state_rejections_write_nothing(datos):
    web = _client("cambiar_estado_rechazos", "change_nomina")
    antes = _snapshot()

    invalido = web.post(_estado(datos["activa"].pk), {"estado": "otro"})
    vacio = web.post(_estado(datos["activa"].pk), {})
    inexistente = web.post(_estado(999999), {"estado": "baja"})
    metodo = web.get(_estado(datos["activa"].pk))

    assert invalido.status_code == 400
    assert invalido.json() == {"success": False, "error": "Estado inválido."}
    assert vacio.status_code == 400
    assert inexistente.status_code == 404
    assert metodo.status_code == 405
    assert metodo.json() == {"success": False, "error": "Método no permitido."}
    assert _snapshot() == antes


def test_change_state_access_is_the_native_one(datos):
    antes = _snapshot()
    cuerpo = {"estado": "baja"}
    sin_permiso = _client("cambiar_estado_sin", "view_nomina")
    sin_csrf = _client("cambiar_estado_csrf", "change_nomina", enforce_csrf=True)

    assert Client().post(_estado(datos["activa"].pk), cuerpo).status_code in (401, 403)
    assert sin_permiso.post(_estado(datos["activa"].pk), cuerpo).status_code == 403
    assert sin_csrf.post(_estado(datos["activa"].pk), cuerpo).status_code == 403
    assert _snapshot() == antes


def test_derive_moves_the_person_and_records_the_derivation(datos):
    web = _client("derivar_ok", "change_nomina", "add_nomina")

    respuesta = web.post(
        _derivar(datos["activa"].pk),
        {"centro_destino_id": datos["destino"].pk, "motivo": "  Se muda  "},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "success": True,
        "message": "Derivación realizada correctamente.",
    }
    datos["activa"].refresh_from_db()
    assert datos["activa"].estado == "baja"
    nueva = Nomina.objects.get(comedor=datos["destino"])
    assert nueva.estado == "espera"
    assert nueva.ciudadano_id == datos["activa"].ciudadano_id
    derivacion = NominaDerivacion.objects.get()
    assert derivacion.nomina_origen_id == datos["activa"].pk
    assert derivacion.nomina_destino_id == nueva.pk
    assert derivacion.motivo == "Se muda"
    assert derivacion.comedor_origen_id == datos["origen"].pk
    assert derivacion.comedor_destino_id == datos["destino"].pk


def test_derive_rejections_write_nothing(datos):
    web = _client("derivar_rechazos", "change_nomina", "add_nomina")
    antes = _snapshot()

    sin_destino = web.post(_derivar(datos["activa"].pk), {"centro_destino_id": "x"})
    mismo = web.post(
        _derivar(datos["activa"].pk), {"centro_destino_id": datos["origen"].pk}
    )
    inexistente = web.post(_derivar(datos["activa"].pk), {"centro_destino_id": 999999})
    en_espera = web.post(
        _derivar(datos["espera"].pk), {"centro_destino_id": datos["destino"].pk}
    )
    sin_nomina = web.post(_derivar(999999), {"centro_destino_id": datos["destino"].pk})
    metodo = web.get(_derivar(datos["activa"].pk))

    assert sin_destino.status_code == 400
    assert sin_destino.json() == {
        "success": False,
        "message": "Centro destino inválido.",
    }
    assert mismo.json()["message"] == (
        "El centro destino debe ser diferente al centro de origen."
    )
    assert inexistente.status_code == 400
    assert (
        en_espera.json()["message"]
        == "Solo se pueden derivar personas con estado Activo."
    )
    assert sin_nomina.status_code == 404
    assert metodo.status_code == 405
    assert _snapshot() == antes


def test_derive_repeated_is_rejected_without_a_second_write(datos):
    web = _client("derivar_repetida", "change_nomina", "add_nomina")
    cuerpo = {"centro_destino_id": datos["destino"].pk}

    assert web.post(_derivar(datos["activa"].pk), cuerpo).status_code == 200
    despues = _snapshot()
    repetida = web.post(_derivar(datos["activa"].pk), cuerpo)

    assert repetida.status_code == 400
    assert _snapshot() == despues


def test_derive_needs_both_permissions_and_csrf(datos):
    antes = _snapshot()
    cuerpo = {"centro_destino_id": datos["destino"].pk}
    solo_cambiar = _client("derivar_solo_cambiar", "change_nomina")
    solo_agregar = _client("derivar_solo_agregar", "add_nomina")
    sin_csrf = _client("derivar_csrf", "change_nomina", "add_nomina", enforce_csrf=True)

    assert Client().post(_derivar(datos["activa"].pk), cuerpo).status_code in (401, 403)
    assert solo_cambiar.post(_derivar(datos["activa"].pk), cuerpo).status_code == 403
    assert solo_agregar.post(_derivar(datos["activa"].pk), cuerpo).status_code == 403
    assert sin_csrf.post(_derivar(datos["activa"].pk), cuerpo).status_code == 403
    assert _snapshot() == antes


def test_admission_nomina_derives_to_a_direct_comedor(datos):
    admision = Admision.objects.create(comedor=Comedor.objects.create(nombre="Con adm"))
    por_admision = Nomina.objects.create(
        admision=admision, ciudadano=datos["activa"].ciudadano, estado="activo"
    )
    web = _client("acciones_admision", "change_nomina", "add_nomina")

    respuesta = web.post(
        _derivar(por_admision.pk), {"centro_destino_id": datos["destino"].pk}
    )

    assert respuesta.status_code == 200
    por_admision.refresh_from_db()
    assert por_admision.estado == "baja"
