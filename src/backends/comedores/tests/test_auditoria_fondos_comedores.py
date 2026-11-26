"""Issue #2791: pagos y rendiciones de comedores quedan en el log de auditoría."""

from decimal import Decimal

from auditlog.models import LogEntry
from django.utils import timezone
import pytest

from comedores.models import Comedor
from expedientespagos.models import ExpedientePago
from rendicioncuentasfinal.models import RendicionCuentasFinal
from rendicioncuentasmensual.models import DocumentacionAdjunta, RendicionCuentaMensual

pytestmark = pytest.mark.django_db


@pytest.fixture(name="comedor")
def comedor_fixture():
    return Comedor.objects.create(nombre="Comedor auditado")


def _ultimo_cambio(obj):
    """`changes` del último evento: {campo: [viejo, nuevo]}."""
    return LogEntry.objects.get_for_object(obj).first().changes


def test_cambio_de_montos_del_expediente_de_pago_queda_auditado(comedor):
    pago = ExpedientePago.objects.create(
        comedor=comedor,
        expediente_convenio="EX-2026-1",
        prestaciones_mensuales_desayuno=10,
        prestaciones_mensuales_almuerzo=10,
        prestaciones_mensuales_merienda=10,
        prestaciones_mensuales_cena=10,
        monto_mensual_desayuno=Decimal("100.00"),
        monto_mensual_almuerzo=Decimal("100.00"),
        monto_mensual_merienda=Decimal("100.00"),
        monto_mensual_cena=Decimal("100.00"),
    )

    pago.monto_mensual_almuerzo = Decimal("150.00")
    pago.numero_orden_pago = "OP-77"
    pago.save()

    cambios = _ultimo_cambio(pago)
    assert cambios["monto_mensual_almuerzo"] == ["100.00", "150.00"]
    assert cambios["numero_orden_pago"] == ["None", "OP-77"]


def test_revision_de_rendicion_y_documento_queda_auditada_sin_ruido(comedor):
    rendicion = RendicionCuentaMensual.objects.create(comedor=comedor, mes=1, anio=2026)
    documento = DocumentacionAdjunta.objects.create(
        nombre="Comprobante",
        archivo="rendiciones/comprobante.pdf",
        rendicion_cuenta_mensual=rendicion,
    )

    rendicion.estado = RendicionCuentaMensual.ESTADO_REVISION
    rendicion.save()
    documento.estado = DocumentacionAdjunta.ESTADO_SUBSANAR
    documento.save()
    # Abrir el documento no es un cambio que interese auditar.
    documento.visualizacion_fecha = timezone.now()
    documento.save()

    assert _ultimo_cambio(rendicion) == {"estado": ["elaboracion", "revision"]}
    entradas_documento = LogEntry.objects.get_for_object(documento)
    assert entradas_documento.count() == 2  # alta + cambio de estado
    assert entradas_documento.first().changes == {"estado": ["presentado", "subsanar"]}


def test_rendicion_final_presentada_queda_auditada(comedor):
    rendicion = RendicionCuentasFinal.objects.create(comedor=comedor)

    rendicion.fisicamente_presentada = True
    rendicion.save()

    assert _ultimo_cambio(rendicion) == {"fisicamente_presentada": ["False", "True"]}
