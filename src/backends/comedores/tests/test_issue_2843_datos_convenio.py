"""Datos del Convenio en el legajo de Abordaje Comunitario (issue #2843).

- "Monto total conveniado" deja de mostrarse y cargarse para todos los programas.
- Los campos siguen el orden pedido, tanto en la edición como en el legajo.
- Las cantidades aceptan solo números y los montos se muestran como $100.000.000.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.urls import reverse

from comedores.forms.convenio_pnud_form import (
    PRESTACIONES_APROBADAS_FIELDS,
    ComedorDatosConvenioPnudForm,
)
from comedores.models import Comedor, ComedorDatosConvenioPnud, Programas

pytestmark = pytest.mark.django_db

TRADICIONAL = "Abordaje Comunitario - Línea Tradicional"
SECOS = "Abordaje Comunitario - Línea Secos"

ORDEN_TRADICIONAL = [
    "Organización solicitante",
    "Código de Proyecto",
    "Número de Convenio",
    "Estado General",
    "Subestado",
    "Nombre del Espacio Comunitario",
    "ID Externo",
    "Domicilio Completo",
    "Monto total del Convenio por Espacio - Prestaciones Alimentarias",
    "Monto total del Convenio por Espacio - Servicio Integral de Promoción Humana",
    "Prestaciones Financiadas Diarias - Desayuno",
    "Prestaciones Financiadas Diarias - Almuerzo",
    "Prestaciones Financiadas Diarias - Merienda",
    "Prestaciones Financiadas Diarias - Merienda Reforzada",
    "Prestaciones Financiadas Diarias - Cena",
    "Personas Conveniadas",
    "Total de personas declaradas en Servicio Integral de Promoción Humana",
]
ORDEN_SECOS = [
    *ORDEN_TRADICIONAL[:10],
    "Personas Conveniadas",
    "Cantidad de Módulos Mensuales",
    "Total de personas declaradas en Servicio Integral de Promoción Humana",
]


def _comedor(programa_nombre):
    programa, _ = Programas.objects.get_or_create(nombre=programa_nombre)
    return Comedor.objects.create(nombre="Espacio 2843", programa=programa)


def _campos_del_form(comedor):
    form = ComedorDatosConvenioPnudForm(comedor=comedor)
    return [name for name in form.fields if name not in PRESTACIONES_APROBADAS_FIELDS]


def _assert_en_orden(html, etiquetas):
    posiciones = [html.index(etiqueta) for etiqueta in etiquetas]
    assert posiciones == sorted(posiciones)


@pytest.mark.parametrize("programa", [TRADICIONAL, SECOS, "PNUD"])
def test_monto_total_conveniado_no_se_carga_en_ningun_programa(programa):
    assert "monto_total_conveniado" not in _campos_del_form(_comedor(programa))


def test_orden_de_campos_linea_tradicional():
    assert _campos_del_form(_comedor(TRADICIONAL)) == [
        "nro_convenio",
        "monto_convenio_prestaciones_alimentarias",
        "monto_convenio_siph",
        "prestaciones_financiadas_diarias_desayuno",
        "prestaciones_financiadas_diarias_almuerzo",
        "prestaciones_financiadas_diarias_merienda",
        "prestaciones_financiadas_diarias_merienda_reforzada",
        "prestaciones_financiadas_diarias_cena",
        "personas_conveniadas",
        "personas_declaradas_siph",
    ]


def test_orden_de_campos_linea_secos():
    assert _campos_del_form(_comedor(SECOS)) == [
        "nro_convenio",
        "monto_convenio_prestaciones_alimentarias",
        "monto_convenio_siph",
        "personas_conveniadas",
        "cantidad_modulos",
        "personas_declaradas_siph",
    ]


@pytest.mark.parametrize("valor", ["abc", "1.5", "-3"])
def test_cantidades_aceptan_solo_numeros_enteros(valor):
    form = ComedorDatosConvenioPnudForm(
        data={
            **{name: 0 for name in PRESTACIONES_APROBADAS_FIELDS},
            "personas_conveniadas": valor,
        },
        comedor=_comedor(SECOS),
    )
    assert not form.is_valid()
    assert "personas_conveniadas" in form.errors


def test_cantidades_marcan_el_input_como_numerico():
    form = ComedorDatosConvenioPnudForm(comedor=_comedor(SECOS))
    html = str(form["cantidad_modulos"])
    assert 'inputmode="numeric"' in html
    assert "data-solo-numeros" in html


def test_monto_acepta_el_signo_pesos():
    form = ComedorDatosConvenioPnudForm(
        data={
            **{name: 0 for name in PRESTACIONES_APROBADAS_FIELDS},
            "monto_convenio_siph": "$100.000.000",
        },
        comedor=_comedor(SECOS),
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["monto_convenio_siph"] == Decimal("100000000")


@pytest.mark.parametrize(
    "programa, orden",
    [(TRADICIONAL, ORDEN_TRADICIONAL), (SECOS, ORDEN_SECOS)],
)
def test_vista_de_edicion_respeta_el_orden(client, programa, orden):
    comedor = _comedor(programa)
    usuario = get_user_model().objects.create_superuser(
        username="admin2843", email="admin2843@example.com", password="x"
    )
    client.force_login(usuario)

    respuesta = client.get(reverse("comedor_convenio_pnud", args=[comedor.pk]))

    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    assert "Monto total conveniado" not in html
    _assert_en_orden(html, orden)
    assert '<span class="input-group-text">$</span>' in html
    # Mismo patrón visual que el alta de comedor: tarjetas de sección y botones fijos.
    assert "custom/css/comedorFormModerno.css" in html
    assert html.count('class="section-card"') == (4 if programa == TRADICIONAL else 3)
    assert "Guardar convenio" in html


@pytest.mark.parametrize(
    "programa, orden, es_tradicional, es_secos",
    [
        (TRADICIONAL, ORDEN_TRADICIONAL, True, False),
        (SECOS, ORDEN_SECOS, False, True),
    ],
)
def test_legajo_respeta_el_orden_y_formatea_montos(
    programa, orden, es_tradicional, es_secos
):
    comedor = _comedor(programa)
    datos = ComedorDatosConvenioPnud.objects.create(
        comedor=comedor,
        monto_total_conveniado=Decimal("999"),
        monto_convenio_prestaciones_alimentarias=Decimal("18889752.00"),
        personas_declaradas_siph=5,
    )

    html = render_to_string(
        "comedor/_datos_convenio_legajo.html",
        {
            "comedor": comedor,
            "datos_convenio_pnud": datos,
            "es_linea_tradicional": es_tradicional,
            "es_linea_secos": es_secos,
            "domicilio_completo_comedor": "Calle 123",
        },
    )

    html = " ".join(html.replace("&oacute;", "ó").replace("&uacute;", "ú").split())
    _assert_en_orden(html, orden)
    assert "Monto total conveniado" not in html
    assert "$18.889.752" in html
    # Monto sin cargar: no muestra un "$" suelto.
    assert (
        "Servicio Integral de Promoción Humana: <strong> Sin información </strong>"
        in html
    )
