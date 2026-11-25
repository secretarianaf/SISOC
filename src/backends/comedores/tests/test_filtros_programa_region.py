"""Filtros de Programa, Región y Subzona/Aglomerado en Comedores y Organizaciones.

Los tres son de opciones fijas (no texto libre). Región y subzona son las de
Abordaje Comunitario, que ahora van por proyecto: en Comedores se toman del
proyecto del comedor y en Organizaciones de cualquiera de sus proyectos.
"""

import json

import pytest
from django.core.cache import cache

from comedores.models import Comedor, Programas
from comedores.services.comedor_service.impl import COMEDOR_ADVANCED_FILTER
from comedores.services.filter_config import (
    FIELD_TYPES as COMEDOR_FIELD_TYPES,
    get_filters_ui_config as comedores_ui_config,
)
from gestion_organizaciones.filter_config import (
    FIELD_TYPES as ORGANIZACION_FIELD_TYPES,
    ORGANIZACION_ADVANCED_FILTER,
    get_filters_ui_config as organizaciones_ui_config,
)
from gestion_organizaciones.models import ProgramaOrganizacion
from organizaciones.models import (
    Organizacion,
    ProyectoOrganizacion,
    RegionAbordajeComunitario,
    SubzonaAbordajeComunitario,
)


@pytest.fixture
def datos(db):
    cache.clear()
    secos = Programas.objects.create(nombre="Abordaje comunitario - Línea Secos")
    alimentar = Programas.objects.create(nombre="Alimentar comunidad")
    amba = RegionAbordajeComunitario.objects.create(nombre="AMBA")
    noa = RegionAbordajeComunitario.objects.create(nombre="NOA")
    sub_amba = SubzonaAbordajeComunitario.objects.create(nombre="AMBA", region=amba)
    salta = SubzonaAbordajeComunitario.objects.create(nombre="SALTA", region=noa)

    org_amba = Organizacion.objects.create(nombre="Org AMBA", sin_vencimiento=True)
    org_noa = Organizacion.objects.create(nombre="Org NOA", sin_vencimiento=True)
    proyecto_amba = ProyectoOrganizacion.objects.create(
        organizacion=org_amba,
        codigo="A-1",
        region_abordaje=amba,
        subzona_abordaje=sub_amba,
    )
    proyecto_noa = ProyectoOrganizacion.objects.create(
        organizacion=org_noa,
        codigo="N-1",
        region_abordaje=noa,
        subzona_abordaje=salta,
    )
    # Una organización con dos proyectos en la misma región no se duplica.
    ProyectoOrganizacion.objects.create(
        organizacion=org_amba, codigo="A-2", region_abordaje=amba
    )
    ProgramaOrganizacion.objects.create(organizacion=org_amba, programa=secos)
    ProgramaOrganizacion.objects.create(organizacion=org_noa, programa=alimentar)

    comedor_amba = Comedor.objects.create(
        nombre="Comedor AMBA",
        organizacion=org_amba,
        proyecto=proyecto_amba,
        programa=secos,
    )
    comedor_noa = Comedor.objects.create(
        nombre="Comedor NOA",
        organizacion=org_noa,
        proyecto=proyecto_noa,
        programa=alimentar,
    )
    yield {
        "comedor_amba": comedor_amba,
        "comedor_noa": comedor_noa,
        "org_amba": org_amba,
        "org_noa": org_noa,
    }
    cache.clear()


def _filtrar(engine, queryset, campo, valor, op="eq"):
    """Como los consumidores (listado, exportación, comunicados): con distinct().

    Región, subzona y programa de una organización cruzan relaciones a muchos
    (proyectos, programas), así que el filtro solo puede repetir filas.
    """
    payload = {"logic": "AND", "items": [{"field": campo, "op": op, "value": valor}]}
    filtrado = engine.filter_queryset(queryset, {"filters": json.dumps(payload)})
    return list(filtrado.distinct())


@pytest.mark.parametrize(
    "ui_config, tipos",
    [
        (comedores_ui_config, COMEDOR_FIELD_TYPES),
        (organizaciones_ui_config, ORGANIZACION_FIELD_TYPES),
    ],
    ids=["comedores", "organizaciones"],
)
def test_programa_region_y_subzona_son_opciones_fijas(datos, ui_config, tipos):
    campos = {campo["name"]: campo for campo in ui_config()["fields"]}

    for nombre in ("programa", "region", "subzona"):
        assert tipos[nombre] == "choice"
        assert campos[nombre]["type"] == "choice"
    assert {c["value"] for c in campos["programa"]["choices"]} >= {
        "Abordaje comunitario - Línea Secos",
        "Alimentar comunidad",
    }
    assert {c["value"] for c in campos["region"]["choices"]} >= {"AMBA", "NOA"}
    assert {c["value"] for c in campos["subzona"]["choices"]} >= {"AMBA", "SALTA"}
    assert campos["region"]["label"] == "Región (Abordaje Comunitario)"
    assert campos["subzona"]["label"] == "Subzona/Aglomerado (Abordaje Comunitario)"


def test_comedores_filtran_por_programa_region_y_subzona(datos):
    comedores = Comedor.objects.all()
    engine = COMEDOR_ADVANCED_FILTER

    assert _filtrar(engine, comedores, "programa", "Alimentar comunidad") == [
        datos["comedor_noa"]
    ]
    assert _filtrar(engine, comedores, "region", "AMBA") == [datos["comedor_amba"]]
    assert _filtrar(engine, comedores, "subzona", "SALTA") == [datos["comedor_noa"]]
    assert _filtrar(engine, comedores, "region", "AMBA", op="ne") == [
        datos["comedor_noa"]
    ]


def test_organizaciones_filtran_por_programa_region_y_subzona(datos):
    organizaciones = Organizacion.objects.all()
    engine = ORGANIZACION_ADVANCED_FILTER

    assert _filtrar(
        engine, organizaciones, "programa", "Abordaje comunitario - Línea Secos"
    ) == [datos["org_amba"]]
    assert _filtrar(engine, organizaciones, "region", "AMBA") == [datos["org_amba"]]
    assert _filtrar(engine, organizaciones, "subzona", "SALTA") == [datos["org_noa"]]


@pytest.mark.django_db
def test_listado_de_organizaciones_no_repite_con_varios_proyectos_en_la_region(
    datos, client, django_user_model
):
    from django.urls import reverse  # pylint: disable=import-outside-toplevel

    admin = django_user_model.objects.create_superuser("admin_filtros", "f@f.com", "x")
    client.force_login(admin)
    payload = json.dumps(
        {"logic": "AND", "items": [{"field": "region", "op": "eq", "value": "AMBA"}]}
    )

    respuesta = client.get(reverse("organizaciones"), {"filters": payload})

    assert respuesta.status_code == 200
    filas = [o.pk for o in respuesta.context["object_list"]]
    assert filas == [datos["org_amba"].pk]


def test_un_filtro_de_texto_viejo_sobre_programa_se_ignora(datos):
    """Un favorito guardado como 'contiene' ya no aplica: queda marcado obsoleto."""
    comedores = Comedor.objects.all()

    resultado = _filtrar(
        COMEDOR_ADVANCED_FILTER, comedores, "programa", "Alimentar", op="contains"
    )

    assert set(resultado) == set(comedores)
