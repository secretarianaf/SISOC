"""Ficha Ciudadano 360 en JSON (C05.01): datos, familia, historial, interacciones y mensajes."""

from datetime import date

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client

from ciudadanos.models import (
    Ciudadano,
    GrupoFamiliar,
    HistorialTransferencia,
    Interaccion,
)
from core.models import Sexo

pytestmark = pytest.mark.django_db

PERM = "ciudadanos.view_ciudadano"


def _cliente(username, permisos=(PERM,)):
    user = User.objects.create_user(username=username, password="x")
    for codigo in permisos:
        app, codename = codigo.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="ciudadano")
def ciudadano_fixture():
    return Ciudadano.objects.create(
        nombre="Ana",
        apellido="Aporte",
        documento=30111222,
        calle="Mitre",
        altura="123",
        fecha_nacimiento=date(1990, 5, 17),
        telefono="1155550000",
        sexo=Sexo.objects.create(sexo="F"),
        observaciones="Sin novedades <b>",
    )


def _ficha(client, ciudadano):
    return client.get(f"/api/web/ciudadanos/{ciudadano.pk}/").json()


def test_datos_personales_se_proyectan_como_el_template(ciudadano):
    datos = _ficha(_cliente("lector_ficha"), ciudadano)["datos"]
    assert datos["apellido"] == "Aporte"
    assert datos["numero_documento"] == "30111222"
    assert datos["calle_altura"] == "Mitre 123"
    assert datos["fecha_nacimiento"] == "17/05/1990"
    assert datos["genero"] == "F"
    assert datos["telefono"] == "1155550000"
    # Vacíos: ``default:'-'``; sin país emisor el template no dibuja la fila.
    assert datos["email"] == datos["provincia"] == datos["cuil_cuit"] == "-"
    assert datos["pais_emisor"] is None
    assert (
        datos["fecha_actualizacion"].count("/") == 2
        and ":" in datos["fecha_actualizacion"]
    )


def test_calle_vacia_se_muestra_con_guion():
    ciudadano = Ciudadano.objects.create(nombre="Vera", apellido="Vacia", documento=1)
    ficha = _ficha(_cliente("lector_vacia"), ciudadano)
    assert ficha["datos"]["calle_altura"] == "-"
    assert ficha["mapa"] is None and ficha["foto_url"] is None
    assert ficha["observaciones"] == ""
    assert ficha["familia"] == [] and ficha["interacciones"] == []


def test_acciones_y_permiso_del_historial(ciudadano):
    sin = _ficha(_cliente("lector_acc"), ciudadano)["acciones"]
    assert sin["historial_url"] is None
    assert sin["editar_url"] == f"/ciudadanos/editar/{ciudadano.pk}"
    assert sin["eliminar_url"] == f"/ciudadanos/eliminar/{ciudadano.pk}"
    assert sin["familiar_nuevo_url"] == f"/ciudadanos/{ciudadano.pk}/familiares/nuevo"
    con = _ficha(_cliente("auditor_acc", (PERM, "auditlog.view_logentry")), ciudadano)
    assert con["acciones"]["historial_url"].endswith(f"/ciudadano/{ciudadano.pk}/")


def test_aviso_de_identidad(ciudadano):
    assert _ficha(_cliente("lector_id1"), ciudadano)["identidad"]["mostrar"] is False
    Ciudadano.objects.filter(pk=ciudadano.pk).update(
        tipo_registro_identidad="SIN_DNI",
        motivo_sin_dni_descripcion="Perdió el documento",
        requiere_revision_manual=True,
    )
    identidad = _ficha(_cliente("lector_id2"), ciudadano)["identidad"]
    assert identidad == {
        "mostrar": True,
        "sin_dni": True,
        "no_validado": False,
        "requiere_revision": True,
        "motivo_texto": "",
        "descripcion_texto": "Perdió el documento",
    }


def test_familia_conserva_el_orden_nativo(ciudadano):
    zeta = Ciudadano.objects.create(nombre="Zoe", apellido="Zeta", documento=2)
    alfa = Ciudadano.objects.create(nombre="Abel", apellido="Alfa", documento=3)
    GrupoFamiliar.objects.create(
        ciudadano_1=ciudadano, ciudadano_2=zeta, vinculo="HIJO/A"
    )
    GrupoFamiliar.objects.create(
        ciudadano_1=alfa, ciudadano_2=ciudadano, vinculo="PAREJA"
    )
    familia = _ficha(_cliente("lector_fam"), ciudadano)["familia"]
    assert [(f["vinculo_texto"], f["apellido"], f["edad_texto"]) for f in familia] == [
        ("Pareja", "Alfa", "-"),
        ("Hijo/a", "Zeta", "-"),
    ]
    assert familia[0]["url"] == f"/ciudadanos/ver/{alfa.pk}"


def test_interacciones_y_observaciones(ciudadano):
    jefa = User.objects.create_user("jefa_ficha", first_name="Julia", last_name="Paz")
    Interaccion.objects.create(
        ciudadano=ciudadano,
        tipo="Llamada",
        fecha=date(2026, 3, 4),
        responsable=jefa,
        estado="completo",
    )
    Interaccion.objects.create(
        ciudadano=ciudadano, tipo="Visita", fecha=date(2026, 2, 1), estado="otro"
    )
    ficha = _ficha(_cliente("lector_int"), ciudadano)
    assert [
        (i["tipo"], i["responsable_texto"], i["estado"]) for i in ficha["interacciones"]
    ] == [
        ("Llamada", "Julia Paz", "completo"),
        ("Visita", "Sin asignar", "pendiente"),
    ]
    assert ficha["interacciones"][0]["fecha_texto"] == "04 Mar 2026"
    assert ficha["observaciones"] == "Sin novedades <b>"


def test_solo_las_diez_ultimas_interacciones(ciudadano):
    for dia in range(1, 13):
        Interaccion.objects.create(
            ciudadano=ciudadano, tipo=f"I{dia}", fecha=date(2026, 1, dia)
        )
    tipos = [
        i["tipo"] for i in _ficha(_cliente("lector_diez"), ciudadano)["interacciones"]
    ]
    assert tipos == [f"I{dia}" for dia in range(12, 2, -1)]


def test_historial_usa_los_meses_nativos(ciudadano):
    from django.utils import timezone

    HistorialTransferencia.objects.create(
        ciudadano=ciudadano,
        mes=3,
        anio=timezone.now().year,
        monto_auh=10,
        monto_comedor="2.50",
    )
    historial = _ficha(_cliente("lector_hist"), ciudadano)["historial"]
    assert historial == {
        "labels": ["Mar"],
        "auh": [10.0],
        "prestacion": [0.0],
        "centro_familia": [0.0],
        "comedor": [2.5],
    }


def test_mensajes_pendientes_se_consumen_una_vez(ciudadano):
    client = _cliente("revisor_msg", (PERM, "ciudadanos.revision_identidad"))
    # El mensaje lo encola la vista nativa ``marcar_revisado``; llega en el siguiente GET.
    client.post(f"/ciudadanos/{ciudadano.pk}/marcar-revisado/")
    primera = _ficha(client, ciudadano)["messages"]
    assert primera == [
        {"message": "Ciudadano Aporte, Ana marcado como revisado.", "level": "success"}
    ]
    assert _ficha(client, ciudadano)["messages"] == []


def test_la_proyeccion_no_escribe(ciudadano):
    antes = Ciudadano.objects.values().get(pk=ciudadano.pk)
    _ficha(_cliente("lector_ro"), ciudadano)
    assert Ciudadano.objects.values().get(pk=ciudadano.pk) == antes


REVISION = "ciudadanos.revision_identidad"


@pytest.fixture(name="pendiente")
def pendiente_fixture():
    return Ciudadano.objects.create(
        nombre="Sara",
        apellido="SinDni",
        tipo_registro_identidad="SIN_DNI",
        motivo_sin_dni=Ciudadano.MOTIVO_SIN_DNI_EXTRAVIADO,
        requiere_revision_manual=True,
    )


def _marcar(client, ciudadano):
    return client.post(f"/api/web/ciudadanos/{ciudadano.pk}/marcar-revisado/")


def test_la_ficha_ofrece_marcar_revisado_solo_con_permiso_y_revision_pendiente(
    pendiente, ciudadano
):
    revisor = _cliente("revisor_url", (PERM, REVISION))
    url = _ficha(revisor, pendiente)["acciones"]["marcar_revisado_url"]
    assert url == f"/api/web/ciudadanos/{pendiente.pk}/marcar-revisado/"
    assert _ficha(revisor, ciudadano)["acciones"]["marcar_revisado_url"] is None
    lector = _cliente("lector_url")
    assert _ficha(lector, pendiente)["acciones"]["marcar_revisado_url"] is None


def test_marcar_revisado_escribe_solo_lo_nativo_y_deja_el_mensaje(pendiente):
    revisor = _cliente("revisor_ok", (PERM, REVISION))
    antes = Ciudadano.objects.values().get(pk=pendiente.pk)
    respuesta = _marcar(revisor, pendiente)
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/ciudadanos/ver/{pendiente.pk}",
    }
    assert "no-store" in respuesta["Cache-Control"]
    despues = Ciudadano.objects.values().get(pk=pendiente.pk)
    cambios = {k for k in antes if antes[k] != despues[k]}
    assert cambios <= {"requiere_revision_manual", "estado_revision_manual"}
    assert despues["requiere_revision_manual"] is False
    assert despues["estado_revision_manual"] == Ciudadano.REVISION_IDENTIDAD_APROBADA
    ficha = _ficha(revisor, pendiente)
    assert ficha["messages"] == [
        {"message": "Ciudadano SinDni, Sara marcado como revisado.", "level": "success"}
    ]
    assert ficha["acciones"]["marcar_revisado_url"] is None


def test_marcar_revisado_rechazado_no_escribe(pendiente):
    antes = Ciudadano.objects.values().get(pk=pendiente.pk)
    assert _marcar(Client(), pendiente).status_code == 401
    sin_permiso = _cliente("lector_rechazo")
    assert _marcar(sin_permiso, pendiente).status_code == 403
    # Sin el permiso un id inexistente tampoco filtra: 403, igual que la vista nativa.
    assert (
        sin_permiso.post("/api/web/ciudadanos/999999/marcar-revisado/").status_code
        == 403
    )
    revisor = _cliente("revisor_rechazo", (PERM, REVISION))
    assert (
        revisor.post("/api/web/ciudadanos/999999/marcar-revisado/").status_code == 404
    )
    assert (
        revisor.get(f"/api/web/ciudadanos/{pendiente.pk}/marcar-revisado/").status_code
        == 405
    )
    assert Ciudadano.objects.values().get(pk=pendiente.pk) == antes


def test_marcar_revisado_exige_csrf(pendiente):
    user = User.objects.create_user(username="revisor_csrf", password="x")
    for codigo in (PERM, REVISION):
        app, codename = codigo.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    antes = Ciudadano.objects.values().get(pk=pendiente.pk)
    assert _marcar(client, pendiente).status_code == 403
    assert Ciudadano.objects.values().get(pk=pendiente.pk) == antes
