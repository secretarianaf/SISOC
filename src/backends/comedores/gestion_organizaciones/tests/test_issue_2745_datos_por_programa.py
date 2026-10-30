"""Etapa 1 del #2745: modelos, carga inicial, región y auditoría.

Plan: docs/plans/2026-T4/2026-10-20-2745-legajo-organizacion-por-programa.md.
"""

import importlib
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from functools import lru_cache
from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.migrations.loader import MigrationLoader
from django.db.models import ProtectedError

from comedores.models import Comedor, Programas
from comedores.utils import (
    es_programa_linea_secos,
    es_programa_linea_tradicional,
    is_abordaje_comunitario_linea_secos_program,
    is_abordaje_comunitario_linea_tradicional_program,
)
from gestion_organizaciones.models import (
    ConvenioProyecto,
    LineaProyecto,
    ProgramaOrganizacion,
)
from organizaciones.models import (
    Organizacion,
    ProyectoOrganizacion,
    RegionAbordajeComunitario,
    SubzonaAbordajeComunitario,
)

retiro_region = importlib.import_module(
    "gestion_organizaciones.migrations.0005_region_desde_issue_2642"
)
carga_inicial = importlib.import_module(
    "gestion_organizaciones.migrations.0004_carga_inicial_programas_lineas"
)


@lru_cache(maxsize=None)
def _apps_de(migracion):
    """Modelos históricos que recibe el RunPython de ``migracion``.

    Prueba la migración contra el estado en que corre, no contra los modelos
    actuales: si un modelo cambia después, el test lo detecta.
    """
    loader = MigrationLoader(None, ignore_no_migrations=True)
    return loader.project_state(
        ("gestion_organizaciones", migracion), at_end=False
    ).apps


def _correr_carga_inicial():
    carga_inicial.carga_inicial(_apps_de("0004_carga_inicial_programas_lineas"), None)


NOMBRE_ALCO = "Alimentar comunidad"
NOMBRE_SECOS = "Abordaje comunitario - Línea Secos"
NOMBRE_TRADICIONAL = "Abordaje comunitario - Línea Tradicional"


@pytest.fixture
def programas(db):
    return SimpleNamespace(
        alco=Programas.objects.create(nombre=NOMBRE_ALCO),
        secos=Programas.objects.create(nombre=NOMBRE_SECOS),
        tradicional=Programas.objects.create(nombre=NOMBRE_TRADICIONAL),
        pnud=Programas.objects.create(nombre="PNUD Prog1"),
    )


def _convenio(proyecto, **extra):
    datos = {
        "proyecto": proyecto,
        "numero": "0123/2026",
        "fecha": date(2026, 3, 1),
        "meses": 12,
        "monto_total": Decimal("12000000"),
        "componente_alimentario": Decimal("9000000"),
        "componente_gastos_generales": Decimal("1800000"),
        "componente_siph": Decimal("900000"),
        "componente_gasto_bancario": Decimal("120000"),
    }
    datos.update(extra)
    return ConvenioProyecto(**datos)


# --- comedores.utils: variantes que reciben un programa ---------------------


@pytest.mark.parametrize(
    "nombre, secos, tradicional",
    [
        (NOMBRE_SECOS, True, False),
        (NOMBRE_TRADICIONAL, False, True),
        ("ABORDAJE COMUNITARIO - LINEA SECOS", True, False),
        (NOMBRE_ALCO, False, False),
        ("PNUD Prog1", False, False),
        ("", False, False),
    ],
)
def test_variantes_por_programa_equivalen_a_las_de_comedor(nombre, secos, tradicional):
    programa = SimpleNamespace(nombre=nombre)
    comedor = SimpleNamespace(programa=programa)

    assert es_programa_linea_secos(programa) is secos
    assert es_programa_linea_tradicional(programa) is tradicional
    assert is_abordaje_comunitario_linea_secos_program(comedor) is secos
    assert is_abordaje_comunitario_linea_tradicional_program(comedor) is tradicional


def test_variantes_toleran_programa_ausente():
    assert es_programa_linea_secos(None) is False
    assert (
        is_abordaje_comunitario_linea_tradicional_program(
            SimpleNamespace(programa=None)
        )
        is False
    )


# --- Modelos -----------------------------------------------------------------


@pytest.mark.django_db
def test_programa_organizacion_es_unico_por_par(programas):
    organizacion = Organizacion.objects.create(nombre="Org única")
    ProgramaOrganizacion.objects.create(
        organizacion=organizacion, programa=programas.alco
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        ProgramaOrganizacion.objects.create(
            organizacion=organizacion, programa=programas.alco
        )


@pytest.mark.django_db
def test_no_se_borra_en_cascada_un_programa_con_organizaciones(programas):
    organizacion = Organizacion.objects.create(nombre="Org protegida")
    ProgramaOrganizacion.objects.create(
        organizacion=organizacion, programa=programas.secos
    )

    with pytest.raises(ProtectedError):
        programas.secos.delete()
    assert ProgramaOrganizacion.objects.filter(organizacion=organizacion).count() == 1


@pytest.mark.django_db
def test_linea_de_proyecto_solo_acepta_secos_o_tradicional(programas):
    organizacion = Organizacion.objects.create(nombre="Org línea")
    proyecto = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo="AC-1"
    )

    with pytest.raises(ValidationError):
        LineaProyecto(proyecto=proyecto, programa=programas.alco).clean()
    LineaProyecto(proyecto=proyecto, programa=programas.secos).clean()


@pytest.mark.django_db
def test_linea_de_proyecto_exige_programa_de_la_organizacion_si_tiene_programas(
    programas,
):
    organizacion = Organizacion.objects.create(nombre="Org con programas")
    proyecto = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo="AC-2"
    )
    # Sin programas cargados no se exige nada (definición 22).
    LineaProyecto(proyecto=proyecto, programa=programas.tradicional).clean()

    ProgramaOrganizacion.objects.create(
        organizacion=organizacion, programa=programas.secos
    )
    with pytest.raises(ValidationError):
        LineaProyecto(proyecto=proyecto, programa=programas.tradicional).clean()
    LineaProyecto(proyecto=proyecto, programa=programas.secos).clean()


@pytest.mark.django_db
def test_imprevistos_solo_en_linea_tradicional(programas):
    organizacion = Organizacion.objects.create(nombre="Org convenio")
    secos = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo="AC-S"
    )
    tradicional = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo="AC-T"
    )
    sin_linea = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo="AC-X"
    )
    LineaProyecto.objects.create(proyecto=secos, programa=programas.secos)
    LineaProyecto.objects.create(proyecto=tradicional, programa=programas.tradicional)

    with pytest.raises(ValidationError):
        _convenio(secos, imprevistos=Decimal("1000")).clean()
    with pytest.raises(ValidationError):
        _convenio(sin_linea, imprevistos=Decimal("1000")).clean()
    _convenio(tradicional, imprevistos=Decimal("1000")).clean()
    _convenio(secos).clean()


@pytest.mark.django_db
def test_linea_no_pasa_a_secos_si_el_convenio_tiene_imprevistos(programas):
    organizacion = Organizacion.objects.create(nombre="Org cambio de línea")
    proyecto = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo="AC-C"
    )
    linea = LineaProyecto.objects.create(
        proyecto=proyecto, programa=programas.tradicional
    )
    convenio = _convenio(proyecto, imprevistos=Decimal("1000"))
    convenio.save()

    linea.programa = programas.secos
    with pytest.raises(ValidationError):
        linea.clean()

    convenio.imprevistos = None
    convenio.save()
    linea.clean()


# --- Migración 0005: región del #2642 ----------------------------------------


@contextmanager
def _tablas_region_propia():
    """Recrea las tablas de la Etapa 1, que la 0005 borra, para probar la copia."""
    apps = _apps_de("0005_region_desde_issue_2642")
    modelos = [
        apps.get_model("gestion_organizaciones", nombre)
        for nombre in ("RegionAbordaje", "SubzonaAbordaje", "DatosRegionOrganizacion")
    ]
    with connection.schema_editor() as editor:
        for modelo in modelos:
            editor.create_model(modelo)
    try:
        yield SimpleNamespace(
            apps=apps, region=modelos[0], subzona=modelos[1], datos=modelos[2]
        )
    finally:
        with connection.schema_editor() as editor:
            for modelo in reversed(modelos):
                editor.delete_model(modelo)


def _correr_retiro_region(apps):
    retiro_region.copiar_region_al_2642(apps, SimpleNamespace(connection=connection))


@pytest.mark.django_db(transaction=True)
def test_retiro_region_copia_catalogo_y_datos_al_2642_incluidas_bajas():
    noa = RegionAbordajeComunitario.objects.create(nombre="NOA")
    salta = SubzonaAbordajeComunitario.objects.create(nombre="SALTA", region=noa)
    con_datos = Organizacion.objects.create(nombre="Org con región")
    dada_de_baja = Organizacion.objects.create(nombre="Org dada de baja")
    dada_de_baja.delete()
    ya_cargada = Organizacion.objects.create(
        nombre="Org ya cargada", region_abordaje=noa, subzona_abordaje=salta
    )

    with _tablas_region_propia() as propia:
        noa_propia = propia.region.objects.create(nombre="NOA")
        nueva = propia.region.objects.create(nombre="REGION AGREGADA A MANO")
        salta_propia = propia.subzona.objects.create(region=noa_propia, nombre="SALTA")
        zona_nueva = propia.subzona.objects.create(region=nueva, nombre="ZONA NUEVA")
        # Sin organizaciones: no se copia al catálogo del kernel.
        sin_uso = propia.region.objects.create(nombre="REGION SIN USO")
        propia.subzona.objects.create(region=sin_uso, nombre="ZONA SIN USO")
        propia.subzona.objects.create(region=noa_propia, nombre="ORAN SIN USO")
        propia.datos.objects.create(
            organizacion_id=con_datos.pk, region=nueva, subzona=zona_nueva
        )
        propia.datos.objects.create(
            organizacion_id=dada_de_baja.pk, region=noa_propia, subzona=salta_propia
        )
        propia.datos.objects.create(
            organizacion_id=ya_cargada.pk, region=noa_propia, subzona=salta_propia
        )

        _correr_retiro_region(propia.apps)

    zona_kernel = SubzonaAbordajeComunitario.objects.get(nombre="ZONA NUEVA")
    assert zona_kernel.region.nombre == "REGION AGREGADA A MANO"
    assert RegionAbordajeComunitario.objects.count() == 2
    assert not SubzonaAbordajeComunitario.objects.filter(
        nombre__in=["ZONA SIN USO", "ORAN SIN USO"]
    ).exists()
    con_datos.refresh_from_db()
    assert (con_datos.region_abordaje, con_datos.subzona_abordaje) == (
        zona_kernel.region,
        zona_kernel,
    )
    baja = Organizacion._base_manager.get(pk=dada_de_baja.pk)
    assert (baja.region_abordaje, baja.subzona_abordaje) == (noa, salta)
    ya_cargada.refresh_from_db()
    assert (ya_cargada.region_abordaje, ya_cargada.subzona_abordaje) == (noa, salta)


@pytest.mark.django_db(transaction=True)
def test_retiro_region_se_frena_si_pisaria_un_dato_distinto():
    centro = RegionAbordajeComunitario.objects.create(nombre="CENTRO")
    noa = RegionAbordajeComunitario.objects.create(nombre="NOA")
    SubzonaAbordajeComunitario.objects.create(nombre="SALTA", region=centro)
    organizacion = Organizacion.objects.create(
        nombre="Org con otra región", region_abordaje=centro
    )

    with _tablas_region_propia() as propia:
        noa_propia = propia.region.objects.create(nombre="NOA")
        salta_propia = propia.subzona.objects.create(region=noa_propia, nombre="SALTA")
        propia.datos.objects.create(
            organizacion_id=organizacion.pk, region=noa_propia, subzona=salta_propia
        )

        with pytest.raises(retiro_region.RegionNoCopiable) as error:
            _correr_retiro_region(propia.apps)

    assert "SALTA" in str(error.value)
    assert "Org con otra región" in str(error.value)
    organizacion.refresh_from_db()
    assert organizacion.region_abordaje == centro
    assert organizacion.subzona_abordaje is None
    assert noa.subzonas.count() == 0


# --- Migración de carga inicial ----------------------------------------------


def _snapshot():
    return {
        "comedores": sorted(
            Comedor._base_manager.values_list(
                "pk", "organizacion_id", "programa_id", "proyecto_id", "deleted_at"
            )
        ),
        "proyectos": sorted(
            ProyectoOrganizacion._base_manager.values_list(
                "pk", "organizacion_id", "codigo", "activo"
            )
        ),
        "organizaciones": sorted(
            Organizacion._base_manager.values_list("pk", "nombre")
        ),
    }


@pytest.fixture
def escenario(programas):
    org_a = Organizacion.objects.create(nombre="Org A")
    org_b = Organizacion.objects.create(nombre="Org B sin comedores")

    p_secos = ProyectoOrganizacion.objects.create(organizacion=org_a, codigo="P-SECOS")
    p_mixto = ProyectoOrganizacion.objects.create(organizacion=org_a, codigo="P-MIXTO")
    p_alco = ProyectoOrganizacion.objects.create(organizacion=org_a, codigo="P-ALCO")
    p_vacio = ProyectoOrganizacion.objects.create(organizacion=org_a, codigo="P-VACIO")
    p_manual = ProyectoOrganizacion.objects.create(
        organizacion=org_a, codigo="P-MANUAL"
    )

    Comedor.objects.create(nombre="A alco", organizacion=org_a, programa=programas.alco)
    Comedor.objects.create(
        nombre="A secos 1",
        organizacion=org_a,
        programa=programas.secos,
        proyecto=p_secos,
    )
    baja = Comedor.objects.create(
        nombre="A secos baja",
        organizacion=org_a,
        programa=programas.secos,
        proyecto=p_secos,
    )
    baja.delete()
    Comedor.objects.create(
        nombre="A mixto secos",
        organizacion=org_a,
        programa=programas.secos,
        proyecto=p_mixto,
    )
    Comedor.objects.create(
        nombre="A mixto trad",
        organizacion=org_a,
        programa=programas.tradicional,
        proyecto=p_mixto,
    )
    Comedor.objects.create(
        nombre="A proyecto alco",
        organizacion=org_a,
        programa=programas.alco,
        proyecto=p_alco,
    )
    Comedor.objects.create(nombre="A pnud", organizacion=org_a, programa=programas.pnud)
    Comedor.objects.create(
        nombre="A manual",
        organizacion=org_a,
        programa=programas.secos,
        proyecto=p_manual,
    )
    LineaProyecto.objects.create(proyecto=p_manual, programa=programas.tradicional)

    return SimpleNamespace(
        org_a=org_a,
        org_b=org_b,
        p_secos=p_secos,
        p_mixto=p_mixto,
        p_alco=p_alco,
        p_vacio=p_vacio,
        p_manual=p_manual,
        programas=programas,
    )


@pytest.mark.django_db
def test_carga_inicial_programas_incluye_bajas_y_otros_programas(escenario):
    _correr_carga_inicial()

    programas = escenario.programas
    asignados = set(
        ProgramaOrganizacion.objects.filter(organizacion=escenario.org_a).values_list(
            "programa_id", flat=True
        )
    )
    # Secos llega también por el comedor dado de baja; PNUD no es de los tres.
    assert asignados == {
        programas.alco.pk,
        programas.secos.pk,
        programas.tradicional.pk,
        programas.pnud.pk,
    }
    assert not ProgramaOrganizacion.objects.filter(
        organizacion=escenario.org_b
    ).exists()


@pytest.mark.django_db
def test_carga_inicial_programas_solo_por_comedor_dado_de_baja(programas):
    organizacion = Organizacion.objects.create(nombre="Org solo bajas")
    comedor = Comedor.objects.create(
        nombre="Baja", organizacion=organizacion, programa=programas.tradicional
    )
    comedor.delete()

    _correr_carga_inicial()

    assert ProgramaOrganizacion.objects.filter(
        organizacion=organizacion, programa=programas.tradicional
    ).exists()


@pytest.mark.django_db
def test_carga_inicial_asigna_linea_solo_sin_ambiguedad(escenario):
    _correr_carga_inicial()

    lineas = dict(LineaProyecto.objects.values_list("proyecto_id", "programa_id"))
    assert lineas[escenario.p_secos.pk] == escenario.programas.secos.pk
    assert escenario.p_mixto.pk not in lineas
    assert escenario.p_alco.pk not in lineas
    assert escenario.p_vacio.pk not in lineas
    # La línea cargada a mano no se pisa.
    assert lineas[escenario.p_manual.pk] == escenario.programas.tradicional.pk


@pytest.mark.django_db
def test_carga_inicial_no_modifica_datos_existentes_y_es_idempotente(escenario):
    antes = _snapshot()

    _correr_carga_inicial()
    programas_tras_primera = ProgramaOrganizacion.objects.count()
    lineas_tras_primera = LineaProyecto.objects.count()
    _correr_carga_inicial()

    assert _snapshot() == antes
    assert ProgramaOrganizacion.objects.count() == programas_tras_primera
    assert LineaProyecto.objects.count() == lineas_tras_primera


def test_log_de_proyectos_sin_linea_va_en_tandas_sin_perder_ids(mocker):
    mocker.patch.object(carga_inicial, "IDS_POR_LINEA_DE_LOG", 2)
    logger = mocker.patch.object(carga_inicial, "logger")

    carga_inicial._loguear_ids(  # pylint: disable=protected-access
        "ambigüedad", [1, 2, 3, 4, 5]
    )

    tandas = [llamada.args[2:] for llamada in logger.warning.call_args_list]
    assert tandas == [(1, 2, 5, [1, 2]), (3, 4, 5, [3, 4]), (5, 5, 5, [5])]


# --- Auditoría -----------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_auditoria_registra_altas_y_cambios(programas, mocker):
    registrar = mocker.patch("gestion_organizaciones.audit_signals.registrar_evento")
    organizacion = Organizacion.objects.create(nombre="Org auditada")
    proyecto = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo="AC-A"
    )

    ProgramaOrganizacion.objects.create(
        organizacion=organizacion, programa=programas.secos
    )
    linea = LineaProyecto.objects.create(proyecto=proyecto, programa=programas.secos)
    linea.programa = programas.tradicional
    linea.save()

    llamadas = [llamada.args for llamada in registrar.call_args_list]
    assert all(args[0] == organizacion for args in llamadas)
    assert any("Programa" in args[1] for args in llamadas)
    assert any("Línea de proyecto" in args[1] for args in llamadas)
    assert any(
        any(clave.startswith("Línea de proyecto:") for clave in args[1])
        for args in llamadas
    )
