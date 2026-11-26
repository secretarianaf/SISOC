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


def _permiso(codename="view_tablero_progresar_curso"):
    """Las llaves están en `Meta.permissions`; se crean acá por si la base de tests no
    corrió el `post_migrate`."""
    content_type = ContentType.objects.get_for_model(
        ProgresarCursoResumen, for_concrete_model=False
    )
    return Permission.objects.get_or_create(
        content_type=content_type, codename=codename, defaults={"name": codename}
    )[0]


def _usuario(username, con_permiso=True, provincial=False, nacional=False):
    user = User.objects.create_user(username=username, password="pass")
    if con_permiso:
        user.user_permissions.add(_permiso())
    if nacional:
        user.user_permissions.add(_permiso("view_tablero_progresar_curso_nacional"))
    if provincial:
        user.profile.es_usuario_provincial = True
        user.profile.save()
    return user


def _titulares(tablero):
    columna = tablero["resumen_columnas"].index("titulares")
    return sum(fila[columna] for fila in tablero["resumen"])


def test_llave_nacional_ve_todo_el_pais(datos):
    tablero = construir_tablero(_usuario("nacional", nacional=True))

    assert tablero["alcance"] == ALCANCE_NACIONAL
    assert _titulares(tablero) == 150
    assert len(tablero["evolucion"]) == 2
    assert tablero["fecha_carga"] == "2026-11-13 10:00"
    # Los nombres largos de SISOC se acortan para las etiquetas
    assert set(tablero["provincias"].values()) == {"Salta", "CABA"}


def test_llave_comun_sin_ser_provincial_no_ve_datos(
    datos,
):  # pylint: disable=unused-argument
    """Un alta incompleta (llave sin perfil provincial) no muestra todo el país."""
    tablero = construir_tablero(_usuario("incompleto"))

    assert tablero["alcance"] == SIN_ALCANCE
    assert tablero["resumen"] == []


def test_llave_nacional_ve_todo_aunque_sea_provincial(datos):
    user = _usuario("coordinacion", provincial=True, nacional=True)
    ProfileTerritorialScope.objects.create(
        profile=user.profile, provincia=datos["salta"]
    )

    tablero = construir_tablero(user)

    assert tablero["alcance"] == ALCANCE_NACIONAL
    assert _titulares(tablero) == 150


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
    tablero = construir_tablero(_usuario("vacio", nacional=True))

    assert tablero["fecha_carga"] is None
    assert tablero["sin_datos"] is True
    assert tablero["resumen"] == []


def test_sin_tablas_bi_muestra_sin_datos_en_lugar_de_fallar(db, monkeypatch):
    """En un entorno sin las tablas `bi_` (QA, homologación) la pantalla no da error 500."""

    def sin_tabla(*args, **kwargs):
        raise DatabaseError("no existe la tabla")

    monkeypatch.setattr(impl, "_filas", sin_tabla)

    tablero = construir_tablero(_usuario("sin_tablas", nacional=True))

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
    client.force_login(_usuario("con_permiso", nacional=True))

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


def test_tablero_solo_con_llave_nacional_entra(
    client, db
):  # pylint: disable=unused-argument
    client.force_login(_usuario("solo_nacional", con_permiso=False, nacional=True))

    assert client.get(URL).status_code == 200


def test_fecha_carga_no_revela_datos_de_otras_provincias(client, datos):
    fecha_otra_provincia = datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc)
    ProgresarCursoResumen.objects.filter(provincia=datos["caba"]).update(
        fecha_carga=fecha_otra_provincia
    )
    user = _usuario("fecha_provincial", provincial=True)
    ProfileTerritorialScope.objects.create(
        profile=user.profile, provincia=datos["salta"]
    )
    client.force_login(user)

    respuesta = client.get(URL)

    assert respuesta.status_code == 200
    assert respuesta.context["tablero_datos"]["fecha_carga"] == "2026-11-13 10:00"
    assert _titulares(respuesta.context["tablero_datos"]) == 100
    assert (
        construir_tablero(_usuario("fecha_nacional", nacional=True))["fecha_carga"]
        == "2026-11-20 15:00"
    )


def test_fecha_y_filas_respetan_union_provincial(client, datos):
    tercera = Provincia.objects.create(nombre="Tercera")
    _resumen(
        tercera,
        "No inscripto",
        3,
        fecha_carga=datetime(2026, 11, 30, 10, tzinfo=timezone.utc),
    )
    ProgresarCursoResumen.objects.filter(provincia=datos["caba"]).update(
        fecha_carga=datetime(2026, 11, 20, 10, tzinfo=timezone.utc)
    )
    user = _usuario("union_metadata", provincial=True)
    for provincia in (datos["salta"], datos["caba"]):
        ProfileTerritorialScope.objects.create(
            profile=user.profile, provincia=provincia
        )
    client.force_login(user)
    respuesta = client.get(URL)
    assert respuesta.status_code == 200
    payload = respuesta.context["tablero_datos"]
    assert payload["fecha_carga"] == "2026-11-20 10:00"
    assert {fila[0] for fila in payload["resumen"]} == {
        datos["salta"].pk,
        datos["caba"].pk,
    }
    columna = payload["evolucion_columnas"].index("provincia_id")
    assert {fila[columna] for fila in payload["evolucion"]} == {
        datos["salta"].pk,
        datos["caba"].pk,
    }
    assert (
        construir_tablero(_usuario("nacional_metadata", nacional=True))["fecha_carga"]
        == "2026-11-30 10:00"
    )


def test_fecha_vacia_si_provincia_autorizada_no_tiene_filas(datos):
    vacia = Provincia.objects.create(nombre="Sin filas")
    user = _usuario("sin_filas_metadata", provincial=True)
    ProfileTerritorialScope.objects.create(profile=user.profile, provincia=vacia)
    payload = construir_tablero(user)
    assert payload["fecha_carga"] is None
    assert payload["resumen"] == []
    assert payload["evolucion"] == []


def _configurar_progresar_explicito():
    from dashboard.models import ConfiguracionTableroInterno, Tablero

    tablero = Tablero.objects.create(
        nombre="Progresar", slug="progresar", ruta_interna=URL
    )
    ConfiguracionTableroInterno.objects.create(
        codigo="progresar_curso", tablero=tablero, activa=True
    )
    return tablero


def test_concesion_explicita_provincial_protege_ruta_y_menu(client, datos):
    from dashboard.models import ConcesionTablero
    from dashboard.templatetags.dashboard_tags import tableros_para_sidebar
    from django.test import RequestFactory

    tablero = _configurar_progresar_explicito()
    user = _usuario("nuevo_salta", con_permiso=False)
    ConcesionTablero.objects.create(
        tablero=tablero, usuario=user, tipo="provincia", provincia=datos["salta"]
    )
    ProgresarCursoResumen.objects.filter(provincia=datos["caba"]).update(
        fecha_carga=datetime(2026, 11, 20, 15, tzinfo=timezone.utc)
    )
    client.force_login(user)
    respuesta = client.get(URL)
    assert respuesta.status_code == 200
    payload = respuesta.context["tablero_datos"]
    assert _titulares(payload) == 100
    assert payload["fecha_carga"] == "2026-11-13 10:00"
    assert set(payload["provincias"]) == {str(datos["salta"].pk)}
    request = RequestFactory().get("/")
    request.user = user
    assert [item["url"] for item in tableros_para_sidebar({"request": request})] == [
        URL
    ]


def test_explicito_no_usa_permiso_legacy_ni_cdi_como_provincia(client, datos):
    from dashboard.models import ConcesionTablero

    tablero = _configurar_progresar_explicito()
    user = _usuario("sin_concesion", nacional=True)
    ConcesionTablero.objects.create(
        tablero=tablero, usuario=user, tipo="cdi", cdi_id=17
    )
    client.force_login(user)
    assert client.get(URL).status_code == 403


def test_identidad_configurada_incorrecta_no_vuelve_a_legacy(client, datos):
    tablero = _configurar_progresar_explicito()
    tablero.ruta_interna = "/otra-ruta/"
    tablero.save(update_fields=["ruta_interna"])
    user = _usuario("identidad_invalida", nacional=True)
    client.force_login(user)
    assert client.get(URL).status_code == 403


def test_modo_legacy_se_mantiene_si_configuracion_no_activa(client, datos):
    from dashboard.models import ConfiguracionTableroInterno, Tablero

    tablero = Tablero.objects.create(
        nombre="Progresar", slug="progresar", ruta_interna=URL
    )
    ConfiguracionTableroInterno.objects.create(
        codigo="progresar_curso", tablero=tablero, activa=False
    )
    client.force_login(_usuario("legacy_activo", nacional=True))
    assert _titulares(client.get(URL).context["tablero_datos"]) == 150


def test_alias_de_catalogo_y_api_usan_misma_politica(client, datos):
    from dashboard.models import ConcesionTablero, Tablero

    tablero = _configurar_progresar_explicito()
    alias = Tablero.objects.create(
        nombre="Alias",
        slug="alias-progresar",
        ruta_interna=URL,
        permisos=["dashboard.view_tablero_progresar_curso_nacional"],
    )
    user = _usuario("alias_legacy", nacional=True)
    user.profile.acceso_web = True
    user.profile.must_change_password = False
    user.profile.needs_profile_confirmation = False
    user.profile.dni = "11222333"
    user.profile.save()
    client.force_login(user)
    assert client.get("/dashboard/alias-progresar/").status_code == 403
    assert client.get("/api/web/dashboard/alias-progresar/").status_code == 403
    ConcesionTablero.objects.create(
        tablero=tablero, usuario=user, tipo="provincia", provincia=datos["salta"]
    )
    assert client.get("/dashboard/alias-progresar/").status_code == 302
    respuesta = client.get("/api/web/dashboard/alias-progresar/")
    assert respuesta.status_code == 200
    assert respuesta.json()["redirect"] == URL
    assert "no-store" in respuesta["Cache-Control"]
    assert alias.usuario_puede_ver(user)


def test_nacional_explicito_y_revocacion(client, datos):
    from dashboard.models import AudienciaTableros, ConcesionTablero

    tablero = _configurar_progresar_explicito()
    user = _usuario("por_audiencia", con_permiso=False)
    audiencia = AudienciaTableros.objects.create(nombre="Nacional")
    audiencia.agregar_miembro(user)
    concesion = ConcesionTablero.objects.create(
        tablero=tablero, audiencia=audiencia, tipo="nacional"
    )
    client.force_login(user)
    respuesta = client.get(URL)
    assert respuesta.status_code == 200
    assert _titulares(respuesta.context["tablero_datos"]) == 150
    assert "no-store" in respuesta["Cache-Control"]
    concesion.delete()
    assert client.get(URL).status_code == 403


def test_configuracion_activa_no_puede_reabrir_legacy(client, datos):
    from django.core.exceptions import ValidationError
    from dashboard.models import ConfiguracionTableroInterno

    _configurar_progresar_explicito()
    client.force_login(_usuario("legacy_sin_concesion", nacional=True))
    assert client.get(URL).status_code == 403
    config = ConfiguracionTableroInterno.objects.get(codigo="progresar_curso")
    with pytest.raises(ValidationError):
        config.delete()
    with pytest.raises(ValidationError):
        ConfiguracionTableroInterno.objects.filter(pk=config.pk).delete()
    assert client.get(URL).status_code == 403


def test_alias_codificado_no_usa_permiso_legacy(client, datos):
    from dashboard.models import Tablero

    _configurar_progresar_explicito()
    Tablero.objects.create(
        nombre="Alias",
        slug="alias-codificado",
        ruta_interna="/dashboard/progresar-curso%2Dobligatorio/",
        permisos=["dashboard.view_tablero_progresar_curso_nacional"],
    )
    client.force_login(_usuario("alias_legacy_codificado", nacional=True))
    assert client.get("/dashboard/alias-codificado/").status_code == 403
    respuesta = client.head("/dashboard/alias-codificado/", REMOTE_ADDR="127.0.0.1")
    assert respuesta.status_code == 403
    assert "X-View" not in respuesta


def test_head_staff_y_anonimo_no_evaden_guarda(datos):
    from django.test import Client

    _configurar_progresar_explicito()
    user = _usuario("staff_sin_concesion", con_permiso=False)
    user.is_staff = True
    user.save()
    externo = Client(REMOTE_ADDR="203.0.113.42")
    externo.force_login(user)
    assert externo.get(URL).status_code == 403
    respuesta = externo.head(URL)
    assert respuesta.status_code == 403
    assert "X-View" not in respuesta
    interno = Client(REMOTE_ADDR="127.0.0.1")
    assert interno.get(URL).status_code == 302
    respuesta = interno.head(URL)
    assert respuesta.status_code == 302
    assert "X-View" not in respuesta


@pytest.mark.parametrize(
    "ruta",
    [
        "/otra/../dashboard/progresar-curso-obligatorio/",
        "/otra/%2e%2e/dashboard/progresar-curso-obligatorio/",
        "/otra/.%2E/dashboard/progresar-curso-obligatorio/",
        "/otra/%2e./dashboard/progresar-curso-obligatorio/",
    ],
)
def test_alias_con_segmentos_padre_no_usa_permiso_legacy(client, datos, ruta):
    from dashboard.models import Tablero

    _configurar_progresar_explicito()
    user = _usuario("alias_padre", nacional=True)
    alias = Tablero.objects.create(
        nombre="Alias",
        slug="alias-padre",
        ruta_interna=ruta,
        permisos=["dashboard.view_tablero_progresar_curso_nacional"],
    )
    alias.clean_fields()
    client.force_login(user)
    assert not alias.usuario_puede_ver(user)
    assert client.get("/dashboard/alias-padre/").status_code == 403
