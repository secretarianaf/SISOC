"""#2797: editar el comedor no cambia lo que muestra un relevamiento finalizado."""

import importlib

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse

from comedores.models import Comedor, Referente
from core.models import Localidad, Municipio, Provincia
from relevamientos.models import Relevamiento
from relevamientos.services.datos_comedor_snapshot import armar_snapshot

pytestmark = pytest.mark.django_db


@pytest.fixture
def comedor():
    provincia = Provincia.objects.create(nombre="Prov 2797")
    municipio = Municipio.objects.create(nombre="Muni 2797", provincia=provincia)
    localidad = Localidad.objects.create(nombre="Loc 2797", municipio=municipio)
    referente = Referente.objects.create(
        nombre="Ana", apellido="Vieja", documento=11111111
    )
    return Comedor.objects.create(
        nombre="Nombre viejo",
        calle="Calle vieja",
        numero=10,
        comienzo=2015,
        provincia=provincia,
        municipio=municipio,
        localidad=localidad,
        referente=referente,
    )


def _editar_comedor(comedor):
    comedor.nombre = "Nombre nuevo"
    comedor.calle = "Calle nueva"
    comedor.save()
    comedor.referente.nombre = "Beatriz"
    comedor.referente.save()


def test_armar_snapshot_devuelve_datos_planos(comedor):
    datos = armar_snapshot(comedor, comedor.referente)

    assert datos["nombre"] == "Nombre viejo"
    assert datos["provincia"] == "Prov 2797"
    assert datos["localidad"] == "Loc 2797"
    assert datos["programa"] is None
    assert datos["referente"]["nombre"] == "Ana"
    assert datos["responsable"]["documento"] == 11111111


def test_finalizar_congela_los_datos_del_comedor(comedor):
    relevamiento = Relevamiento.objects.create(comedor=comedor, estado="Finalizado")
    _editar_comedor(comedor)

    relevamiento = Relevamiento.objects.get(pk=relevamiento.pk)

    assert relevamiento.datos_comedor["nombre"] == "Nombre viejo"
    assert relevamiento.datos_comedor["calle"] == "Calle vieja"
    assert relevamiento.datos_comedor["referente"]["nombre"] == "Ana"


def test_pendiente_muestra_los_datos_vivos_del_comedor(comedor):
    relevamiento = Relevamiento.objects.create(
        comedor=comedor, estado="Visita pendiente"
    )
    _editar_comedor(comedor)

    relevamiento = Relevamiento.objects.get(pk=relevamiento.pk)

    assert relevamiento.datos_comedor_snapshot is None
    assert relevamiento.datos_comedor["nombre"] == "Nombre nuevo"
    assert relevamiento.datos_comedor["referente"]["nombre"] == "Beatriz"


def test_al_pasar_a_finalizado_captura_lo_cargado_en_ese_momento(comedor):
    relevamiento = Relevamiento.objects.create(
        comedor=comedor, estado="Visita pendiente"
    )
    _editar_comedor(comedor)

    relevamiento = Relevamiento.objects.get(pk=relevamiento.pk)
    relevamiento.estado = "Finalizado"
    relevamiento.save()

    assert relevamiento.datos_comedor_snapshot["nombre"] == "Nombre nuevo"


def test_finalizado_no_reasigna_responsable_al_nuevo_referente(comedor):
    relevamiento = Relevamiento.objects.create(comedor=comedor, estado="Finalizado")
    responsable_original = relevamiento.responsable_relevamiento_id
    otro = Referente.objects.create(nombre="Otro", documento=22222222)
    comedor.referente = otro
    comedor.save()

    relevamiento = Relevamiento.objects.get(pk=relevamiento.pk)
    relevamiento.observacion = "se guarda de nuevo"
    relevamiento.save()

    assert relevamiento.responsable_relevamiento_id == responsable_original
    assert relevamiento.responsable_relevamiento_id != otro.pk


def test_pendiente_sigue_sincronizando_el_responsable(comedor):
    relevamiento = Relevamiento.objects.create(
        comedor=comedor, estado="Visita pendiente"
    )
    otro = Referente.objects.create(nombre="Otro", documento=22222222)
    comedor.referente = otro
    comedor.save()

    relevamiento = Relevamiento.objects.get(pk=relevamiento.pk)
    relevamiento.save()

    assert relevamiento.responsable_relevamiento_id == otro.pk


def test_detalle_de_finalizado_muestra_datos_congelados(client, comedor):
    user = get_user_model().objects.create_user(username="u2797", password="x")
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="relevamientos", codename="view_relevamiento"
        )
    )
    client.force_login(user)
    relevamiento = Relevamiento.objects.create(comedor=comedor, estado="Finalizado")
    _editar_comedor(comedor)

    respuesta = client.get(
        reverse("relevamiento_detalle", args=[comedor.pk, relevamiento.pk])
    )

    contenido = respuesta.content.decode()
    assert "Nombre viejo" in contenido
    assert "Calle vieja" in contenido
    assert "Loc 2797" in contenido
    assert "Calle nueva" not in contenido


def test_backfill_completa_solo_finalizados_sin_snapshot(comedor):
    migracion = importlib.import_module(
        "relevamientos.migrations.0024_relevamiento_datos_comedor_snapshot"
    )
    finalizado = Relevamiento.objects.create(comedor=comedor, estado="Finalizado")
    pendiente = Relevamiento.objects.create(comedor=comedor, estado="Visita pendiente")
    Relevamiento.objects.filter(pk=finalizado.pk).update(datos_comedor_snapshot=None)

    migracion.completar_snapshot_de_finalizados(apps, None)

    finalizado.refresh_from_db()
    pendiente.refresh_from_db()
    assert finalizado.datos_comedor_snapshot["nombre"] == "Nombre viejo"
    assert finalizado.datos_comedor_snapshot["provincia"] == "Prov 2797"
    assert pendiente.datos_comedor_snapshot is None
