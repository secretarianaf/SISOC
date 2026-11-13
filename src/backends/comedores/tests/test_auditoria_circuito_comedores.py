"""Issue #2791: admisión, informe técnico, dupla y comunicados en la auditoría."""

from auditlog.models import LogEntry
from django.contrib.auth.models import User
import pytest

from admisiones.models.admisiones import Admision, InformeTecnico, TipoConvenio
from comedores.models import Comedor
from comunicados.models import Comunicado
from duplas.models import Dupla

pytestmark = pytest.mark.django_db


@pytest.fixture(name="admision")
def admision_fixture():
    return Admision.objects.create(
        comedor=Comedor.objects.create(nombre="Comedor auditado"),
        tipo_convenio=TipoConvenio.objects.create(nombre="Convenio auditado"),
        tipo="renovacion",
    )


def _ultimo_cambio(obj):
    """`changes` del último evento: {campo: [viejo, nuevo]}."""
    return LogEntry.objects.get_for_object(obj).first().changes


def test_cambio_de_la_admision_queda_auditado_sin_snapshot(admision):
    admision.num_expediente = "EX-2026-99"
    admision.datos_organizacion_snapshot = {"cuit": "30111222333"}
    admision.save()

    cambios = _ultimo_cambio(admision)
    assert cambios["num_expediente"] == ["None", "EX-2026-99"]
    assert "datos_organizacion_snapshot" not in cambios
    assert "modificado" not in cambios


def test_informe_tecnico_registra_su_avance_sin_datos_personales(admision):
    informe = InformeTecnico.objects.create(
        admision=admision,
        tipo="base",
        estado="Iniciado",
        estado_formulario="borrador",
        representante_dni="20111222",
    )

    informe.estado = "Para revision"
    informe.representante_dni = "20333444"
    informe.responsable_tarjeta_dni = "27555666"
    informe.save()

    entradas = LogEntry.objects.get_for_object(informe)
    assert entradas.first().changes == {"estado": ["Iniciado", "Para revision"]}
    for entrada in entradas:
        assert "representante_dni" not in entrada.changes
        assert "responsable_tarjeta_dni" not in entrada.changes


def test_cambios_de_dupla_y_comunicado_quedan_auditados():
    abogado = User.objects.create_user("abogado-auditoria", password="x")
    dupla = Dupla.objects.create(nombre="Dupla 1", estado="Activo", abogado=abogado)
    dupla.estado = "Inactivo"
    dupla.save()
    comunicado = Comunicado.objects.create(
        titulo="Aviso", cuerpo="Texto", usuario_creador=abogado
    )
    estado_inicial = comunicado.estado
    comunicado.estado = "publicado"
    comunicado.save()

    assert _ultimo_cambio(dupla) == {"estado": ["Activo", "Inactivo"]}
    assert _ultimo_cambio(comunicado)["estado"] == [estado_inicial, "publicado"]
