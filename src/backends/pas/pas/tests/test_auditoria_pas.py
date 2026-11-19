"""Issue #2791: los modelos críticos de PAS quedan en el log de auditoría."""

from datetime import date

from auditlog.models import LogEntry
from django.utils import timezone
import pytest

from core.models import Municipio, Provincia
from pas.models import (
    PasCircuitoMensual,
    PasEstado,
    PasIncompatibilidad,
    PasInvitacionDDJJ,
    PasPersona,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(name="persona")
def persona_fixture():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    return PasPersona.objects.create(
        id_persona=9001,
        apellidos="Garcia",
        nombres="Maria",
        dni=30111222,
        provincia=provincia,
        municipio=Municipio.objects.create(nombre="La Plata", provincia=provincia),
        estado=PasEstado.objects.create(nombre="Activo"),
        telefono_celular="1100000000",
    )


def _ultimo_cambio(obj):
    """`changes` del último evento: {campo: [viejo, nuevo]}."""
    return LogEntry.objects.get_for_object(obj).first().changes


def test_cambio_de_estado_y_contacto_de_la_persona_queda_auditado(persona):
    estado_anterior = persona.estado
    persona.estado = PasEstado.objects.create(nombre="Suspendido")
    persona.telefono_celular = "1199999999"
    persona.save()

    cambios = _ultimo_cambio(persona)
    assert cambios["estado"] == [str(estado_anterior.pk), str(persona.estado.pk)]
    assert cambios["telefono_celular"] == ["1100000000", "1199999999"]
    assert "fecha_actualizacion" not in cambios


def test_gestion_de_incompatibilidad_queda_auditada(persona):
    incompatibilidad = PasIncompatibilidad.objects.create(
        persona=persona,
        categoria=PasIncompatibilidad.Categoria.SUPERVIVENCIA,
        periodo_impacto=date(2026, 12, 1),
        detalle="Fallecimiento informado por RENAPER",
    )

    incompatibilidad.estado = PasIncompatibilidad.Estado.GESTIONADA
    incompatibilidad.save(update_fields=["estado"])

    cambios = _ultimo_cambio(incompatibilidad)
    assert cambios == {"estado": ["pendiente", "gestionada"]}


def test_circuito_mensual_queda_auditado():
    circuito = PasCircuitoMensual.objects.create(periodo=date(2026, 11, 1))

    circuito.fecha_importacion_sintys = timezone.now()
    circuito.save()

    assert "fecha_importacion_sintys" in _ultimo_cambio(circuito)


def test_la_invitacion_ddjj_no_se_audita_porque_su_token_es_secreto(persona):
    invitacion = PasInvitacionDDJJ.objects.create(persona=persona)

    assert not LogEntry.objects.get_for_object(invitacion).exists()
