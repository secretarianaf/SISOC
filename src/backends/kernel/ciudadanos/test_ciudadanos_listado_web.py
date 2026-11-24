"""Listado de ciudadanos en JSON (``/ciudadanos/listar``): filas, filtros, páginas, permisos y exportación."""

import itertools
import json

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.test import Client

from ciudadanos.models import Ciudadano
from ciudadanos.forms import PROVINCIA_FILTER_CHOICES_CACHE_KEY
from core.models import Provincia, Sexo

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _sin_choices_cacheados():
    """Las provincias del filtro se cachean: que otro test no deje su lista aquí."""
    cache.delete(PROVINCIA_FILTER_CHOICES_CACHE_KEY)
    yield
    cache.delete(PROVINCIA_FILTER_CHOICES_CACHE_KEY)


URL = "/api/web/ciudadanos/listar/"


_DOCUMENTOS = itertools.count(30111222)


def _permiso(codigo):
    app, codename = codigo.split(".")
    permiso = Permission.objects.filter(
        content_type__app_label=app, codename=codename
    ).first()
    return permiso or Permission.objects.create(
        content_type=ContentType.objects.get_for_model(Group),
        codename=codename,
        name=codename,
    )


def _cliente(username, permisos=("ciudadanos.view_ciudadano",), csrf=False):
    user = User.objects.create_user(username=username, password="x")
    for codigo in permisos:
        user.user_permissions.add(_permiso(codigo))
    client = Client(enforce_csrf_checks=csrf)
    client.force_login(user)
    return client


def _ciudadano(apellido, **extra):
    return Ciudadano.objects.create(
        **{
            "nombre": "Nora",
            "apellido": apellido,
            "documento": next(_DOCUMENTOS),
            **extra,
        }
    )


def _apellidos(datos):
    return [fila["cells"][0]["text"] for fila in datos["results"]]


def test_proyecta_filas_celdas_badges_y_orden_por_pk():
    chaco = Provincia.objects.create(nombre="Chaco")
    mujer = Sexo.objects.create(sexo="Femenino")
    estandar = _ciudadano("Zeta", sexo=mujer, provincia=chaco)
    sin_dni = _ciudadano(
        "Alfa",
        documento=None,
        tipo_registro_identidad=Ciudadano.TIPO_REGISTRO_SIN_DNI,
        motivo_sin_dni=Ciudadano.MOTIVO_SIN_DNI_OTRO,
        requiere_revision_manual=True,
        estado_revision_manual=Ciudadano.REVISION_IDENTIDAD_PENDIENTE,
    )
    respuesta = _cliente("lis_get").get(f"{URL}?estado_revision=TODOS&filters_mode=ui")
    assert respuesta.status_code == 200
    assert "no-store" in respuesta["Cache-Control"]
    datos = respuesta.json()
    primero, segundo = datos["results"]
    assert primero["id"] == estandar.pk
    assert primero["cells"] == [
        {"text": "Zeta", "sort": "Zeta"},
        {"text": "Nora", "sort": "Nora"},
        {"text": str(estandar.documento), "sort": str(estandar.documento)},
        {"text": "Femenino", "sort": "Femenino"},
        {"text": "Chaco", "sort": "Chaco"},
    ]
    assert primero["tipo_registro"] == "ESTANDAR"
    assert primero["requiere_revision"] is False
    assert primero["ver_url"] == f"/ciudadanos/ver/{estandar.pk}"
    assert segundo["id"] == sin_dni.pk
    assert segundo["cells"][2:] == [{"text": "-", "sort": ""}] * 3
    assert segundo["tipo_registro"] == "SIN_DNI"
    assert segundo["requiere_revision"] is True
    assert datos["urls"] == {
        "list": "/ciudadanos/listar",
        "add": "/ciudadanos/crear/",
        "export": "/ciudadanos/exportar",
    }
    assert datos["messages"] == []
    assert [campo["name"] for campo in datos["filters_config"]["fields"]] == [
        "apellido",
        "nombre",
        "documento",
        "identificador_interno",
        "provincia",
    ]
    assert datos["filters_config"]["fields"][-1]["choices"] == [
        {"value": "Chaco", "label": "Chaco"}
    ]


def test_filtros_del_formulario_propio_y_valores_devueltos():
    for apellido in ("Pendiente", "Finalizada"):
        _ciudadano(
            apellido,
            documento=None,
            tipo_registro_identidad=Ciudadano.TIPO_REGISTRO_SIN_DNI,
            motivo_sin_dni=Ciudadano.MOTIVO_SIN_DNI_OTRO,
            requiere_revision_manual=True,
            estado_revision_manual=Ciudadano.REVISION_IDENTIDAD_PENDIENTE,
        )
    Ciudadano.objects.filter(apellido="Finalizada").update(
        requiere_revision_manual=False
    )
    cliente = _cliente("lis_filtro")
    inicial = cliente.get(URL).json()
    # Sin parámetros se aplica el modo UI: solo las revisiones finalizadas.
    assert inicial["filtros"]["estado_revision"]["value"] == "FINALIZADA"
    assert inicial["filtros"]["tipo_registro"]["label"] == "Estado identidad:"
    assert inicial["filtros"]["estado_revision"]["label"] == "Estado de Revisión:"
    assert [o["value"] for o in inicial["filtros"]["tipo_registro"]["options"]] == [
        "",
        "ESTANDAR",
        "SIN_DNI",
        "DNI_NO_VALIDADO_RENAPER",
    ]
    assert _apellidos(inicial) == ["Finalizada"]
    pendientes = cliente.get(
        f"{URL}?filters_mode=ui&estado_revision=PENDIENTE&q=Pend"
    ).json()
    assert _apellidos(pendientes) == ["Pendiente"]
    assert pendientes["filtros"]["q"] == "Pend"
    # Sin ``filters_mode`` el formulario trabaja en modo API: ``TODOS``.
    sin_modo = cliente.get(f"{URL}?q=Pend").json()
    assert sin_modo["filtros"]["estado_revision"]["value"] == "TODOS"
    assert _apellidos(sin_modo) == ["Pendiente"]
    por_tipo = cliente.get(f"{URL}?tipo_registro=SIN_DNI&filters_mode=ui").json()
    assert por_tipo["filtros"]["tipo_registro"]["value"] == "SIN_DNI"
    assert _apellidos(por_tipo) == ["Finalizada"]


def test_filtros_combinables_y_su_valor_crudo():
    _ciudadano("Alfa")
    _ciudadano("Beta")
    filtros = json.dumps(
        {
            "logic": "AND",
            "items": [{"field": "apellido", "op": "contains", "value": "bet"}],
        }
    )
    datos = _cliente("lis_comb").get(URL, {"filters": filtros}).json()
    assert _apellidos(datos) == ["Beta"]
    assert datos["filtros"]["filters"] == filtros


def test_paginas_de_25_sin_total_y_enlaces_con_los_demas_parametros():
    for numero in range(30):
        _ciudadano(f"Pag{numero:02d}")
    cliente = _cliente("lis_pag")
    primera = cliente.get(f"{URL}?q=Pag&busqueda=x").json()
    assert len(primera["results"]) == 25
    assert primera["page"] == {
        "is_paginated": True,
        "number": 1,
        "previous": None,
        "next": 2,
        "range": [1, 2, "..."],
        "query_prefix": "q=Pag&",
    }
    segunda = cliente.get(f"{URL}?page=2").json()
    assert len(segunda["results"]) == 5
    assert (segunda["page"]["previous"], segunda["page"]["next"]) == (1, None)
    assert segunda["page"]["range"] == [1, 2]


def test_exportar_e_importar_siguen_los_permisos_nativos():
    sin = _cliente("lis_sin").get(URL).json()
    assert sin["can_export"] is False
    assert sin["additional_buttons"] == []
    con = (
        _cliente(
            "lis_con",
            (
                "ciudadanos.view_ciudadano",
                "ciudadanos.add_ciudadano",
                "auth.role_exportar_a_csv",
            ),
        )
        .get(URL)
        .json()
    )
    assert con["can_export"] is True
    assert con["additional_buttons"] == [
        {
            "label": "IMPORTACION MASIVA",
            "url": "/ciudadanos/importacion-masiva/",
            "class": "btn btn-lg btn-export-csv",
            "title": "Importar ciudadanos desde Excel",
        }
    ]


def test_rechazos_y_solo_lectura():
    _ciudadano("Intacto")
    campos = ("pk", "apellido", "requiere_revision_manual")
    antes = list(Ciudadano.objects.values_list(*campos))
    assert Client().get(URL).status_code in (401, 403)
    assert _cliente("lis_perm", permisos=()).get(URL).status_code == 403
    cliente = _cliente("lis_ok", csrf=True)
    assert cliente.post(URL).status_code in (403, 405)
    assert cliente.get(URL).status_code == 200
    assert list(Ciudadano.objects.values_list(*campos)) == antes
