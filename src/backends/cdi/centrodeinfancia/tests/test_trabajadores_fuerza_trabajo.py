"""Fuerza de Trabajo (#2943): quién ve y gestiona los trabajadores de un CDI.

Regla única ``puede_ver_trabajadores_cdi`` (R1), ocultamiento en el legajo y su
API web (R2), bloqueo por URL (R3), reporte Excel (R4) y falla cerrada (R5).
Los grupos llevan los permisos de users/bootstrap/groups_seed.py.
"""

from io import BytesIO

import openpyxl
import pytest
from django.contrib.auth.models import Group, Permission, User
from django.test import Client
from django.urls import reverse

from centrodeinfancia.access import puede_ver_trabajadores_cdi
from centrodeinfancia.models import AccesoCDI, CentroDeInfancia, Trabajador
from centrodeinfancia.services_reportes import (
    COLUMNAS_TRABAJADORES,
    filas_resumen,
    generar_reporte_cdi_xlsx,
)
from core.constants import UserGroups
from core.models import Provincia
from users.bootstrap.groups_seed import permission_codes_for_bootstrap_group
from users.models import Profile, ProfileTerritorialScope

pytestmark = pytest.mark.django_db

TRABAJADOR = UserGroups.CDI_TRABAJADOR
REFERENTE = UserGroups.CDI_REFERENTE_CENTRO
VEN_TODOS = (
    UserGroups.SIMEPI_ADMINISTRADOR,
    UserGroups.SIMEPI_EQUIPO_NACIONAL,
    UserGroups.SIMEPI_AUDITORIA,
    UserGroups.SIMEPI_EGP,
)


def _grupo_sembrado(nombre):
    grupo, _ = Group.objects.get_or_create(name=nombre)
    for code in permission_codes_for_bootstrap_group(nombre):
        app, codename = code.split(".", 1)
        permiso = Permission.objects.filter(
            content_type__app_label=app, codename=codename
        ).first()
        if permiso:
            grupo.permissions.add(permiso)
    return grupo


def _usuario(username, *grupos, superuser=False, provincia=None):
    user = User.objects.create_user(username=username, is_superuser=superuser)
    for nombre in grupos:
        user.groups.add(_grupo_sembrado(nombre))
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    if provincia is not None:
        profile.es_usuario_provincial = True
        profile.provincia = provincia
        ProfileTerritorialScope.objects.create(profile=profile, provincia=provincia)
    profile.save()
    return User.objects.get(pk=user.pk)


def _legajo(centro, user, funcion, subcomponente="cdi", apellido="Legajo"):
    return Trabajador.objects.create(
        centro=centro,
        usuario=user,
        nombre=user.username,
        apellido=apellido,
        subcomponente=subcomponente,
        funcion_cdi=funcion,
    )


def _trabajador_cdi(username, centro, funcion, **kwargs):
    user = _usuario(username, TRABAJADOR)
    _legajo(centro, user, funcion, **kwargs)
    return user


def _cliente(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="datos")
def datos_fixture():
    provincia = Provincia.objects.create(nombre="Neuquén")
    a = CentroDeInfancia.objects.create(nombre="CDI A", provincia=provincia)
    b = CentroDeInfancia.objects.create(nombre="CDI B", provincia=provincia)
    trabajador_a = Trabajador.objects.create(
        centro=a, nombre="Ana", apellido="Sala", subcomponente="cdi"
    )
    trabajador_b = Trabajador.objects.create(
        centro=b, nombre="Beto", apellido="Cocina", subcomponente="cdi"
    )
    return {
        "provincia": provincia,
        "a": a,
        "b": b,
        "trabajador_a": trabajador_a,
        "trabajador_b": trabajador_b,
    }


# R1 / R5 — regla única por CDI


@pytest.mark.parametrize("grupo", VEN_TODOS)
def test_simepi_del_pedido_ve_los_trabajadores(datos, grupo):
    provincia = datos["provincia"] if grupo == UserGroups.SIMEPI_EGP else None
    user = _usuario(f"r1-{grupo}", grupo, provincia=provincia)

    assert puede_ver_trabajadores_cdi(user, datos["a"])


def test_superusuario_ve_los_trabajadores(datos):
    assert puede_ver_trabajadores_cdi(_usuario("r1-super", superuser=True), datos["a"])


def test_analista_de_datos_ya_no_ve_los_trabajadores(datos):
    user = _usuario("r1-analista", UserGroups.SIMEPI_ANALISTA_DATOS)

    assert not puede_ver_trabajadores_cdi(user, datos["a"])


def test_referente_solo_con_acceso_activo_a_ese_cdi(datos):
    activo = _usuario("r1-ref-activo", REFERENTE)
    AccesoCDI.objects.create(user=activo, centro=datos["a"])
    suspendido = _usuario("r1-ref-suspendido", REFERENTE)
    AccesoCDI.objects.create(
        user=suspendido, centro=datos["a"], estado=AccesoCDI.Estado.SUSPENDIDO
    )

    assert puede_ver_trabajadores_cdi(activo, datos["a"])
    assert not puede_ver_trabajadores_cdi(activo, datos["b"])
    assert not puede_ver_trabajadores_cdi(suspendido, datos["a"])


@pytest.mark.parametrize("funcion", ["director_coordinador", "administrativo"])
def test_trabajador_director_o_administrativo_ve_su_cdi(datos, funcion):
    user = _trabajador_cdi(f"r1-{funcion}", datos["a"], funcion)

    assert puede_ver_trabajadores_cdi(user, datos["a"])
    assert not puede_ver_trabajadores_cdi(user, datos["b"])


def test_la_funcion_se_evalua_por_centro(datos):
    # Director en A, docente en B: ve A y no B.
    user = _trabajador_cdi("r1-por-centro", datos["a"], "director_coordinador")
    _legajo(datos["b"], user, "educador_docente_sala")

    assert puede_ver_trabajadores_cdi(user, datos["a"])
    assert not puede_ver_trabajadores_cdi(user, datos["b"])


@pytest.mark.parametrize(
    ("funcion", "subcomponente"),
    [
        ("educador_docente_sala", "cdi"),
        ("seguridad", "cdi"),
        (None, "cdi"),
        ("director_coordinador", "egp"),
    ],
)
def test_falla_cerrada_para_el_resto_de_los_trabajadores(datos, funcion, subcomponente):
    user = _trabajador_cdi(
        f"r5-{funcion}-{subcomponente}",
        datos["a"],
        funcion,
        subcomponente=subcomponente,
    )

    assert not puede_ver_trabajadores_cdi(user, datos["a"])


def test_trabajador_sin_legajo_vinculado_no_ve(datos):
    assert not puede_ver_trabajadores_cdi(
        _usuario("r5-sin-legajo", TRABAJADOR), datos["a"]
    )


def test_legajo_director_sin_el_grupo_no_alcanza(datos):
    user = _usuario("r5-sin-grupo")
    _legajo(datos["a"], user, "director_coordinador")

    assert not puede_ver_trabajadores_cdi(user, datos["a"])


# R2 — legajo nativo y API web


def test_legajo_oculta_contador_y_tarjeta_sin_la_regla(datos):
    url = reverse("centrodeinfancia_detalle", args=[datos["a"].pk])
    analista = _cliente(_usuario("r2-analista", UserGroups.SIMEPI_ANALISTA_DATOS))
    director = _cliente(
        _trabajador_cdi("r2-director", datos["a"], "director_coordinador")
    )

    oculto = analista.get(url)
    visible = director.get(url)

    assert oculto.status_code == visible.status_code == 200
    assert 'id="tablaTrabajadores"' not in oculto.content.decode()
    assert "<span>Trabajadores</span>" not in oculto.content.decode()
    assert 'id="tablaTrabajadores"' in visible.content.decode()
    assert "Sala, Ana" in visible.content.decode()
    # El director edita pero no elimina (matriz 4.1).
    assert (
        reverse("centrodeinfancia_trabajador_crear", args=[datos["a"].pk])
        in visible.content.decode()
    )
    assert 'data-bs-target="#modalEliminarTrabajador"' not in visible.content.decode()


def test_api_web_del_legajo_manda_null_sin_la_regla(datos):
    url = f"/api/web/cdi/centros/{datos['a'].pk}/"
    analista = _cliente(_usuario("r2-api-analista", UserGroups.SIMEPI_ANALISTA_DATOS))
    auditor = _cliente(_usuario("r2-api-auditor", UserGroups.SIMEPI_AUDITORIA))

    oculto = analista.get(url).json()
    visible = auditor.get(url).json()

    assert oculto["hero"]["trabajadores"] is None
    assert oculto["trabajadores"] is None
    assert visible["hero"]["trabajadores"] == 1
    assert [fila["nombre"] for fila in visible["trabajadores"]["filas"]] == [
        "Sala, Ana"
    ]


# R3 — bloqueo por URL


def _urls(datos):
    pk, t = datos["a"].pk, datos["trabajador_a"].pk
    return {
        "ver": reverse("centrodeinfancia_trabajador_ver", args=[pk, t]),
        "crear": reverse("centrodeinfancia_trabajador_crear", args=[pk]),
        "editar": reverse("centrodeinfancia_trabajador_editar", args=[pk, t]),
    }


def test_sin_la_regla_ficha_alta_y_edicion_responden_404(datos):
    # El docente tiene view/add/change_trabajador por su grupo, pero no la función.
    docente = _cliente(
        _trabajador_cdi("r3-docente", datos["a"], "educador_docente_sala")
    )
    analista = _cliente(_usuario("r3-analista", UserGroups.SIMEPI_ANALISTA_DATOS))

    for nombre, url in _urls(datos).items():
        assert docente.get(url).status_code == 404, nombre
    assert analista.get(_urls(datos)["ver"]).status_code in {403, 404}


def test_director_abre_ficha_alta_y_edicion_de_su_cdi(datos):
    director = _cliente(
        _trabajador_cdi("r3-director", datos["a"], "director_coordinador")
    )

    for nombre, url in _urls(datos).items():
        assert director.get(url).status_code == 200, nombre
    otro_cdi = reverse(
        "centrodeinfancia_trabajador_ver",
        args=[datos["b"].pk, datos["trabajador_b"].pk],
    )
    assert director.get(otro_cdi).status_code == 404


def test_director_no_elimina_trabajadores(datos):
    director = _cliente(
        _trabajador_cdi("r3-director-baja", datos["a"], "director_coordinador")
    )
    url = reverse(
        "centrodeinfancia_trabajador_eliminar",
        args=[datos["a"].pk, datos["trabajador_a"].pk],
    )

    assert director.post(url).status_code == 403
    assert Trabajador.objects.filter(pk=datos["trabajador_a"].pk).exists()


# R4 — reporte Excel


def _hojas(contenido):
    libro = openpyxl.load_workbook(BytesIO(contenido))
    return {
        hoja.title: [list(fila) for fila in hoja.iter_rows(values_only=True)]
        for hoja in libro.worksheets
    }


def test_analista_recibe_la_hoja_trabajadores_vacia_y_sin_filas_en_el_resumen(datos):
    analista = _usuario("r4-analista", UserGroups.SIMEPI_ANALISTA_DATOS)

    hojas = _hojas(generar_reporte_cdi_xlsx(analista))

    assert hojas["Trabajadores"] == [list(COLUMNAS_TRABAJADORES)]
    detalles = [fila[1] for fila in hojas["Resumen"][1:]]
    assert "Trabajadores" not in detalles
    assert "CDI sin trabajadores" not in detalles
    assert "Centros de Desarrollo Infantil" in detalles


def test_auditoria_sigue_viendo_trabajadores_en_el_reporte(datos):
    auditor = _usuario("r4-auditor", UserGroups.SIMEPI_AUDITORIA)

    hojas = _hojas(generar_reporte_cdi_xlsx(auditor))

    assert len(hojas["Trabajadores"]) == 3
    assert ("Totales", "Trabajadores", 2) in [
        tuple(fila) for fila in filas_resumen(auditor)
    ]


# Semilla de grupos (matriz 4.1)


def test_semilla_de_permisos_de_trabajador():
    trabajador = permission_codes_for_bootstrap_group(TRABAJADOR)
    analista = permission_codes_for_bootstrap_group(UserGroups.SIMEPI_ANALISTA_DATOS)

    assert {
        "centrodeinfancia.view_trabajador",
        "centrodeinfancia.add_trabajador",
        "centrodeinfancia.change_trabajador",
    } <= set(trabajador)
    assert "centrodeinfancia.delete_trabajador" not in trabajador
    assert not [code for code in analista if code.endswith("_trabajador")]
