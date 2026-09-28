"""Issue #2445: filtro y columna Territorial asignado en el listado de rendiciones."""

import json

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import RequestFactory
from django.urls import reverse

from comedores.models import Comedor
from core.services.favorite_filters import (
    SeccionesFiltrosFavoritos,
    obtener_configuracion_seccion,
)
from core.services.favorite_filters.validation import obtener_items_obsoletos
from organizaciones.models import Organizacion, ProyectoOrganizacion
from rendicioncuentasmensual import filter_config
from rendicioncuentasmensual import views as module
from rendicioncuentasmensual.models import RendicionCuentaMensual
from users.services_territoriales import ROL_TERRITORIAL_PNUD

pytestmark = pytest.mark.django_db
User = get_user_model()

CAMPO = "territorial_asignado"


def _territorial(username, last_name, rol=ROL_TERRITORIAL_PNUD):
    user = User.objects.create_user(
        username=username, password="pwd", first_name="Nom", last_name=last_name
    )
    user.profile.rol = rol
    user.profile.save(update_fields=["rol"])
    return user


def _organizacion(nombre, *territoriales):
    organizacion = Organizacion.objects.create(nombre=nombre)
    organizacion.territoriales_abordaje_comunitario.add(*territoriales)
    return organizacion


def _rendicion_por_comedor(organizacion, mes=1):
    comedor = Comedor.objects.create(nombre=f"Comedor {mes}", organizacion=organizacion)
    return RendicionCuentaMensual.objects.create(comedor=comedor, mes=mes, anio=2026)


def _rendicion_por_proyecto(organizacion, mes=1, comedor=None):
    proyecto = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo=f"PROY-{mes}"
    )
    return RendicionCuentaMensual.objects.create(
        proyecto=proyecto, comedor=comedor, mes=mes, anio=2026
    )


def _filtrar(*items):
    request = RequestFactory().get(
        "/rendicioncuentasmensual/rendicioncuentasmensual/listado/",
        {"filters": json.dumps({"logic": "AND", "items": list(items)})},
    )
    view = module.RendicionCuentaMensualGlobalListView()
    view.request = request
    return list(view.get_queryset())


def _item(user, op="eq"):
    return {"field": CAMPO, "op": op, "value": str(user.pk)}


def test_filtra_rendiciones_por_territorial_via_comedor_y_via_proyecto():
    territorial = _territorial("t1", "Uno")
    otro = _territorial("t2", "Dos")
    org = _organizacion("Org A", territorial)
    via_comedor = _rendicion_por_comedor(org, mes=1)
    via_proyecto = _rendicion_por_proyecto(org, mes=2)
    _rendicion_por_comedor(_organizacion("Org B", otro), mes=3)

    assert set(_filtrar(_item(territorial))) == {via_comedor, via_proyecto}


def test_varios_territoriales_devuelven_todas_las_coincidencias_sin_duplicar():
    uno = _territorial("t1", "Uno")
    dos = _territorial("t2", "Dos")
    compartida = _rendicion_por_comedor(_organizacion("Org AB", uno, dos), mes=1)
    solo_dos = _rendicion_por_comedor(_organizacion("Org B", dos), mes=2)
    _rendicion_por_comedor(_organizacion("Org sin territorial"), mes=3)

    resultado = _filtrar(_item(uno), _item(dos))

    assert sorted(r.pk for r in resultado) == sorted([compartida.pk, solo_dos.pk])


def test_con_proyecto_manda_la_organizacion_del_proyecto():
    territorial = _territorial("t1", "Uno")
    org_proyecto = _organizacion("Org proyecto")
    org_comedor = _organizacion("Org comedor", territorial)
    comedor = Comedor.objects.create(nombre="Comedor", organizacion=org_comedor)
    _rendicion_por_proyecto(org_proyecto, mes=1, comedor=comedor)

    assert _filtrar(_item(territorial)) == []


def test_operador_ne_excluye_las_del_territorial():
    territorial = _territorial("t1", "Uno")
    excluida = _rendicion_por_comedor(_organizacion("Org A", territorial), mes=1)
    incluida = _rendicion_por_comedor(_organizacion("Org B"), mes=2)

    resultado = _filtrar(_item(territorial, op="ne"))

    assert incluida in resultado
    assert excluida not in resultado


def test_valor_invalido_se_ignora():
    rendicion = _rendicion_por_comedor(_organizacion("Org"), mes=1)

    assert _filtrar({"field": CAMPO, "op": "eq", "value": "abc"}) == [rendicion]


def test_filtro_combina_con_otros_campos_por_and():
    territorial = _territorial("t1", "Uno")
    org = _organizacion("Org A", territorial)
    enero = _rendicion_por_comedor(org, mes=1)
    _rendicion_por_comedor(org, mes=2)

    resultado = _filtrar(_item(territorial), {"field": "mes", "op": "eq", "value": "1"})

    assert resultado == [enero]


def test_configuracion_expone_territoriales_elegibles_aunque_haya_cache():
    cache.delete(filter_config.FILTERS_UI_CONFIG_CACHE_KEY)
    filter_config.get_filters_ui_config()
    territorial = _territorial("t1", "Uno")
    _territorial("no_elegible", "Otro", rol="TECNICO")

    campo = next(
        field
        for field in filter_config.get_filters_ui_config()["fields"]
        if field["name"] == CAMPO
    )

    assert campo["label"] == "Territorial asignado"
    assert campo["type"] == "choice"
    assert campo["choices"] == [
        {"value": str(territorial.pk), "label": "Uno, Nom (t1)"}
    ]


def test_filtro_favorito_con_territorial_no_queda_obsoleto():
    configuracion = obtener_configuracion_seccion(SeccionesFiltrosFavoritos.RENDICIONES)

    obsoletos = obtener_items_obsoletos(
        {"items": [{"field": CAMPO, "op": "eq", "value": "1"}]}, configuracion
    )

    assert obsoletos == []


def test_columna_territorial_disponible_y_exportable():
    territorial = _territorial("t1", "Uno")
    rendicion = _rendicion_por_comedor(_organizacion("Org", territorial), mes=1)
    view = module.RendicionCuentaMensualGlobalListView()

    claves = [clave for clave, _t, _f in view.COLUMN_DEFINITIONS]
    assert CAMPO in claves
    _clave, titulo, campo = next(
        definicion for definicion in view.COLUMN_DEFINITIONS if definicion[0] == CAMPO
    )
    assert titulo == "Territorial asignado"
    assert view.resolve_field(rendicion, campo) == "Uno, Nom (t1)"


def test_listado_muestra_territorial_en_la_grilla(client, admin_user):
    territorial = _territorial("t1", "Uno")
    _rendicion_por_proyecto(_organizacion("Org", territorial), mes=1)
    client.force_login(admin_user)

    response = client.get(reverse("rendicioncuentasmensual_global_list"))

    assert response.status_code == 200
    html = response.content.decode()
    assert "Territorial asignado" in html
    assert "Uno, Nom (t1)" in html
