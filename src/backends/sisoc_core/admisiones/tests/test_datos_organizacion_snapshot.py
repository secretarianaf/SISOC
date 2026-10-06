"""Issue #2571: los datos de la organizacion del informe tecnico respetan la
opcion elegida en el modal de resincronizacion de la admision."""

import pytest

from admisiones.forms.admisiones_forms import InformeTecnicoBaseForm
from admisiones.models.admisiones import Admision
from admisiones.services import datos_organizacion_snapshot
from admisiones.services.admisiones_service import AdmisionService
from admisiones.tests.test_informe_tecnico_docx_workflow import crear_informe_tecnico
from comedores.models import Comedor
from organizaciones.models import Organizacion


pytestmark = pytest.mark.django_db


@pytest.fixture
def admision():
    organizacion = Organizacion.objects.create(
        nombre="Org Original", cuit=20111111112, domicilio="Calle Vieja 1"
    )
    comedor = Comedor.objects.create(nombre="Comedor", organizacion=organizacion)
    admision = Admision.objects.create(comedor=comedor)
    # Primera visita a la admision: queda la linea de base.
    assert (
        datos_organizacion_snapshot.datos_organizacion_desactualizados(admision)
        is False
    )
    return admision


@pytest.fixture
def organizacion_nueva():
    return Organizacion.objects.create(
        nombre="Org Nueva", cuit=30222222223, domicilio="Calle Nueva 2"
    )


def _cambiar_organizacion(admision, organizacion):
    comedor = Comedor.objects.get(pk=admision.comedor_id)
    comedor.organizacion = organizacion
    comedor.save()
    return Admision.objects.select_related("comedor__organizacion").get(pk=admision.pk)


def test_cambio_de_organizacion_marca_datos_desactualizados(
    admision, organizacion_nueva
):
    admision = _cambiar_organizacion(admision, organizacion_nueva)

    assert datos_organizacion_snapshot.datos_organizacion_desactualizados(admision)


def test_continuar_conserva_datos_de_la_organizacion_anterior(
    admision, organizacion_nueva
):
    admision = _cambiar_organizacion(admision, organizacion_nueva)

    ok, _ = AdmisionService.aceptar_desincronizacion_admision(admision)

    assert ok
    admision.refresh_from_db()
    assert not datos_organizacion_snapshot.datos_organizacion_desactualizados(admision)
    form = InformeTecnicoBaseForm(admision=admision)
    assert form.fields["nombre_organizacion"].initial == "Org Original"
    assert form.fields["cuit_organizacion"].initial == "20111111112"
    assert form.fields["domicilio_organizacion"].initial == "Calle Vieja 1"


def test_snapshot_se_congela_aunque_la_admision_no_se_haya_visitado(
    organizacion_nueva,
):
    organizacion = Organizacion.objects.create(nombre="Org Legacy")
    comedor = Comedor.objects.create(nombre="Comedor", organizacion=organizacion)
    admision = Admision.objects.create(comedor=comedor)
    assert admision.datos_organizacion_snapshot is None

    admision = _cambiar_organizacion(admision, organizacion_nueva)
    AdmisionService.aceptar_desincronizacion_admision(admision)

    form = InformeTecnicoBaseForm(admision=admision)
    assert form.fields["nombre_organizacion"].initial == "Org Legacy"


def test_actualizar_toma_datos_nuevos_y_actualiza_informes_no_validados(
    admision, organizacion_nueva
):
    informe = crear_informe_tecnico(admision, nombre_organizacion="Org Original")
    validado = crear_informe_tecnico(
        admision, nombre_organizacion="Org Original", estado="Validado"
    )
    admision = _cambiar_organizacion(admision, organizacion_nueva)

    ok, _ = AdmisionService.actualizar_documentacion_desde_organizacion(admision)

    assert ok
    admision.refresh_from_db()
    assert not datos_organizacion_snapshot.datos_organizacion_desactualizados(admision)
    informe.refresh_from_db()
    validado.refresh_from_db()
    assert informe.nombre_organizacion == "Org Nueva"
    assert informe.cuit_organizacion == "30222222223"
    assert validado.nombre_organizacion == "Org Original"
    form = InformeTecnicoBaseForm(admision=admision)
    assert form.fields["nombre_organizacion"].initial == "Org Nueva"


def test_edicion_de_datos_de_la_organizacion_dispara_desactualizacion(admision):
    organizacion = admision.comedor.organizacion
    organizacion.nombre = "Org Renombrada"
    organizacion.save()
    admision = Admision.objects.select_related("comedor__organizacion").get(
        pk=admision.pk
    )

    assert datos_organizacion_snapshot.datos_organizacion_desactualizados(admision)
    AdmisionService.aceptar_desincronizacion_admision(admision)
    form = InformeTecnicoBaseForm(admision=admision)
    assert form.fields["nombre_organizacion"].initial == "Org Original"


def test_informe_guardado_conserva_sus_datos_de_organizacion(admision):
    informe = crear_informe_tecnico(admision, nombre_organizacion="Valor guardado")

    form = InformeTecnicoBaseForm(instance=informe, admision=admision)

    assert form["nombre_organizacion"].value() == "Valor guardado"
