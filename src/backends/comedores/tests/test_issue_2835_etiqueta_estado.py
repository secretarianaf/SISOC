"""Etiqueta de estado del legajo con la combinación Inactivo / En ejecución (#2835)."""

import pytest

from comedores.models import (
    Comedor,
    EstadoActividad,
    EstadoGeneral,
    EstadoHistorial,
    EstadoProceso,
)


def _comedor_con_estado(actividad_nombre, proceso_nombre):
    actividad, _ = EstadoActividad.objects.get_or_create(estado=actividad_nombre)
    proceso = EstadoProceso.objects.create(
        estado=proceso_nombre, estado_actividad=actividad
    )
    estado_general = EstadoGeneral.objects.create(
        estado_actividad=actividad, estado_proceso=proceso
    )
    comedor = Comedor.objects.create(nombre="Comedor 2835")
    historial = EstadoHistorial.objects.create(
        comedor=comedor, estado_general=estado_general
    )
    comedor.ultimo_estado = historial
    comedor.save(update_fields=["ultimo_estado"])
    return comedor, historial


@pytest.mark.django_db
def test_combinacion_inactivo_en_ejecucion_muestra_estado_general():
    comedor, historial = _comedor_con_estado("Inactivo", "En ejecución")

    assert comedor.get_etiqueta_estado_display() == "Inactivo"
    # No se toca el estado registrado.
    historial.refresh_from_db()
    assert historial.estado_general.estado_proceso.estado == "En ejecución"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("actividad", "proceso"),
    [
        ("Activo", "En ejecución"),
        ("Inactivo", "Baja"),
        ("Activo", "En proceso de alta"),
    ],
)
def test_otras_combinaciones_muestran_el_subestado(actividad, proceso):
    comedor, _ = _comedor_con_estado(actividad, proceso)

    assert comedor.get_etiqueta_estado_display() == proceso


@pytest.mark.django_db
def test_sin_estado_muestra_sin_proceso():
    comedor = Comedor.objects.create(nombre="Comedor sin estado")

    assert comedor.get_etiqueta_estado_display() == "Sin proceso"
