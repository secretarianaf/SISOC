"""Regresiones de rendiciones y actividades de Abordaje Comunitario (#2683)."""

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from comedores.forms.actividad_espacio_pwa_form import ActividadEspacioPWAWebForm
from core.models import Dia
from pwa.models import ActividadEspacioPWA, CatalogoActividadPWA
from rendicioncuentasmensual.models import DocumentacionAdjunta, RendicionCuentaMensual
from rendicioncuentasmensual.services import RendicionCuentaMensualService
from tests.test_rendicioncuentasmensual_domain_rules import (
    scopes,
)  # pylint: disable=unused-import
from tests.test_pwa_rendicion_edicion_api import _crear_rendicion


@pytest.mark.django_db
@pytest.mark.parametrize(
    "categoria", ["formulario_ii", "comprobantes_alimentario", "planilla_seguros"]
)
def test_subsanacion_conserva_observacion_hasta_nueva_revision(scopes, categoria):
    comedor, proyecto, _, _ = scopes
    rendicion = _crear_rendicion(
        comedor,
        proyecto=proyecto,
        estado=RendicionCuentaMensual.ESTADO_SUBSANAR,
        etapa_proceso=RendicionCuentaMensual.ETAPA_REVISION_DOCUMENTACION,
        subestado_proceso=RendicionCuentaMensual.SUBESTADO_PENDIENTE_CORRECCIONES,
    )
    observado = DocumentacionAdjunta.objects.create(
        rendicion_cuenta_mensual=rendicion,
        categoria=categoria,
        archivo="observado.pdf",
        nombre="Observado",
        estado="subsanar",
        observaciones="Debe incluir la firma",
    )
    nuevo = RendicionCuentaMensualService.adjuntar_documentacion_mobile(
        rendicion=rendicion,
        categoria=categoria,
        documento_data={
            "archivo": SimpleUploadedFile("nuevo.pdf", b"contenido"),
            "nombre": "Nuevo",
        },
        documento_subsanado_id=observado.pk,
    )
    assert nuevo.observaciones == "Debe incluir la firma"
    RendicionCuentaMensualService.presentar_rendicion_mobile(rendicion)
    assert rendicion.subestado_proceso == RendicionCuentaMensual.SUBESTADO_SUBSANADO
    detalle = RendicionCuentaMensualService.obtener_documentacion_para_detalle(
        rendicion
    )
    archivos = [archivo for grupo in detalle for archivo in grupo["archivos"]]
    assert (
        next(archivo for archivo in archivos if archivo.pk == nuevo.pk).observaciones
        == "Debe incluir la firma"
    )
    RendicionCuentaMensualService.actualizar_estado_documento_revision(
        documento=nuevo,
        estado=DocumentacionAdjunta.ESTADO_VALIDADO,
    )
    nuevo.refresh_from_db()
    assert nuevo.observaciones is None


@pytest.mark.django_db
def test_planilla_seguros_admite_varios_archivos_sin_reemplazarlos(scopes):
    comedor, proyecto, _, _ = scopes
    rendicion = _crear_rendicion(comedor, proyecto=proyecto)
    for index in range(2):
        RendicionCuentaMensualService.adjuntar_documentacion_mobile(
            rendicion=rendicion,
            categoria="planilla_seguros",
            documento_data={
                "archivo": SimpleUploadedFile(f"seguro-{index}.pdf", b"contenido"),
                "nombre": f"Seguro {index}",
            },
        )
    assert rendicion.archivos_adjuntos.filter(categoria="planilla_seguros").count() == 2
    categoria = next(
        item
        for item in DocumentacionAdjunta.categorias_mobile("tradicional")
        if item["codigo"] == "planilla_seguros"
    )
    assert categoria["label"] == "Planilla de Seguros II"
    assert categoria["multiple"] is True


@pytest.mark.django_db
def test_subsanar_planilla_seguros_exige_indicar_el_documento_observado(scopes):
    """Contrato con mobile: sin documento_subsanado_id el archivo se suma y no
    reemplaza al observado, que sigue bloqueando la presentación."""
    comedor, proyecto, _, _ = scopes
    rendicion = _crear_rendicion(
        comedor,
        proyecto=proyecto,
        estado=RendicionCuentaMensual.ESTADO_SUBSANAR,
        etapa_proceso=RendicionCuentaMensual.ETAPA_REVISION_DOCUMENTACION,
        subestado_proceso=RendicionCuentaMensual.SUBESTADO_PENDIENTE_CORRECCIONES,
    )
    observado = DocumentacionAdjunta.objects.create(
        rendicion_cuenta_mensual=rendicion,
        categoria="planilla_seguros",
        archivo="observado.pdf",
        nombre="Observado",
        estado="subsanar",
        observaciones="Debe incluir la firma",
    )
    nuevo = RendicionCuentaMensualService.adjuntar_documentacion_mobile(
        rendicion=rendicion,
        categoria="planilla_seguros",
        documento_data={
            "archivo": SimpleUploadedFile("nuevo.pdf", b"contenido"),
            "nombre": "Nuevo",
        },
    )
    assert nuevo.documento_subsanado_id is None
    observado.refresh_from_db()
    assert observado.estado == DocumentacionAdjunta.ESTADO_SUBSANAR
    with pytest.raises(ValidationError):
        RendicionCuentaMensualService.presentar_rendicion_mobile(rendicion)


@pytest.mark.django_db
def test_actividades_separan_categoria_y_nombre_y_conservan_catalogo_existente(scopes):
    comedor, _, _, _ = scopes
    CatalogoActividadPWA.objects.all().delete()
    catalogo = CatalogoActividadPWA.objects.create(
        categoria="Salud", actividad="Yoga", activo=False
    )
    CatalogoActividadPWA.objects.create(categoria="Arte", actividad="Dibujo")
    CatalogoActividadPWA.objects.create(
        categoria="Ámbito comunitario", actividad="Huerta"
    )
    dia, _ = Dia.objects.get_or_create(nombre="Lunes")
    actividad = ActividadEspacioPWA.objects.create(
        comedor=comedor,
        catalogo_actividad=catalogo,
        dia_actividad=dia,
        horario_actividad="10:00 a 11:00",
    )
    form = ActividadEspacioPWAWebForm(instance=actividad, comedor=comedor)
    assert form.initial["categoria"] == "Salud"
    assert list(form.fields["categoria"].choices) == [
        ("", "Seleccionar"),
        ("Ámbito comunitario", "Ámbito comunitario"),
        ("Arte", "Arte"),
        ("Salud", "Salud"),
    ]
    assert form.fields["catalogo_actividad"].label_from_instance(catalogo) == "Yoga"
    assert catalogo in form.fields["catalogo_actividad"].queryset
    actividad.refresh_from_db()
    assert actividad.catalogo_actividad_id == catalogo.pk


@pytest.mark.django_db
def test_actividad_rechaza_categoria_ajena(scopes):
    comedor, _, _, _ = scopes
    catalogo = CatalogoActividadPWA.objects.create(categoria="Salud", actividad="Yoga")
    CatalogoActividadPWA.objects.create(categoria="Arte", actividad="Dibujo")
    form = ActividadEspacioPWAWebForm(
        data={"categoria": "Arte", "catalogo_actividad": catalogo.pk}, comedor=comedor
    )
    assert not form.is_valid()
    assert "catalogo_actividad" in form.errors


@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", ["", "detalle"])
def test_usuario_con_acceso_comedor_sin_permiso_rendicion_no_puede_consultarla(
    scopes, endpoint
):
    from tests.test_pwa_comedores_api import _create_pwa_user, _token_client
    from pwa.models import AccesoComedorPWA

    comedor, proyecto, _, _ = scopes
    usuario = _create_pwa_user(
        comedor=comedor,
        role=AccesoComedorPWA.ROL_REPRESENTANTE,
        username="sin_rendiciones",
    )
    rendicion = _crear_rendicion(comedor, proyecto=proyecto)
    url = f"/api/comedores/{comedor.pk}/rendiciones/"
    if endpoint:
        url += f"{rendicion.pk}/"
    assert _token_client(usuario).get(url).status_code == 403


@pytest.mark.parametrize("tradicional", [True, False])
def test_cuadro_prestaciones_muestra_merienda_reforzada_solo_en_tradicional(
    tradicional,
):
    from pathlib import Path
    from types import SimpleNamespace
    from django.template import Context, Template
    from django.utils.html import strip_tags

    archivo = (
        Path(__file__).parents[1] / "comedores/templates/comedor/comedor_detail.html"
    )
    template = archivo.read_text(encoding="utf-8")
    inicio = template.index(
        '<table class="table table-bordered table-sm align-middle text-center mb-0 prestaciones-table">'
    )
    fin = template.index("</table>", inicio) + len("</table>")
    html = Template("{% load custom_filters %}" + template[inicio:fin]).render(
        Context(
            {
                "es_linea_tradicional": tradicional,
                "informe_tecnico": SimpleNamespace(
                    aprobadas_merienda_reforzada_lunes=37
                ),
            }
        )
    )
    assert ("Merienda Reforzada" in html) is tradicional
    assert ("37" in strip_tags(html).split()) is tradicional
    assert "Asistentes" not in html
    assert "Prestaciones" in html


def test_migracion_seguros_conserva_contrato_de_campos():
    from importlib import import_module
    from rendicioncuentasmensual.models import SolicitudDocumentoFaltante

    migration = import_module(
        "rendicioncuentasmensual.migrations.0023_issue_2683_planilla_seguros_ii"
    )
    modelos = {
        "documentacionadjunta": DocumentacionAdjunta,
        "solicituddocumentofaltante": SolicitudDocumentoFaltante,
    }
    assert len(migration.Migration.operations) == 2
    for operation in migration.Migration.operations:
        assert operation.name == "categoria"
        actual = modelos[operation.model_name]._meta.get_field("categoria")
        assert operation.field.deconstruct()[1:] == actual.deconstruct()[1:]
