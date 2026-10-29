"""Etapa 5 del #2745: legajo de la organización por programa (B v3).

Plan: docs/plans/2026-T4/2026-10-20-2745-legajo-organizacion-por-programa.md.
"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from comedores.models import Comedor, Programas
from gestion_organizaciones.models import (
    ConvenioProyecto,
    Firmante,
    LineaProyecto,
    ProgramaOrganizacion,
)
from organizaciones.models import (
    ArchivoOrganizacion,
    Organizacion,
    ProyectoOrganizacion,
)
from rendicioncuentasmensual.models import RendicionCuentaMensual

SECOS = RendicionCuentaMensual.LINEA_SECOS
TRADICIONAL = RendicionCuentaMensual.LINEA_TRADICIONAL


@pytest.fixture
def programas(db):
    return SimpleNamespace(
        alco=Programas.objects.create(nombre="Alimentar comunidad"),
        secos=Programas.objects.create(nombre="Abordaje comunitario - Línea Secos"),
        tradicional=Programas.objects.create(
            nombre="Abordaje comunitario - Línea Tradicional"
        ),
    )


@pytest.fixture
def cliente(client, db):
    usuario = User.objects.create_superuser(
        username="admin2745legajo", password="x", email="legajo2745@example.com"
    )
    client.force_login(usuario)
    return client


def _organizacion(nombre, *programas_org):
    organizacion = Organizacion.objects.create(nombre=nombre)
    for programa in programas_org:
        ProgramaOrganizacion.objects.create(
            organizacion=organizacion, programa=programa
        )
    return organizacion


def _proyecto(organizacion, codigo, linea=None):
    proyecto = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo=codigo
    )
    if linea is not None:
        LineaProyecto.objects.create(proyecto=proyecto, programa=linea)
    return proyecto


def _rendicion(numero, linea, **extra):
    return RendicionCuentaMensual.objects.create(
        mes=1,
        anio=2026,
        convenio=f"C-{numero}",
        numero_rendicion=numero,
        linea_programatica=linea,
        **extra,
    )


def _legajo(cliente, organizacion, **parametros):
    respuesta = cliente.get(
        reverse("organizacion_detalle", kwargs={"pk": organizacion.pk}), parametros
    )
    assert respuesta.status_code == 200
    return respuesta


def _html(respuesta):
    return respuesta.content.decode()


# --- Selector de programa y secciones ------------------------------------------


def test_un_programa_muestra_solo_ese_programa(cliente, programas):
    organizacion = _organizacion("Org alco", programas.alco)
    Firmante.objects.create(
        organizacion=organizacion, nombre="Ana", programa=programas.alco
    )
    Comedor.objects.create(
        nombre="Comedor alco", organizacion=organizacion, programa=programas.alco
    )

    respuesta = _legajo(cliente, organizacion)

    assert respuesta.context["programa"] == programas.alco
    assert respuesta.context["es_alimentar"]
    html = _html(respuesta)
    assert "Firmantes · Alimentar comunidad" in html
    assert "Comedor alco" in html
    assert "Documentación de la Organización" in html
    assert "Información del programa" not in html


def test_tres_programas_y_eleccion_por_url(cliente, programas):
    organizacion = _organizacion(
        "Org tres", programas.tradicional, programas.alco, programas.secos
    )
    Firmante.objects.create(
        organizacion=organizacion, nombre="Firmante Secos", programa=programas.secos
    )
    Firmante.objects.create(
        organizacion=organizacion, nombre="Firmante Alco", programa=programas.alco
    )

    primero = _legajo(cliente, organizacion)
    secos = _legajo(cliente, organizacion, programa=programas.secos.pk)

    assert [item["programa"] for item in primero.context["programas"]] == [
        programas.alco,
        programas.secos,
        programas.tradicional,
    ]
    assert primero.context["programa"] == programas.alco
    assert secos.context["programa"] == programas.secos
    assert "Firmante Secos" in _html(secos)
    assert "Firmante Alco" not in _html(secos)
    assert "Documentación de la Organización" not in _html(secos)


@pytest.mark.parametrize("valor", ["999999", "abc", ""])
def test_programa_invalido_usa_el_primero(cliente, programas, valor):
    organizacion = _organizacion("Org inválido", programas.secos)

    respuesta = _legajo(cliente, organizacion, programa=valor)

    assert respuesta.context["programa"] == programas.secos


def test_abordaje_muestra_proyectos_region_convenio_y_territoriales(cliente, programas):
    territorial = User.objects.create_user(
        username="terr2745", first_name="Ana", last_name="Zapata"
    )
    organizacion = _organizacion("Org secos", programas.secos, programas.tradicional)
    secos = _proyecto(organizacion, "S-1", programas.secos)
    _proyecto(organizacion, "T-1", programas.tradicional)
    secos.territoriales.add(territorial)
    ConvenioProyecto.objects.create(
        proyecto=secos,
        numero="0456/2026",
        fecha=date(2026, 3, 1),
        meses=12,
        monto_total=Decimal("1000"),
        componente_alimentario=Decimal("600"),
        componente_gastos_generales=Decimal("200"),
        componente_siph=Decimal("50"),
        componente_gasto_bancario=Decimal("50"),
    )

    html = _html(_legajo(cliente, organizacion, programa=programas.secos.pk))

    assert "Proyectos · Abordaje comunitario - Línea Secos" in html
    assert "S-1" in html
    assert "T-1" not in html
    assert "Zapata, Ana (terr2745)" in html
    assert "Datos de Región" in html
    assert "Convenio 0456/2026" in html
    assert "no coincide con el monto total" in html
    assert "Imprevistos no aplica" in html


def test_rendiciones_por_linea_de_la_rendicion_incluidas_sin_proyecto(
    cliente, programas
):
    organizacion = _organizacion("Org rend", programas.secos, programas.tradicional)
    proyecto = _proyecto(organizacion, "S-1", programas.secos)
    comedor = Comedor.objects.create(
        nombre="Comedor rend", organizacion=organizacion, programa=programas.secos
    )
    _rendicion(1, SECOS, proyecto=proyecto)
    _rendicion(2, SECOS, comedor=comedor)
    _rendicion(3, TRADICIONAL, comedor=comedor)

    respuesta = _legajo(
        cliente, organizacion, programa=programas.secos.pk, seccion="rendiciones"
    )

    assert {r.convenio for r in respuesta.context["rendiciones"]} == {"C-1", "C-2"}
    assert respuesta.context["rendiciones_otras_lineas"] == []
    assert "C-3" not in _html(respuesta)


def test_proyecto_sin_seccion_abre_rendiciones(cliente, programas):
    organizacion = _organizacion("Org filtro", programas.secos)
    proyecto = _proyecto(organizacion, "S-1", programas.secos)
    _proyecto(organizacion, "S-2", programas.secos)
    _rendicion(1, SECOS, proyecto=proyecto)

    respuesta = _legajo(cliente, organizacion, proyecto="S-1")

    assert respuesta.context["seccion"] == "rendiciones"
    assert respuesta.context["proyecto_rendiciones"] == "S-1"
    assert [r.convenio for r in respuesta.context["rendiciones"]] == ["C-1"]


def test_proyecto_sin_programa_abre_la_linea_de_ese_proyecto(cliente, programas):
    # Un enlace viejo `?proyecto=` no cae en Alimentar, que va primero.
    organizacion = _organizacion(
        "Org enlace viejo", programas.alco, programas.tradicional
    )
    proyecto = _proyecto(organizacion, "T-1", programas.tradicional)
    _rendicion(1, TRADICIONAL, proyecto=proyecto)

    respuesta = _legajo(cliente, organizacion, proyecto="T-1")

    assert respuesta.context["programa"] == programas.tradicional
    assert respuesta.context["seccion"] == "rendiciones"
    assert [r.convenio for r in respuesta.context["rendiciones"]] == ["C-1"]


def test_filtro_ofrece_los_mismos_codigos_que_el_legajo_anterior(cliente, programas):
    organizacion = _organizacion("Org códigos", programas.secos)
    _proyecto(organizacion, "S-1", programas.secos)
    comedor = Comedor.objects.create(
        nombre="Comedor con código", organizacion=organizacion, programa=programas.secos
    )
    Comedor.objects.filter(pk=comedor.pk).update(codigo_de_proyecto="VIEJO-1")

    respuesta = _legajo(cliente, organizacion, seccion="rendiciones")

    assert respuesta.context["codigos_rendiciones"] == ["S-1", "VIEJO-1"]


def test_sin_abordaje_el_filtro_sigue_visible_sin_resultados(cliente, programas):
    organizacion = _organizacion("Org sin abordaje filtro", programas.alco)
    proyecto = _proyecto(organizacion, "P-1")
    _proyecto(organizacion, "P-2")
    _rendicion(1, "", proyecto=proyecto)

    html = _html(_legajo(cliente, organizacion, proyecto="P-2"))

    assert "No hay rendiciones presentadas para la selección actual." in html
    assert 'value="P-1"' in html


def test_sin_programas_se_pueden_agregar_firmantes(cliente, programas):
    organizacion = _organizacion("Org sin programas firmantes")
    Comedor.objects.create(nombre="Comedor suelto", organizacion=organizacion)

    respuesta = _legajo(cliente, organizacion)

    html = _html(respuesta)
    assert reverse("firmante_crear", args=[organizacion.pk]) in html
    assert respuesta.context["comedores_count"] == 1
    assert 'id="documentacion"' in html


@pytest.mark.parametrize("con_archivo", [True, False])
def test_documentacion_sin_alimentar_se_ve_si_tiene_archivos(
    cliente, programas, con_archivo
):
    organizacion = _organizacion("Org docs sin alimentar", programas.secos)
    if con_archivo:
        ArchivoOrganizacion.objects.create(
            organizacion=organizacion, archivo="organizaciones/documentacion/a.pdf"
        )

    respuesta = _legajo(cliente, organizacion)

    assert respuesta.context["muestra_documentacion"] is con_archivo


def test_sin_permiso_de_gestion_no_ve_botones(cliente, programas, mocker):
    # Mismo criterio que el legajo anterior: los botones dependen de
    # `puede_gestionar_organizaciones`; el #2745 no cambia permisos. Simula
    # un usuario de la dupla, que ve la organización sin poder gestionarla.
    mocker.patch(
        "gestion_organizaciones.views._filtrar_organizaciones_por_dupla",
        side_effect=lambda queryset, _usuario: queryset,
    )
    mocker.patch(
        "gestion_organizaciones.views._puede_ver_todas_las_organizaciones",
        return_value=False,
    )
    organizacion = _organizacion("Org lectura", programas.secos)
    _proyecto(organizacion, "S-1", programas.secos)

    html = _html(_legajo(cliente, organizacion))

    assert "Agregar Firmante" not in html
    assert reverse("organizacion_editar", args=[organizacion.pk]) not in html
    assert "Cargar convenio" not in html


# --- Casos especiales y su resolución ------------------------------------------


def test_caso_1_sin_programas_y_al_cargarlos_se_normaliza(cliente, programas):
    organizacion = _organizacion("Org sin programas")

    antes = _html(_legajo(cliente, organizacion))
    ProgramaOrganizacion.objects.create(
        organizacion=organizacion, programa=programas.alco
    )
    despues = _html(_legajo(cliente, organizacion))

    assert "Sin programas asignados" in antes
    assert "Sin programas asignados" not in despues
    assert "Firmantes · Alimentar comunidad" in despues


def test_caso_2_sin_programa_asignado_y_al_asignarlo_se_normaliza(cliente, programas):
    organizacion = _organizacion("Org caso 2", programas.alco)
    firmante = Firmante.objects.create(organizacion=organizacion, nombre="Raúl Ortega")
    comedor = Comedor.objects.create(
        nombre="Merendero Las Lomas",
        organizacion=organizacion,
        programa=programas.secos,
    )

    antes = _legajo(cliente, organizacion)
    firmante.programa = programas.alco
    firmante.save()
    comedor.programa = programas.alco
    comedor.save()
    despues = _legajo(cliente, organizacion)

    assert antes.context["sin_programa"]["firmantes"] == [firmante]
    assert antes.context["sin_programa"]["comedores"] == [comedor]
    assert "Sin programa asignado" in _html(antes)
    assert "Sin programa asignado" not in _html(despues)
    assert despues.context["firmantes"] == [firmante]
    assert despues.context["comedores"] == [comedor]


def test_caso_3_proyecto_sin_linea_y_al_asignarla_se_normaliza(cliente, programas):
    organizacion = _organizacion("Org caso 3", programas.secos)
    proyecto = _proyecto(organizacion, "AC-MIXTO")

    antes = _legajo(cliente, organizacion)
    LineaProyecto.objects.create(proyecto=proyecto, programa=programas.secos)
    despues = _legajo(cliente, organizacion)

    assert antes.context["proyectos_sin_linea"] == [proyecto]
    assert "sin línea" in _html(antes)
    assert despues.context["proyectos_sin_linea"] == []
    assert despues.context["proyectos"] == [proyecto]


def test_caso_4_rendiciones_de_otras_lineas_y_al_cargar_la_linea_se_normaliza(
    cliente, programas
):
    organizacion = _organizacion("Org caso 4", programas.tradicional)
    proyecto = _proyecto(organizacion, "AC-0456")
    rendicion = _rendicion(3, SECOS, proyecto=proyecto)

    antes = _legajo(
        cliente,
        organizacion,
        programa=programas.tradicional.pk,
        seccion="rendiciones",
    )
    ProgramaOrganizacion.objects.create(
        organizacion=organizacion, programa=programas.secos
    )
    despues = _legajo(
        cliente, organizacion, programa=programas.secos.pk, seccion="rendiciones"
    )

    assert antes.context["rendiciones_otras_lineas"] == [rendicion]
    assert "Rendiciones de otras líneas" in _html(antes)
    assert despues.context["rendiciones_otras_lineas"] == []
    assert list(despues.context["rendiciones"]) == [rendicion]


def test_sin_abordaje_muestra_proyectos_region_y_rendiciones(cliente, programas):
    organizacion = _organizacion("Org solo alco", programas.alco)
    proyecto = _proyecto(organizacion, "P-1")
    _rendicion(1, TRADICIONAL, proyecto=proyecto)

    respuesta = _legajo(cliente, organizacion)

    assert respuesta.context["abordaje_sin_programa"]["proyectos"] == [proyecto]
    assert [r.convenio for r in respuesta.context["rendiciones_generales"]] == ["C-1"]
    assert "no tiene cargada Línea Secos ni Línea Tradicional" in _html(respuesta)


# --- No pérdida ---------------------------------------------------------------


def test_todo_dato_de_la_organizacion_aparece_en_algun_lugar(cliente, programas):
    """Recorre todos los programas y secciones: nada queda sin lugar."""
    organizacion = _organizacion("Org completa", programas.alco, programas.secos)
    proyectos = [
        _proyecto(organizacion, "S-1", programas.secos),
        _proyecto(organizacion, "T-1", programas.tradicional),
        _proyecto(organizacion, "X-1"),
    ]
    firmantes = [
        Firmante.objects.create(
            organizacion=organizacion, nombre="F alco", programa=programas.alco
        ),
        Firmante.objects.create(
            organizacion=organizacion, nombre="F trad", programa=programas.tradicional
        ),
        Firmante.objects.create(organizacion=organizacion, nombre="F sin"),
    ]
    comedores = [
        Comedor.objects.create(
            nombre="C secos", organizacion=organizacion, programa=programas.secos
        ),
        Comedor.objects.create(nombre="C sin", organizacion=organizacion),
    ]
    rendiciones = [
        _rendicion(1, SECOS, proyecto=proyectos[0]),
        _rendicion(2, TRADICIONAL, proyecto=proyectos[1]),
        _rendicion(3, "", comedor=comedores[0]),
    ]

    vistos = {"firmantes": set(), "comedores": set(), "rendiciones": set()}
    proyectos_vistos = set()
    for programa in (programas.alco, programas.secos):
        for seccion in ("info", "rendiciones"):
            contexto = _legajo(
                cliente, organizacion, programa=programa.pk, seccion=seccion
            ).context
            vistos["firmantes"].update(contexto["firmantes"])
            vistos["firmantes"].update(contexto["sin_programa"]["firmantes"])
            vistos["comedores"].update(contexto["comedores"])
            vistos["comedores"].update(contexto["sin_programa"]["comedores"])
            vistos["rendiciones"].update(contexto.get("rendiciones") or [])
            vistos["rendiciones"].update(contexto["rendiciones_otras_lineas"])
            proyectos_vistos.update(contexto.get("proyectos") or [])
            proyectos_vistos.update(contexto.get("proyectos_sin_linea") or [])

    assert vistos["firmantes"] == set(firmantes)
    assert vistos["comedores"] == set(comedores)
    assert vistos["rendiciones"] == set(rendiciones)
    # T-1 es de Tradicional, que la organización no tiene: aparece en el
    # aviso de proyectos sin línea, junto a X-1.
    assert proyectos_vistos == set(proyectos)
