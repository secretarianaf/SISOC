"""Regresiones de catálogos, asignaciones, montos y cierre documental (#2642)."""

import json
from datetime import date
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.test import RequestFactory

from comedores.forms.convenio_pnud_form import (
    ComedorDatosConvenioPnudForm,
    PRESTACIONES_APROBADAS_FIELDS,
)
from comedores.models import ComedorDatosConvenioPnud
from comedores.territoriales_pnud import territoriales_proyecto_comedor
from core.models import Provincia
from gestion_organizaciones.forms import OrganizacionForm
from organizaciones.models import RegionAbordajeComunitario, SubzonaAbordajeComunitario
from rendicioncuentasmensual.models import DocumentacionAdjunta, RendicionCuentaMensual
from rendicioncuentasmensual.services import (
    RendicionCuentaMensualService,
    RendicionProcesoService,
)
from tests.test_rendicioncuentasmensual_domain_rules import (
    scopes,
)  # pylint: disable=unused-import


@pytest.mark.django_db
def test_catalogo_admite_renombrar_opciones_asignadas(scopes):
    _, proyecto, _, _ = scopes
    organizacion = proyecto.organizacion
    region = RegionAbordajeComunitario.objects.create(nombre="Región inicial")
    subzona = SubzonaAbordajeComunitario.objects.create(
        nombre="Zona inicial", region=region
    )
    organizacion.region_abordaje = region
    organizacion.subzona_abordaje = subzona
    organizacion.save()
    region.nombre = "Región definitiva"
    subzona.nombre = "Zona definitiva"
    region.save()
    subzona.save()
    organizacion.refresh_from_db()
    assert organizacion.region_abordaje.nombre == "Región definitiva"
    assert organizacion.subzona_abordaje.nombre == "Zona definitiva"


def _documento(rendicion, nombre="Documento"):
    return DocumentacionAdjunta.objects.create(
        rendicion_cuenta_mensual=rendicion,
        nombre=nombre,
        archivo="prueba.pdf",
        categoria=DocumentacionAdjunta.CATEGORIA_FORMULARIO_II,
    )


def _rendicion(comedor, proyecto, etapa):
    return RendicionCuentaMensual.objects.create(
        comedor=comedor,
        proyecto=proyecto,
        mes=1,
        anio=2026,
        estado=RendicionCuentaMensual.ESTADO_REVISION,
        etapa_proceso=etapa,
        subestado_proceso=RendicionCuentaMensual.SUBESTADO_EN_CURSO,
    )


@pytest.mark.parametrize("valor", ["100.000.000", "100000000", "0"])
def test_montos_aceptan_pesos_enteros_y_separadores(valor):
    form = ComedorDatosConvenioPnudForm(
        data={
            **{name: 0 for name in PRESTACIONES_APROBADAS_FIELDS},
            "monto_total_conveniado": valor,
        }
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["monto_total_conveniado"] == Decimal(
        valor.replace(".", "")
    )


@pytest.mark.parametrize("valor", ["100,50", "100.50", "1.00.000", "1e5"])
def test_montos_rechazan_formatos_ambiguos(valor):
    form = ComedorDatosConvenioPnudForm(
        data={
            **{name: 0 for name in PRESTACIONES_APROBADAS_FIELDS},
            "monto_total_conveniado": valor,
        }
    )
    assert not form.is_valid()
    assert "monto_total_conveniado" in form.errors


def test_montos_se_muestran_sin_decimales_y_conservan_centavos_historicos():
    instance = ComedorDatosConvenioPnud(monto_total_conveniado=Decimal("100000000.25"))
    form = ComedorDatosConvenioPnudForm(instance=instance)
    assert 'value="100.000.000"' in str(form["monto_total_conveniado"])
    bound = ComedorDatosConvenioPnudForm(
        data={
            **{name: 0 for name in PRESTACIONES_APROBADAS_FIELDS},
            "monto_total_conveniado": "100.000.000",
        },
        instance=instance,
    )
    assert bound.is_valid(), bound.errors
    assert bound.cleaned_data["monto_total_conveniado"] == Decimal("100000000.25")


@pytest.mark.django_db
def test_asignacion_territorial_se_guarda_por_proyecto_y_conserva_legado(scopes):
    comedor, proyecto, _, otro_proyecto = scopes
    usuario = get_user_model().objects.create_user(username="territorial2642")
    usuario.profile.rol = "TERRITORIAL PNUD"
    usuario.profile.save()
    organizacion = proyecto.organizacion
    organizacion.territoriales_abordaje_comunitario.add(usuario)
    legado = get_user_model().objects.create_user(username="historico2642")
    organizacion.territoriales_abordaje_comunitario.add(legado)
    provincia = Provincia.objects.create(nombre="Provincia2642")
    datos = {
        "nombre": organizacion.nombre,
        "provincia": str(provincia.pk),
        "sin_vencimiento": "on",
        "proyectos_lineas": json.dumps(
            [{"codigo": proyecto.codigo}, {"codigo": otro_proyecto.codigo}]
        ),
        "asignaciones_territoriales": json.dumps(
            [{"proyecto": proyecto.codigo, "territorial": usuario.pk}]
        ),
    }
    form = OrganizacionForm(data=datos, instance=organizacion)
    assert form.is_valid(), form.errors
    form.save()
    assert list(proyecto.territoriales.all()) == [usuario]
    assert not otro_proyecto.territoriales.exists()
    assert not organizacion.territoriales_abordaje_comunitario.filter(
        pk=usuario.pk
    ).exists()
    assert organizacion.territoriales_abordaje_comunitario.filter(pk=legado.pk).exists()
    assert territoriales_proyecto_comedor(comedor) == [
        {"codigo": proyecto.codigo, "territorial": usuario.username}
    ]
    primera = _rendicion(
        comedor, proyecto, RendicionCuentaMensual.ETAPA_CARGA_DOCUMENTACION
    )
    segunda = _rendicion(
        comedor, otro_proyecto, RendicionCuentaMensual.ETAPA_CARGA_DOCUMENTACION
    )
    condicion = RendicionCuentaMensualService.q_territorial_asignado(usuario.pk)
    assert list(RendicionCuentaMensual.objects.filter(condicion)) == [primera]
    assert list(RendicionCuentaMensual.objects.filter(~condicion)) == [segunda]

    datos["asignaciones_territoriales"] = json.dumps(
        [{"proyecto": "AJENO", "territorial": usuario.pk}]
    )
    assert not OrganizacionForm(data=datos, instance=organizacion).is_valid()


@pytest.mark.django_db
def test_asignacion_general_legada_puede_quitarse_sin_proyecto(scopes):
    _, proyecto, _, _ = scopes
    organizacion = proyecto.organizacion
    legado = get_user_model().objects.create_user(username="legado2642")
    conservado = get_user_model().objects.create_user(username="conservado2642")
    ajeno = get_user_model().objects.create_user(username="ajeno2642")
    organizacion.territoriales_abordaje_comunitario.add(legado, conservado)
    provincia = Provincia.objects.create(nombre="Provincia2642")
    datos = {
        "nombre": organizacion.nombre,
        "provincia": str(provincia.pk),
        "sin_vencimiento": "on",
        "proyectos_lineas": json.dumps([{"codigo": proyecto.codigo}]),
        "asignaciones_territoriales": "[]",
        "quitar_territoriales_sin_proyecto": [str(legado.pk)],
    }

    form = OrganizacionForm(data=datos, instance=organizacion)
    assert form.is_valid(), form.errors
    form.save()

    assert list(organizacion.territoriales_abordaje_comunitario.all()) == [conservado]
    datos["quitar_territoriales_sin_proyecto"] = [str(ajeno.pk)]
    assert "quitar_territoriales_sin_proyecto" in (
        OrganizacionForm(data=datos, instance=organizacion).errors
    )
    datos["asignaciones_territoriales"] = json.dumps([{"proyecto": proyecto.codigo}])
    assert not OrganizacionForm(data=datos, instance=organizacion).is_valid()


@pytest.mark.django_db
def test_region_subzona_son_opcionales_y_selectores_cerrados(scopes):
    _, proyecto, _, _ = scopes
    region = RegionAbordajeComunitario.objects.create(nombre="Región de prueba")
    subzona = SubzonaAbordajeComunitario.objects.create(
        nombre="Subzona de prueba", region=region
    )
    proyecto.organizacion.region_abordaje = region
    form = OrganizacionForm(instance=proyecto.organizacion)
    assert not form.fields["region_abordaje"].required
    assert not form.fields["subzona_abordaje"].required
    assert form.fields["region_abordaje"].clean(region.pk) == region
    assert form.fields["subzona_abordaje"].clean(subzona.pk) == subzona
    with pytest.raises(ValidationError):
        form.fields["region_abordaje"].clean("valor inventado")


@pytest.mark.django_db
def test_rendiciones_filtran_region_subzona_incluyendo_historicas(scopes):
    comedor, proyecto, _, _ = scopes
    region = RegionAbordajeComunitario.objects.create(nombre="Región de prueba")
    subzona = SubzonaAbordajeComunitario.objects.create(nombre="Subzona de prueba")
    organizacion = proyecto.organizacion
    organizacion.region_abordaje = region
    organizacion.subzona_abordaje = subzona
    organizacion.save()
    actual = _rendicion(
        comedor, proyecto, RendicionCuentaMensual.ETAPA_CARGA_DOCUMENTACION
    )
    historica = _rendicion(
        comedor, None, RendicionCuentaMensual.ETAPA_CARGA_DOCUMENTACION
    )
    qs = RendicionCuentaMensualService.obtener_todas_rendiciones_cuentas_mensuales()
    assert set(
        qs.filter(
            region_abordaje_id=region.pk, subzona_abordaje_id=subzona.pk
        ).values_list("pk", flat=True)
    ) == {actual.pk, historica.pk}
    from rendicioncuentasmensual.views import RendicionCuentaMensualGlobalListView

    view = RendicionCuentaMensualGlobalListView()
    view.request = RequestFactory().get(
        "/",
        {
            "filters": json.dumps(
                {
                    "logic": "AND",
                    "items": [
                        {"field": "region", "op": "eq", "value": str(region.pk)},
                        {"field": "subzona", "op": "eq", "value": str(subzona.pk)},
                    ],
                }
            )
        },
    )
    assert set(view.get_queryset().values_list("pk", flat=True)) == {
        actual.pk,
        historica.pk,
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    "etapa,accion",
    [
        (
            RendicionCuentaMensual.ETAPA_REVISION_DOCUMENTACION,
            RendicionProcesoService.ACCION_FINALIZAR_TERRITORIAL,
        ),
        (
            RendicionCuentaMensual.ETAPA_REVISION_AUDITORIA,
            RendicionProcesoService.ACCION_FINALIZAR_REVISION_AUDITORIA,
        ),
    ],
)
def test_decisiones_rectificables_solo_se_confirman_al_finalizar(scopes, etapa, accion):
    comedor, proyecto, _, _ = scopes
    rendicion = _rendicion(comedor, proyecto, etapa)
    documento = _documento(rendicion)
    for estado, observacion in [
        ("subsanar", "Falta firma"),
        ("validado", None),
        ("subsanar", "Corregir fecha"),
        ("validado", None),
    ]:
        RendicionCuentaMensualService.actualizar_estado_documento_revision(
            documento=documento, estado=estado, observaciones=observacion
        )
        documento.refresh_from_db()
        assert documento.estado == "presentado"
        assert documento.revision_estado == estado
    RendicionProcesoService.ejecutar(rendicion=rendicion, accion=accion, datos={})
    documento.refresh_from_db()
    assert documento.estado == "validado"
    assert documento.revision_estado is None
    with pytest.raises(ValidationError):
        RendicionCuentaMensualService.actualizar_estado_documento_revision(
            documento=documento, estado="subsanar", observaciones="No permitido"
        )


@pytest.mark.django_db
def test_cierre_incompleto_no_confirma_borradores(scopes):
    comedor, proyecto, _, _ = scopes
    rendicion = _rendicion(
        comedor, proyecto, RendicionCuentaMensual.ETAPA_REVISION_DOCUMENTACION
    )
    documento = _documento(rendicion)
    _documento(rendicion, nombre="Sin revisar")
    RendicionCuentaMensualService.actualizar_estado_documento_revision(
        documento=documento, estado="validado"
    )
    with pytest.raises(ValidationError, match="sin revisar"):
        RendicionProcesoService.ejecutar(
            rendicion=rendicion,
            accion=RendicionProcesoService.ACCION_FINALIZAR_TERRITORIAL,
            datos={},
        )
    documento.refresh_from_db()
    assert documento.estado == "presentado"
    assert documento.revision_estado == "validado"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "codigo,nombre,linea",
    [
        ("AMBA", "", "secos"),
        ("AMBA111", "", "secos"),
        ("AMBA123", "", "secos"),
        ("AMBA-123", "", "secos"),
        ("AMBA_123", "", "secos"),
        ("AMBA 1111", "", "secos"),
        (" amba111 ", "", "secos"),
        ("CODIGO", " AMBA 1111 ", "secos"),
        ("XAMBA111", "", "tradicional"),
        ("CODIGO", " amba ", "secos"),
        ("OTRO", "Otro", "tradicional"),
    ],
)
def test_alta_deriva_linea_del_proyecto_aunque_cliente_envie_otra(
    scopes, codigo, nombre, linea
):
    comedor, proyecto, _, _ = scopes
    proyecto.codigo, proyecto.nombre = codigo, nombre
    proyecto.save()
    rendicion = RendicionCuentaMensualService.crear_rendicion_mobile(
        comedor=comedor,
        data={
            "proyecto_id": proyecto.pk,
            "convenio": "P01",
            "numero_rendicion": 1,
            "periodo_inicio": date(2026, 1, 1),
            "periodo_fin": date(2026, 1, 31),
            "linea_programatica": "tradicional" if linea == "secos" else "secos",
        },
    )
    assert rendicion.linea_programatica == linea


@pytest.mark.mysql_compat
@pytest.mark.django_db(transaction=True)
def test_dos_inicios_concurrentes_solo_ocupan_un_cupo(scopes):
    if not connection.features.has_select_for_update:
        pytest.skip("Requiere bloqueos de fila reales")
    comedor, proyecto, _, _ = scopes
    rendiciones = [
        _rendicion(
            comedor, proyecto, RendicionCuentaMensual.ETAPA_REVISION_DOCUMENTACION
        )
        for _ in range(2)
    ]
    RendicionCuentaMensual.objects.filter(
        pk__in=[item.pk for item in rendiciones]
    ).update(subestado_proceso="pendiente")
    barrera = Barrier(2, timeout=15)

    def iniciar(pk):
        close_old_connections()
        try:
            rendicion = RendicionCuentaMensual.objects.get(pk=pk)
            barrera.wait()
            try:
                RendicionProcesoService.ejecutar(
                    rendicion=rendicion,
                    accion=RendicionProcesoService.ACCION_INICIAR_TERRITORIAL,
                    datos={},
                )
            except ValidationError:
                return "bloqueada"
            return "iniciada"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(iniciar, [item.pk for item in rendiciones]))
    assert sorted(resultados) == ["bloqueada", "iniciada"]
    assert (
        RendicionCuentaMensual.objects.filter(
            proyecto=proyecto, subestado_proceso="en_curso"
        ).count()
        == 1
    )
