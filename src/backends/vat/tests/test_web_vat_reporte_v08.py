"""V08.01: web API del reporte de inscriptos y asistencias. Datos sintéticos."""

import itertools
from datetime import date, time

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import Client
from rest_framework.test import APIClient

from ciudadanos.models import Ciudadano
from core.models import Dia, Localidad, Municipio, Provincia, Sexo
import VAT.views.reporte as reporte_views
from VAT.models import (
    AsistenciaSesion,
    Centro,
    ComisionCurso,
    ComisionHorario,
    Curso,
    Inscripcion,
    InstitucionUbicacion,
    ModalidadCursada,
    SesionComision,
)

pytestmark = pytest.mark.django_db

URL = "/api/web/vat/reportes/inscripciones-asistencias/"
NATIVA = "/vat/reportes/inscripciones-asistencias/"
_COUNTER = itertools.count()


def _client(*codes):
    user = get_user_model().objects.create_user(f"u{next(_COUNTER)}")
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="VAT", codename__in=codes)
    )
    client = APIClient()
    client.force_login(user)
    return client


def _superusuario():
    user = get_user_model().objects.create_superuser(f"s{next(_COUNTER)}", password="x")
    client = APIClient()
    client.force_login(user)
    return user, client


@pytest.fixture(autouse=True)
def _sin_cache_de_opciones():
    """Las opciones de filtros se cachean por id de usuario (5 minutos)."""
    cache.clear()


@pytest.fixture(name="datos")
def datos_fixture():
    provincia = Provincia.objects.create(nombre="Cordoba")
    municipio = Municipio.objects.create(nombre="Capital", provincia=provincia)
    localidad = Localidad.objects.create(nombre="Centro", municipio=municipio)
    sexo = Sexo.objects.create(sexo="X")
    modalidad = ModalidadCursada.objects.create(nombre="Virtual", activo=True)
    centro = Centro.objects.create(
        nombre="CFP Sintetico & Uno",
        codigo="CFP-SIN",
        provincia=provincia,
        municipio=municipio,
        localidad=localidad,
        activo=True,
    )
    ubicacion = InstitucionUbicacion.objects.create(
        centro=centro,
        localidad=localidad,
        rol_ubicacion="sede_principal",
        domicilio="Calle 1",
        es_principal=True,
    )
    comisiones = []
    for n in (1, 2):
        curso = Curso.objects.create(
            centro=centro,
            nombre=f"Curso {n}",
            modalidad=modalidad,
            usa_voucher=False,
            costo_creditos=0,
            estado="activo",
        )
        comisiones.append(
            ComisionCurso.objects.create(
                curso=curso,
                ubicacion=ubicacion,
                codigo_comision=f"COM-{n}",
                nombre=f"Comision {n}",
                cupo_total=20,
                fecha_inicio=date(2026, 4, 1),
                fecha_fin=date(2026, 4, 30),
                estado="activa",
            )
        )
    inscripciones = []
    for n, (estado, comision) in enumerate(
        [("inscripta", comisiones[0]), ("pre_inscripta", comisiones[1])], start=1
    ):
        ciudadano = Ciudadano.objects.create(
            apellido=f"Apellido{n}",
            nombre=f"Nombre{n}",
            fecha_nacimiento=date(1999, 5, n),
            tipo_documento=Ciudadano.DOCUMENTO_DNI,
            documento=40111000 + n,
            sexo=sexo,
        )
        inscripciones.append(
            Inscripcion.objects.create(
                ciudadano=ciudadano, comision_curso=comision, estado=estado
            )
        )
    dia, _ = Dia.objects.get_or_create(nombre="Lunes")
    horario = ComisionHorario.objects.create(
        comision_curso=comisiones[0],
        dia_semana=dia,
        hora_desde=time(18, 0),
        hora_hasta=time(20, 0),
        aula_espacio="Aula 1",
        vigente=True,
    )
    sesion = SesionComision.objects.create(
        comision_curso=comisiones[0],
        horario=horario,
        numero_sesion=1,
        fecha=date(2026, 4, 14),
        estado="realizada",
    )
    user, _ = _superusuario()
    AsistenciaSesion.objects.create(
        sesion=sesion,
        inscripcion=inscripciones[0],
        presente=True,
        registrado_por=user,
    )
    return {"centro": centro, "comisiones": comisiones, "inscripciones": inscripciones}


def test_access_follows_the_native_route_rule():
    assert APIClient().get(URL).status_code == 401
    assert _client("view_voucher").get(URL).status_code == 403
    for code in ("view_inscripcion", "view_comisioncurso", "view_centro"):
        assert _client(code).get(URL).status_code == 200


def test_projects_filters_summary_and_detail_like_the_native_page(datos):
    _, client = _superusuario()
    data = client.get(URL).json()
    assert data["nivel_pill"] == "INET"
    assert [f["key"] for f in data["filters"]] == [
        "nivel",
        "group_by",
        "fecha_desde",
        "fecha_hasta",
        "provincia_id",
        "municipio_id",
        "centro_id",
        "comision_id",
        "curso_id",
        "programa_id",
        "titulo_id",
        "estado",
        "usa_voucher",
        "estado_curso",
        "estado_comision",
    ]
    por_clave = {f["key"]: f for f in data["filters"]}
    assert (por_clave["nivel"]["value"], por_clave["nivel"]["permanent"]) == (
        "inet",
        True,
    )
    assert [o["label"] for o in por_clave["nivel"]["options"]] == [
        "Centro",
        "Provincia",
        "INET (Global)",
    ]
    assert por_clave["fecha_desde"]["type"] == "date"
    assert por_clave["provincia_id"]["options"][0] == {"value": "", "label": "Todas"}
    assert por_clave["centro_id"]["options"][1] == {
        "value": str(datos["centro"].pk),
        "label": "CFP Sintetico & Uno",
    }
    assert [o["label"] for o in por_clave["comision_id"]["options"][1:]] == [
        "COM-1 - CFP Sintetico & Uno",
        "COM-2 - CFP Sintetico & Uno",
    ]
    assert [o["value"] for o in por_clave["usa_voucher"]["options"]] == [
        "",
        "true",
        "false",
    ]
    assert data["resumen"] == {
        "inscripciones_total": "2",
        "presentes": "1",
        "ausentes": "0",
        "porcentaje_asistencia": "100,0",
    }
    assert data["group_label"] == "Centro"
    assert data["group_label_lower"] == "centro"
    assert data["rows"][0]["grupo"] == "CFP Sintetico & Uno"
    assert data["rows"][0]["inscripciones_total"] == "2"
    assert data["rows"][0]["porcentaje_asistencia"] == "100,0"
    assert data["page"]["summary"] is True
    assert data["detalle"]["info"]["count"] == "2"
    assert (
        data["detalle"]["info"]["start_index"],
        data["detalle"]["info"]["end_index"],
    ) == ("1", "2")
    fila = data["detalle"]["rows"][0]
    assert fila["persona"] in {"Apellido1, Nombre1", "Apellido2, Nombre2"}
    assert fila["documento"].startswith("4011100")
    assert fila["con_voucher"] is False
    assert fila["fecha"].count("/") == 2 and ":" in fila["fecha"]
    # Misma cifra que imprime la página nativa.
    nativo = Client()
    nativo.force_login(get_user_model().objects.filter(is_superuser=True).first())
    html = nativo.get(NATIVA).content.decode()
    assert '<strong class="rep-metric__value">2</strong>' in html
    assert "Mostrando 1-2 de 2" in html


def test_filters_and_grouping_follow_the_native_view(datos):
    _, client = _superusuario()
    data = client.get(URL, {"estado": "inscripta", "group_by": "comision"}).json()
    assert data["resumen"]["inscripciones_total"] == "1"
    assert data["group_label_lower"] == "comisión"
    assert [r["grupo"] for r in data["rows"]] == ["COM-1"]
    assert {f["key"]: f["value"] for f in data["filters"]}["estado"] == "inscripta"
    assert data["querystring"] == "estado=inscripta&group_by=comision"
    invalido = client.get(URL, {"group_by": "otro", "nivel": ""}).json()
    assert invalido["group_label"] == "Centro"
    assert invalido["nivel_pill"] == "INET"


def test_pagination_of_groups_and_detail(datos, monkeypatch):
    monkeypatch.setattr(
        reporte_views.ReporteInscriptosAsistenciasView, "paginate_by", 1
    )
    monkeypatch.setattr(reporte_views, "DETALLE_PER_PAGE", 1)
    _, client = _superusuario()
    data = client.get(URL, {"group_by": "comision", "page": "2"}).json()
    assert data["page"] == {
        "is_paginated": True,
        "number": 2,
        "num_pages": 2,
        "count": 2,
        "previous": 1,
        "next": None,
        "summary": True,
    }
    assert data["querystring"] == "group_by=comision"
    assert data["querystring_detalle"] == "group_by=comision&page=2"
    info = client.get(URL, {"detalle_page": "9"}).json()["detalle"]["info"]
    assert (info["number"], info["num_pages"], info["previous"], info["next"]) == (
        2,
        2,
        1,
        None,
    )
    assert len(client.get(URL).json()["detalle"]["rows"]) == 1


def test_empty_report_has_no_page_summary_and_ignores_export(datos):
    _, client = _superusuario()
    data = client.get(URL, {"estado": "rechazada"}).json()
    assert data["rows"] == []
    assert data["page"]["summary"] is False
    assert data["detalle"]["info"]["count"] == "0"
    assert data["resumen"]["inscripciones_total"] == "0"
    # Las descargas siguen siendo la vista nativa: la API no las sirve.
    respuesta = client.get(URL, {"export": "csv"})
    assert respuesta.status_code == 200
    assert respuesta["Content-Type"].startswith("application/json")


def test_the_api_is_read_only():
    client = _client("view_inscripcion")
    assert client.post(URL, {}).status_code == 405
