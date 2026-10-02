"""El reporte de la API tiene que dar lo mismo que la pantalla.

Las agregaciones son reglas finas (que cuenta como persona unica, que es una
dupla, como se clasifica un aprobado). Viven en `reporte_service` y los dos
frentes lo usan; estos tests fijan que no se separen.
"""

from datetime import date

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from celiaquia.models import (
    EstadoExpediente,
    EstadoLegajo,
    Expediente,
    ExpedienteCiudadano,
    RevisionTecnico,
)
from ciudadanos.models import Ciudadano
from core.models import Localidad, Municipio, Provincia

pytestmark = pytest.mark.django_db


@pytest.fixture
def escenario():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)
    localidad = Localidad.objects.create(nombre="Tolosa", municipio=municipio)
    estado_exp, _ = EstadoExpediente.objects.get_or_create(nombre="EN_ESPERA")
    estado_leg, _ = EstadoLegajo.objects.get_or_create(nombre="CARGADO")

    admin = User.objects.create_superuser("admin_reporte", "r@r.com", "test")
    expediente = Expediente.objects.create(
        usuario_provincia=admin, estado=estado_exp, numero_expediente="EX-REP"
    )
    revisiones = [
        RevisionTecnico.APROBADO,
        RevisionTecnico.APROBADO,
        RevisionTecnico.PENDIENTE,
        RevisionTecnico.RECHAZADO,
    ]
    for i, revision in enumerate(revisiones):
        ciudadano = Ciudadano.objects.create(
            apellido=f"Ape{i}",
            nombre=f"Nom{i}",
            documento=f"2011111111{i}",
            fecha_nacimiento=date(1990, 1, 1),
            provincia=provincia,
            municipio=municipio,
            localidad=localidad,
        )
        ExpedienteCiudadano.objects.create(
            expediente=expediente,
            ciudadano=ciudadano,
            estado=estado_leg,
            revision_tecnico=revision,
        )
    return admin, expediente


def _contexto_pantalla(client):
    """El contexto del template, que es la referencia."""

    respuesta = client.get("/reporter-provincias/")
    contextos = (
        respuesta.context
        if isinstance(respuesta.context, list)
        else [respuesta.context]
    )
    return next(c for c in contextos if "total_casos" in c)


def test_la_api_devuelve_los_mismos_totales_que_la_pantalla(client, escenario):
    admin, _ = escenario
    client.force_login(admin)

    pantalla = _contexto_pantalla(client)
    api = client.get(reverse("celiaquia-reporte-list")).json()

    assert api["total_casos"] == pantalla["total_casos"]
    assert api["casos_documentos_ok"] == pantalla["casos_documentos_ok"]
    assert (
        api["casos_documentos_incompletos"] == pantalla["casos_documentos_incompletos"]
    )
    assert api["casos_con_comentarios"] == pantalla["casos_con_comentarios"]
    assert api["casos_por_instancia"] == pantalla["casos_por_instancia"]


def test_los_porcentajes_coinciden(client, escenario):
    admin, _ = escenario
    client.force_login(admin)

    pantalla = _contexto_pantalla(client)
    api = client.get(reverse("celiaquia-reporte-list")).json()

    assert round(api["porcentaje_documentos_ok"], 4) == round(
        pantalla["porcentaje_documentos_ok"], 4
    )
    assert round(api["porcentaje_documentos_incompletos"], 4) == round(
        pantalla["porcentaje_documentos_incompletos"], 4
    )


def test_la_clasificacion_de_aprobados_coincide(client, escenario):
    """Es la agregación con las reglas más finas: dupla, persona única."""

    admin, _ = escenario
    client.force_login(admin)

    pantalla = _contexto_pantalla(client)
    api = client.get(reverse("celiaquia-reporte-list")).json()

    assert (
        api["clasificacion_aprobados"]["total"]
        == pantalla["clasificacion_aprobados"]["total"]
    )
    conteos_api = [i["count"] for i in api["clasificacion_aprobados"]["items"]]
    conteos_pantalla = [
        i["count"] for i in pantalla["clasificacion_aprobados"]["items"]
    ]
    assert conteos_api == conteos_pantalla


def test_los_filtros_se_aplican_igual(client, escenario):
    admin, _ = escenario
    client.force_login(admin)

    filtrado = client.get(
        reverse("celiaquia-reporte-list"), {"revision_tecnico": "APROBADO"}
    ).json()
    sin_filtro = client.get(reverse("celiaquia-reporte-list")).json()

    assert filtrado["total_casos"] == 2
    assert filtrado["total_casos"] < sin_filtro["total_casos"]
    assert all(c["revision_tecnico"] == "APROBADO" for c in filtrado["casos"])


def test_el_detalle_trae_las_filas_de_la_pagina(client, escenario):
    admin, _ = escenario
    client.force_login(admin)

    api = client.get(reverse("celiaquia-reporte-list")).json()

    assert len(api["casos"]) == api["total_casos"]
    assert api["detalle_desde"] == 1
    assert api["detalle_hasta"] == api["total_casos"]
    primero = api["casos"][0]
    assert primero["documento"]
    assert primero["expediente_numero"] == "EX-REP"


def test_el_usuario_provincial_solo_ve_su_alcance(client, escenario):
    """El scope territorial lo aplica el service, no la pantalla."""

    from users.models import Profile, ProfileTerritorialScope

    _, _expediente = escenario
    otra = Provincia.objects.create(nombre="Salta")
    usuario = User.objects.create_user("prov_reporte", password="x")
    perfil, _ = Profile.objects.get_or_create(user=usuario)
    perfil.es_usuario_provincial = True
    perfil.save()
    ProfileTerritorialScope.objects.create(profile=perfil, provincia=otra)
    usuario.user_permissions.add(
        Permission.objects.get(
            codename="view_expediente",
            content_type=ContentType.objects.get_for_model(Expediente),
        )
    )
    client.force_login(usuario)

    api = client.get(reverse("celiaquia-reporte-list")).json()

    # Los casos son de Buenos Aires: un usuario de Salta no los ve.
    assert api["total_casos"] == 0
    assert api["es_usuario_provincial"] is True
