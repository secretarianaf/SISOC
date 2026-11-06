"""Issue #2791: los modelos críticos de Celiaquía quedan en el log de auditoría."""

from auditlog.models import LogEntry
from django.contrib.auth.models import User
import pytest

from celiaquia.models import (
    AsignacionTecnico,
    EstadoExpediente,
    EstadoLegajo,
    Expediente,
    ExpedienteCiudadano,
    ProvinciaCupo,
    RevisionTecnico,
)
from ciudadanos.models import Ciudadano
from core.models import Provincia

pytestmark = pytest.mark.django_db


@pytest.fixture(name="usuario")
def usuario_fixture():
    return User.objects.create_user("auditoria-celiaquia", password="x")


@pytest.fixture(name="expediente")
def expediente_fixture(usuario):
    return Expediente.objects.create(
        usuario_provincia=usuario,
        estado=EstadoExpediente.objects.get_or_create(nombre="EN_ESPERA")[0],
    )


def _legajo(expediente):
    ciudadano = Ciudadano.objects.create(
        apellido="Ape", nombre="Nom", documento=72000001
    )
    return ExpedienteCiudadano.objects.create(
        expediente=expediente,
        ciudadano=ciudadano,
        estado=EstadoLegajo.objects.get_or_create(nombre="VALIDO")[0],
    )


def _ultimo_cambio(obj):
    """`changes` del último evento: {campo: [viejo, nuevo]}."""
    return LogEntry.objects.get_for_object(obj).first().changes


def test_revision_tecnica_del_legajo_queda_auditada_sin_texto_libre(expediente):
    legajo = _legajo(expediente)

    legajo.revision_tecnico = RevisionTecnico.SUBSANAR
    legajo.subsanacion_motivo = "Diagnóstico ilegible del hospital X"
    legajo.observacion_cruce = "Dato sensible del cruce"
    legajo.save()

    entradas = LogEntry.objects.get_for_object(legajo)
    assert entradas.count() == 2  # alta + modificación
    assert entradas.first().changes["revision_tecnico"] == ["PENDIENTE", "SUBSANAR"]
    # Ni texto libre, ni archivos, ni timestamps en ningún evento.
    for entrada in entradas:
        for campo in (
            "subsanacion_motivo",
            "observacion_cruce",
            "archivo1",
            "modificado_en",
        ):
            assert campo not in entrada.changes


def test_cambio_de_estado_del_expediente_queda_auditado(expediente):
    expediente.estado = EstadoExpediente.objects.get_or_create(
        nombre="CRUCE_FINALIZADO"
    )[0]
    expediente.observaciones = "Texto libre"
    expediente.save()

    cambios = _ultimo_cambio(expediente)
    assert list(cambios) == ["estado"]


def test_cupo_provincial_y_asignacion_de_tecnico_quedan_auditados(expediente, usuario):
    cupo = ProvinciaCupo.objects.create(
        provincia=Provincia.objects.create(nombre="Auditada"), total_asignado=10
    )
    cupo.total_asignado = 25
    cupo.save()
    asignacion = AsignacionTecnico.objects.create(
        expediente=expediente, tecnico=usuario
    )

    assert _ultimo_cambio(cupo)["total_asignado"] == ["10", "25"]
    assert (
        LogEntry.objects.get_for_object(asignacion)
        .filter(action=LogEntry.Action.CREATE)
        .exists()
    )
