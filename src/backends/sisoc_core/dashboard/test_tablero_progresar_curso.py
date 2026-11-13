"""Tests del Tablero Becas Progresar · Curso obligatorio.

Las tablas que lee (`bi_progresar_curso_obligatorio_*`) las mantiene el equipo de
Datos y los modelos son `managed=False`: la base de tests no las crea, así que se
crean acá una vez por módulo. Los datos son inventados.
"""

import json
from datetime import date, datetime, timezone

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import DatabaseError, connection
from django.urls import reverse

from core.models import Municipio, Provincia
from users.models import ProfileTerritorialScope

from dashboard.models import ProgresarCursoEvolucion, ProgresarCursoResumen
from dashboard.services.tablero_progresar_curso import (
    alcance_del_usuario,
    construir_tablero,
)
from dashboard.services.tablero_progresar_curso import impl
from dashboard.services.tablero_progresar_curso.impl import (
    ALCANCE_NACIONAL,
    ALCANCE_PROVINCIAL,
    SIN_ALCANCE,
)

URL = "/dashboard/progresar-curso-obligatorio/"
# La carga real escribe la hora de Argentina sin zona; Django la lee como UTC. Se guarda
# así (10:00 en la base) para reproducir ese caso: el tablero tiene que mostrar 10:00.
CARGA = datetime(2026, 11, 13, 10, 0, tzinfo=timezone.utc)
OBLIGATORIO = "Progresar Obligatorio"


@pytest.fixture(scope="module")
def tablas_bi(django_db_setup, django_db_blocker):
    """Crea las tablas `bi_` en la base de tests (fuera de la transacción del test)."""
    with django_db_blocker.unblock():
        with connection.schema_editor() as editor:
            editor.create_model(ProgresarCursoResumen)
            editor.create_model(ProgresarCursoEvolucion)
    yield
    with django_db_blocker.unblock():
        with connection.schema_editor() as editor:
            editor.delete_model(ProgresarCursoEvolucion)
            editor.delete_model(ProgresarCursoResumen)


def _resumen(provincia, estado, titulares, **extra):
    datos = {
        "provincia_codigo": 0,
        "provincia": provincia,
        "linea": OBLIGATORIO,
        "estado_curso": estado,
        "genero_codigo": "F",
        "rango_edad": "18",
        "tramo_inactividad": None,
        "tramo_aprobacion": None,
        "titulares": titulares,
        "suma_edad": None,
        "casos_edad": 0,
        "fecha_carga": CARGA,
    }
    datos.update(extra)
    return ProgresarCursoResumen.objects.create(**datos)


@pytest.fixture
def datos(db, tablas_bi):  # pylint: disable=unused-argument,redefined-outer-name
    salta = Provincia.objects.create(nombre="Salta")
    caba = Provincia.objects.create(nombre="Ciudad Autónoma de Buenos Aires")
    _resumen(salta, "No inscripto", 90)
    _resumen(
        salta,
        "Certificado",
        8,
        suma_edad=144,
        casos_edad=8,
        tramo_aprobacion="menos de 1 h",
    )
    _resumen(
        salta,
        "Inscripto sin rendir",
        2,
        suma_edad=36,
        casos_edad=2,
        tramo_inactividad="más de 30",
    )
    _resumen(caba, "No inscripto", 45)
    _resumen(caba, "Certificado", 5, suma_edad=95, casos_edad=5)
    for provincia, inscriptos, aprobados in ((salta, 10, 8), (caba, 5, 5)):
        ProgresarCursoEvolucion.objects.create(
            fecha=date(2026, 11, 10),
            provincia_codigo=0,
            provincia=provincia,
            linea=OBLIGATORIO,
            genero_codigo="F",
            inscriptos=inscriptos,
            aprobados=aprobados,
            fecha_carga=CARGA,
        )
    return {"salta": salta, "caba": caba}


def _permiso():
    """La llave está en `Meta.permissions`; se crea acá por si la base de tests no
    corrió el `post_migrate`."""
    content_type = ContentType.objects.get_for_model(
        ProgresarCursoResumen, for_concrete_model=False
    )
    return Permission.objects.get_or_create(
        content_type=content_type,
        codename="view_tablero_progresar_curso",
        defaults={"name": "Puede ver el Tablero Becas Progresar · Curso obligatorio"},
    )[0]


def _usuario(username, con_permiso=True, provincial=False):
    user = User.objects.create_user(username=username, password="pass")
    if con_permiso:
        user.user_permissions.add(_permiso())
    if provincial:
        user.profile.es_usuario_provincial = True
        user.profile.save()
    return user


def _titulares(tablero):
    columna = tablero["resumen_columnas"].index("titulares")
    return sum(fila[columna] for fila in tablero["resumen"])


def test_usuario_no_provincial_ve_todo_el_pais(datos):
    tablero = construir_tablero(_usuario("nacional"))

    assert tablero["alcance"] == ALCANCE_NACIONAL
    assert _titulares(tablero) == 150
    assert len(tablero["evolucion"]) == 2
    assert tablero["fecha_carga"] == "2026-11-13 10:00"
    # Los nombres largos de SISOC se acortan para las etiquetas
    assert set(tablero["provincias"].values()) == {"Salta", "CABA"}


def test_provincial_ve_solo_su_provincia(datos):
    user = _usuario("salta", provincial=True)
    ProfileTerritorialScope.objects.create(
        profile=user.profile, provincia=datos["salta"]
    )

    tablero = construir_tablero(user)

    assert tablero["alcance"] == ALCANCE_PROVINCIAL
    assert _titulares(tablero) == 100
    assert tablero["provincias"] == {str(datos["salta"].id): "Salta"}
    columna = tablero["evolucion_columnas"].index("provincia_id")
    assert {fila[columna] for fila in tablero["evolucion"]} == {datos["salta"].id}


def test_provincial_con_varias_provincias_ve_las_suyas(datos):
    user = _usuario("noa", provincial=True)
    for provincia in (datos["salta"], datos["caba"]):
        ProfileTerritorialScope.objects.create(
            profile=user.profile, provincia=provincia
        )

    tablero = construir_tablero(user)

    assert tablero["alcance"] == ALCANCE_PROVINCIAL
    assert _titulares(tablero) == 150


def test_provincial_sin_jurisdiccion_no_ve_datos(
    datos,
):  # pylint: disable=unused-argument
    tablero = construir_tablero(_usuario("sin_scope", provincial=True))

    assert tablero["alcance"] == SIN_ALCANCE
    assert tablero["resumen"] == []
    assert tablero["evolucion"] == []
    assert tablero["provincias"] == {}


def test_provincial_solo_con_municipio_no_ve_la_provincia_entera(datos):
    """Las tablas no tienen municipio: un alcance por municipio no habilita la provincia."""
    user = _usuario("municipal", provincial=True)
    municipio = Municipio.objects.create(nombre="Capital", provincia=datos["salta"])
    ProfileTerritorialScope.objects.create(
        profile=user.profile, provincia=datos["salta"], municipio=municipio
    )

    tipo, filtro = alcance_del_usuario(user)

    assert tipo == SIN_ALCANCE
    assert filtro is None
    assert construir_tablero(user)["resumen"] == []


def test_superusuario_ve_todo_el_pais(datos):  # pylint: disable=unused-argument
    user = User.objects.create_superuser(username="admin", password="pass")
    user.profile.es_usuario_provincial = True
    user.profile.save()

    assert construir_tablero(user)["alcance"] == ALCANCE_NACIONAL


def test_sin_datos_cargados_no_falla(db, tablas_bi):  # pylint: disable=unused-argument
    tablero = construir_tablero(_usuario("vacio"))

    assert tablero["fecha_carga"] is None
    assert tablero["sin_datos"] is True
    assert tablero["resumen"] == []


def test_sin_tablas_bi_muestra_sin_datos_en_lugar_de_fallar(db, monkeypatch):
    """En un entorno sin las tablas `bi_` (QA, homologación) la pantalla no da error 500."""

    def sin_tabla(*args, **kwargs):
        raise DatabaseError("no existe la tabla")

    monkeypatch.setattr(impl, "_filas", sin_tabla)

    tablero = construir_tablero(_usuario("sin_tablas"))

    assert tablero["sin_datos"] is True
    assert tablero["resumen"] == []


def test_tablero_sin_login_redirige(client, db):  # pylint: disable=unused-argument
    respuesta = client.get(URL)

    assert respuesta.status_code == 302


def test_tablero_sin_permiso_devuelve_403(
    client, db
):  # pylint: disable=unused-argument
    client.force_login(_usuario("sin_permiso", con_permiso=False))

    assert client.get(URL).status_code == 403


def test_tablero_con_permiso_muestra_datos_agregados_sin_datos_personales(
    client, datos
):  # pylint: disable=unused-argument
    client.force_login(_usuario("con_permiso"))

    respuesta = client.get(URL)

    assert respuesta.status_code == 200
    contenido = respuesta.content.decode()
    assert 'id="tpc-tablero-datos"' in contenido
    datos_pagina = respuesta.context["tablero_datos"]
    assert _titulares(datos_pagina) == 150
    texto = json.dumps(datos_pagina).lower()
    assert "dni" not in texto
    assert "nombre" not in texto


def test_tablero_url_con_nombre():
    assert reverse("dashboard_tablero_progresar_curso") == URL
