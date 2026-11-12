"""Issue #2791: los modelos críticos de VAT quedan en el log de auditoría."""

from datetime import date, timedelta

from auditlog.models import LogEntry
import pytest

from VAT.models import (
    ActaCierreComision,
    Centro,
    ComisionCurso,
    Curso,
    Inscripcion,
    InstitucionUbicacion,
    ModalidadCursada,
    ProfesorCentro,
    Voucher,
    VoucherParametria,
)
from ciudadanos.models import Ciudadano
from core.models import Localidad, Municipio, Programa, Provincia

pytestmark = pytest.mark.django_db


@pytest.fixture(name="centro")
def centro_fixture():
    provincia = Provincia.objects.create(nombre="Chaco")
    municipio = Municipio.objects.create(nombre="Resistencia", provincia=provincia)
    localidad = Localidad.objects.create(nombre="Centro", municipio=municipio)
    return Centro.objects.create(
        nombre="CFP Auditado",
        codigo="CFP-AUD",
        provincia=provincia,
        municipio=municipio,
        localidad=localidad,
        domicilio_actividad="Calle 1",
        telefono="3620000",
        celular="3620001",
        correo="cfp@vat.test",
        nombre_referente="Ref",
        apellido_referente="Erente",
        telefono_referente="3620002",
        correo_referente="ref@vat.test",
    )


@pytest.fixture(name="comision_curso")
def comision_curso_fixture(centro):
    ubicacion = InstitucionUbicacion.objects.create(
        centro=centro,
        localidad=centro.localidad,
        rol_ubicacion="sede_principal",
        domicilio="Calle 1",
        es_principal=True,
    )
    curso = Curso.objects.create(
        centro=centro,
        nombre="Soldadura",
        modalidad=ModalidadCursada.objects.create(nombre="Presencial", activo=True),
        estado="activo",
    )
    return ComisionCurso.objects.create(
        curso=curso,
        ubicacion=ubicacion,
        codigo_comision="COM-AUD",
        nombre="Comisión auditada",
        cupo_total=10,
        fecha_inicio=date(2026, 4, 1),
        fecha_fin=date(2026, 12, 30),
        estado="activa",
    )


def _ciudadano(documento):
    return Ciudadano.objects.create(
        apellido=f"Ape{documento}",
        nombre=f"Nom{documento}",
        fecha_nacimiento=date(2000, 1, 1),
        documento=documento,
    )


def _ultimo_cambio(obj):
    """`changes` del último evento: {campo: [viejo, nuevo]}."""
    return LogEntry.objects.get_for_object(obj).first().changes


def test_cambio_de_estado_de_inscripcion_queda_auditado(comision_curso):
    inscripcion = Inscripcion.objects.create(
        ciudadano=_ciudadano(71000001),
        comision_curso=comision_curso,
        observaciones="Dato personal en texto libre",
    )

    inscripcion.estado = "inscripta"
    inscripcion.resultado_final = Inscripcion.RESULTADO_APROBADO
    inscripcion.observaciones = "Otro dato personal"
    inscripcion.save()

    entradas = LogEntry.objects.get_for_object(inscripcion)
    assert entradas.count() == 2  # alta + modificación
    cambios = entradas.first().changes
    assert cambios["estado"] == ["pre_inscripta", "inscripta"]
    assert cambios["resultado_final"] == ["None", "aprobado"]
    # Texto libre y timestamps automáticos no entran al log en ningún evento.
    for entrada in entradas:
        assert "observaciones" not in entrada.changes
        assert "fecha_modificacion" not in entrada.changes


def test_cambio_de_creditos_de_voucher_queda_auditado(superuser):
    programa = Programa.objects.create(nombre="VAT auditoría")
    parametria = VoucherParametria.objects.create(
        nombre="Plantilla",
        programa=programa,
        cantidad_inicial=10,
        fecha_vencimiento=date.today() + timedelta(days=90),
        creado_por=superuser,
    )
    voucher = Voucher.objects.create(
        parametria=parametria,
        ciudadano=_ciudadano(71000002),
        programa=programa,
        cantidad_inicial=10,
        cantidad_disponible=10,
        fecha_vencimiento=date.today() + timedelta(days=90),
    )

    voucher.cantidad_disponible = 4
    voucher.cantidad_usada = 6
    voucher.save()
    parametria.cantidad_inicial = 20
    parametria.save()

    cambios_voucher = _ultimo_cambio(voucher)
    assert cambios_voucher["cantidad_disponible"] == ["10", "4"]
    assert cambios_voucher["cantidad_usada"] == ["0", "6"]
    assert "fecha_modificacion" not in cambios_voucher
    assert _ultimo_cambio(parametria)["cantidad_inicial"] == ["10", "20"]


def test_cambios_de_centro_y_acta_de_cierre_quedan_auditados(
    centro, comision_curso, superuser
):
    centro.correo = "nuevo@vat.test"
    centro.save()
    profesor = ProfesorCentro.objects.create(
        centro=centro,
        apellido="Docente",
        nombre="Ana",
        documento=30111222,
        email="ana@vat.test",
    )
    acta = ActaCierreComision.objects.create(
        comision_curso=comision_curso,
        profesor=profesor,
        fecha_fin=date(2026, 12, 30),
        numero_acta="A-1",
        registrado_por=superuser,
    )

    acta.numero_acta = "A-2"
    acta.save()

    assert _ultimo_cambio(centro)["correo"] == ["cfp@vat.test", "nuevo@vat.test"]
    assert _ultimo_cambio(acta)["numero_acta"] == ["A-1", "A-2"]
    # El profesor no está en la lista auditada: no genera eventos.
    assert not LogEntry.objects.get_for_object(profesor).exists()
