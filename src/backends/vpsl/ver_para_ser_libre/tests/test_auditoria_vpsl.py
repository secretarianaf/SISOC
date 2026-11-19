"""Issue #2791: los modelos críticos de VPSL quedan en el log de auditoría."""

from auditlog.models import LogEntry
import pytest

from ver_para_ser_libre.models import (
    EstadoItinerario,
    EstadoJornada,
    EstadoRegistroNominal,
    RegistroNominalVPSL,
    ResultadoAtencion,
)
from ver_para_ser_libre.tests.test_workflow import crear_itinerario, crear_jornada

pytestmark = pytest.mark.django_db


def _ultimo_cambio(obj):
    """`changes` del último evento: {campo: [viejo, nuevo]}."""
    return LogEntry.objects.get_for_object(obj).first().changes


def test_cambio_de_estado_de_itinerario_y_jornada_queda_auditado():
    itinerario = crear_itinerario()
    estado_inicial = itinerario.estado
    itinerario.estado = EstadoItinerario.PRESENTADO
    itinerario.save()
    jornada = crear_jornada(itinerario=itinerario)
    jornada.estado = EstadoJornada.HABILITADA
    jornada.referente_datos_renaper = {"nombre": "Dato crudo de RENAPER"}
    jornada.save()

    assert _ultimo_cambio(itinerario)["estado"] == [estado_inicial, "presentado"]
    cambios_jornada = _ultimo_cambio(jornada)
    assert cambios_jornada["estado"][1] == "habilitada"
    assert "referente_datos_renaper" not in cambios_jornada
    assert "updated_at" not in cambios_jornada


def test_registro_nominal_audita_el_circuito_sin_datos_de_salud():
    registro = RegistroNominalVPSL.objects.create(
        jornada=crear_jornada(),
        dni="45111222",
        nombre="Nombre",
        apellido="Apellido",
        numero_acta="A-1",
        resultado=ResultadoAtencion.NO_REQUIERE,
        prescripcion="Prescripción del oftalmólogo",
    )

    registro.estado = EstadoRegistroNominal.VALIDADO
    registro.resultado = ResultadoAtencion.DERIVADO
    registro.prescripcion = "Otra prescripción"
    registro.telefono = "1100000000"
    registro.save()

    entradas = LogEntry.objects.get_for_object(registro)
    assert entradas.count() == 2  # alta + modificación
    assert all(
        entry.object_repr == f"Registro nominal VPSL #{registro.pk}"
        for entry in entradas
    )
    assert entradas.first().changes == {"estado": ["cargado", "validado"]}
    # El alta tampoco lleva datos personales ni de salud.
    alta = entradas.last().changes
    for campo in ("dni", "nombre", "resultado", "prescripcion", "telefono"):
        assert campo not in alta
