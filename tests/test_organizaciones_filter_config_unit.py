"""Tests de los filtros combinables del listado de Organizaciones (issue #2505)."""

import json

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from core.models import Localidad, Municipio, Provincia
from gestion_organizaciones.filter_config import (
    FIELD_MAP,
    FIELD_TYPES,
    ORGANIZACION_ADVANCED_FILTER,
    get_filters_ui_config,
)
from organizaciones.models import Organizacion, TipoEntidad


def test_config_expone_campos_con_mapeo_y_operadores():
    config = get_filters_ui_config()
    nombres = {field["name"] for field in config["fields"]}

    # Todo campo ofrecido en la UI tiene mapeo ORM y tipo declarado.
    assert nombres <= set(FIELD_MAP)
    assert nombres <= set(FIELD_TYPES)
    assert config["defaultField"] == "nombre"
    for tipo in ("text", "number", "choice", "boolean", "date"):
        assert config["operators"][tipo]


@pytest.mark.django_db
def test_config_toma_los_tipos_de_entidad_de_la_base():
    TipoEntidad.objects.create(nombre="Asociacion civil")
    from django.core.cache import cache

    cache.clear()

    config = get_filters_ui_config()
    tipo_entidad = next(
        field for field in config["fields"] if field["name"] == "tipo_entidad"
    )

    assert {"value": "Asociacion civil", "label": "Asociacion civil"} in tipo_entidad[
        "choices"
    ]


@pytest.mark.django_db
def test_engine_combina_filtros_de_distintos_campos():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    otra = Provincia.objects.create(nombre="Cordoba")
    tipo = TipoEntidad.objects.create(nombre="Fundacion")
    objetivo = Organizacion.objects.create(
        nombre="Merendero Sur", provincia=provincia, tipo_entidad=tipo
    )
    Organizacion.objects.create(nombre="Merendero Norte", provincia=otra)
    Organizacion.objects.create(nombre="Otra cosa", provincia=provincia)

    payload = {
        "logic": "AND",
        "items": [
            {"field": "nombre", "op": "contains", "value": "Merendero"},
            {"field": "provincia", "op": "contains", "value": "Buenos"},
        ],
    }
    resultado = ORGANIZACION_ADVANCED_FILTER.filter_queryset(
        Organizacion.objects.all(), {"filters": json.dumps(payload)}
    )

    assert list(resultado) == [objetivo]


@pytest.mark.django_db
def test_listado_de_organizaciones_acepta_filters(client):
    admin = User.objects.create_superuser("admin_org_filtros", "org@test.com", "test")
    provincia = Provincia.objects.create(nombre="Santa Fe")
    municipio = Municipio.objects.create(nombre="Rosario", provincia=provincia)
    Localidad.objects.create(nombre="Centro", municipio=municipio)
    buscada = Organizacion.objects.create(nombre="Comedor Esperanza", cuit=20111111112)
    Organizacion.objects.create(nombre="Otra organizacion", cuit=20222222223)
    client.force_login(admin)

    payload = json.dumps(
        {
            "logic": "AND",
            "items": [{"field": "nombre", "op": "contains", "value": "Esperanza"}],
        }
    )
    response = client.get(reverse("organizaciones"), {"filters": payload})

    assert response.status_code == 200
    ids = [org.pk for org in response.context["organizaciones"]]
    assert ids == [buscada.pk]


@pytest.mark.django_db
def test_filtros_de_fecha_comparan_por_dia_sobre_datetime():
    from datetime import datetime

    from django.utils import timezone

    del_dia = Organizacion.objects.create(nombre="Vence el 10")
    posterior = Organizacion.objects.create(nombre="Vence el 11")
    Organizacion.objects.filter(pk=del_dia.pk).update(
        fecha_vencimiento=timezone.make_aware(datetime(2026, 9, 10, 15, 0))
    )
    Organizacion.objects.filter(pk=posterior.pk).update(
        fecha_vencimiento=timezone.make_aware(datetime(2026, 9, 11, 9, 0))
    )

    def filtrar(op):
        payload = {
            "logic": "AND",
            "items": [{"field": "fecha_vencimiento", "op": op, "value": "2026-09-10"}],
        }
        return set(
            ORGANIZACION_ADVANCED_FILTER.filter_queryset(
                Organizacion.objects.all(), {"filters": json.dumps(payload)}
            ).values_list("pk", flat=True)
        )

    assert filtrar("eq") == {del_dia.pk}
    assert filtrar("gt") == {posterior.pk}
    assert filtrar("lte") == {del_dia.pk}


@pytest.mark.django_db
def test_export_no_infla_el_conteo_al_filtrar_por_relacion(rf):
    from comedores.models import Comedor
    from gestion_organizaciones.views_export import OrganizacionExportView

    organizacion = Organizacion.objects.create(nombre="Org con comedores")
    Comedor.objects.create(nombre="Comedor A", organizacion=organizacion)
    Comedor.objects.create(nombre="Comedor B", organizacion=organizacion)
    payload = json.dumps(
        {
            "logic": "AND",
            "items": [{"field": "comedor", "op": "contains", "value": "Comedor"}],
        }
    )
    view = OrganizacionExportView()
    view.request = rf.get("/", {"filters": payload})

    fila = view.get_queryset().get(pk=organizacion.pk)

    assert fila.comedores_count == 2
