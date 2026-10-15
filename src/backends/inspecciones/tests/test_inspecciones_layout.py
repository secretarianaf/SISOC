"""Layout de Inspecciones en el backoffice: pantalla clara como el mockup.

El resto de SISOC no cambia: sigue en oscuro, con su cabecera azul y su script
que fuerza el tema.
"""

import re
from pathlib import Path

import pytest
from django.urls import reverse

from inspecciones.services.asignaciones import asignaciones_de_jornada
from inspecciones.services.formato import iniciales

from tests.test_inspecciones_panel import _acta_cerrada

pytestmark = pytest.mark.django_db


def test_sisoc_sigue_en_oscuro_fuera_del_layout_claro(panel):
    respuesta = panel.get(reverse("changelog"))

    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    assert 'data-bs-theme="dark"' in html
    assert "bg-body-tertiary dark-mode" in html
    assert 'localStorage.setItem("theme", "dark")' in html
    assert 'class="main-header"' in html
    assert "sidebar-brand" not in html
    assert "insp-cabecera" not in html
    assert re.search(r'<aside class="app-sidebar shadow"\s*>', html)
    # La barra lateral ya no muestra el panel de usuario (va como en Inspecciones).
    assert 'class="nav-item user-info' not in html
    assert "user-panel" not in html


def test_inicio_usa_el_marco_claro(panel):
    html = panel.get(reverse("inicio")).content.decode()

    assert 'data-bs-theme="light"' in html
    assert "bg-body-tertiary insp-cuerpo" in html
    assert '<header class="app-header insp-cabecera">' in html
    assert '<strong aria-current="page">Inicio</strong>' in html
    assert "sidebar-brand" in html
    assert 'class="main-header"' not in html
    assert "sisoc-volver" not in html
    assert "inicio-presentacion" in html


def test_el_helper_de_layout_claro_vive_en_el_kernel():
    from core.services.layout_claro import (
        contexto_layout_claro,
        iniciales as iniciales_core,
    )
    from inspecciones.services.formato import iniciales

    assert iniciales is iniciales_core
    assert contexto_layout_claro.__module__ == "core.services.layout_claro"


def test_iniciales_para_el_avatar():
    assert iniciales("Laura Gómez") == "LG"
    assert iniciales("carla coordinadora sosa") == "CC"
    assert iniciales("lgomez") == "L"
    assert iniciales("") == "?"
    assert iniciales(None) == "?"


def test_panel_sale_en_claro_con_la_cabecera_del_mockup(panel):
    html = panel.get(reverse("inspecciones_panel")).content.decode()

    assert 'data-bs-theme="light"' in html
    assert "bg-body-tertiary insp-cuerpo" in html
    assert 'localStorage.setItem("theme", "dark")' not in html
    assert "sisoc-volver" not in html
    assert 'class="main-header"' not in html
    assert re.search(
        r'<aside class="app-sidebar shadow"\s+data-bs-theme="dark"\s*>', html
    )
    assert "sidebar-brand" in html
    assert '<header class="app-header insp-cabecera">' in html
    assert '<a href="/inicio/">Inicio</a>' in html
    assert '<strong aria-current="page">Inspecciones escolares</strong>' in html
    assert 'aria-label="Cerrar sesión"' in html


def test_tablero_usa_el_mismo_layout(panel):
    html = panel.get(reverse("inspecciones_tablero")).content.decode()

    assert 'data-bs-theme="light"' in html
    assert '<header class="app-header insp-cabecera">' in html
    assert '<a href="/inicio/">Inicio</a>' in html
    assert '<strong aria-current="page">Tablero</strong>' in html
    assert "leaflet@1.9.4/dist/leaflet.js" in html


def test_totales_generales_solo_en_la_pestana_escuelas(panel):
    escuelas = panel.get(reverse("inspecciones_panel")).content.decode()
    asignaciones = panel.get(reverse("inspecciones_asignaciones")).content.decode()
    actas = panel.get(reverse("inspecciones_actas")).content.decode()

    assert "Escuelas en el catálogo" in escuelas
    assert "Escuelas en el catálogo" not in asignaciones
    assert "Escuelas en el catálogo" not in actas


def test_panel_css_no_conserva_el_parche_de_seccion_clara():
    raiz = Path(__file__).resolve().parents[2]
    css = (
        raiz.joinpath("inspecciones", "inspecciones", "static", "inspecciones", "css")
        .joinpath("panel.css")
        .read_text(encoding="utf-8")
    )
    css_layout = raiz.joinpath(
        "kernel", "static", "custom", "css", "layout_claro.css"
    ).read_text(encoding="utf-8")

    assert 'body.dark-mode [data-bs-theme="light"]' not in css
    assert 'body.dark-mode [data-bs-theme="light"]' not in css_layout
    assert ".insp-cuerpo" in css
    assert ".insp-seccion-barra" in css
    # La cabecera blanca pasó al layout claro compartido del kernel.
    assert ".insp-cabecera" in css_layout
    assert ".insp-cabecera" not in css


XHR = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


def _crear_escuelas(panel, geografia, cantidad):
    for i in range(cantidad):
        respuesta = panel.post(
            reverse("inspecciones_escuela_nueva"),
            {
                "provincia": geografia["bsas"].pk,
                "localidad": geografia["san_justo"].pk,
                "cueanexo": f"06012{i:04d}",
                "nombre": f"EP N° {i} Paginada",
                "domicilio": "Av. Perón 3245",
                "cp": "B1754",
                "telefono": "",
                "mail": "",
            },
            **XHR,
        )
        assert respuesta.status_code == 200, respuesta.content


def test_listado_de_escuelas_con_el_pie_y_la_paginacion_del_mockup(panel, geografia):
    _crear_escuelas(panel, geografia, 26)

    html = panel.get(reverse("inspecciones_panel"), {"q": "Paginada"}).content.decode()

    assert "Mostrando 1–25 de 26" in html
    assert 'class="insp-paginacion"' in html
    assert 'href="?q=Paginada&amp;page=2"' in html
    assert '<span class="insp-pagina activa" aria-current="page">1</span>' in html
    assert "Se encontraron" not in html
    assert 'class="insp-seccion-barra"' in html
    assert "card-custom" not in html


def test_fila_de_asignacion_trae_las_iniciales_del_inspector(asignada_a, inspector_a):
    inspector_a.first_name, inspector_a.last_name = "Laura", "Gómez"
    inspector_a.save(update_fields=["first_name", "last_name"])

    filas, _totales = asignaciones_de_jornada(asignada_a.fecha)

    assert filas[0]["iniciales"] == "LG"


def test_asignaciones_con_avatar_y_pie_del_mockup(panel, asignada_a):
    html = panel.get(
        reverse("inspecciones_asignaciones"), {"fecha": asignada_a.fecha.isoformat()}
    ).content.decode()

    assert 'class="insp-avatar" aria-hidden="true"' in html
    assert 'class="insp-jornada"' in html
    assert "Mostrando 1–1 de 1 · 1 inspectores" in html
    assert "Escuelas en el catálogo" not in html
    assert "card-custom" not in html


def test_actas_usa_la_misma_seccion(panel):
    html = panel.get(reverse("inspecciones_actas")).content.decode()

    assert 'class="insp-seccion-barra"' in html
    assert "card-custom" not in html


def test_formulario_de_escuela_como_pagina_va_en_la_caja_del_mockup(panel):
    html = panel.get(reverse("inspecciones_escuela_nueva")).content.decode()

    assert 'class="insp-dialogo"' in html
    assert "card-custom" not in html
    assert "Guardar y cargar otra" in html


def test_aviso_de_escuela_ya_asignada_usa_el_aviso_ambar(panel):
    html = panel.get(reverse("inspecciones_asignacion_nueva"), **XHR).content.decode()

    assert 'class="insp-aviso insp-aviso-ambar d-none"' in html


def test_subir_archivo_de_escuelas_muestra_la_caja_del_mockup(panel):
    html = panel.get(reverse("inspecciones_importar_escuelas")).content.decode()

    assert 'class="insp-dialogo"' in html
    assert 'class="insp-dialogo-cerrar"' in html
    assert 'class="insp-pasos"' in html
    assert "card-custom" not in html


def test_detalle_del_acta_con_el_encabezado_del_mockup(
    panel, api_a, escuela, cerrar, imagen, nuevo_uuid
):
    numero, _imagen_uuid = _acta_cerrada(api_a, escuela, cerrar, imagen, nuevo_uuid)

    html = panel.get(
        reverse("inspecciones_acta_detalle", args=[numero])
    ).content.decode()

    assert 'class="insp-acta-rotulo"' in html
    assert f'<h1 class="insp-acta-numero">{numero}</h1>' in html
    assert 'class="insp-columnas-2-1"' in html
    assert "card-custom" not in html
    assert '<h1 class="insp-titulo">' not in html
    assert "insp-tabs" not in html


def test_tablero_con_filtros_en_una_fila_y_contenedores_de_barras(panel):
    html = panel.get(reverse("inspecciones_tablero")).content.decode()

    assert 'class="insp-seccion-barra insp-filtros"' in html
    assert '<label class="visually-hidden" for="tablero-fecha">Jornada</label>' in html
    assert "data-tablero-turnos" in html
    assert 'data-tablero-presencia="personal"' in html
    assert "card-custom" not in html
    assert 'data-kpi="con_firma"' not in html
    assert 'class="insp-totales insp-totales-5"' in html
    assert 'data-indice="ausentismo-fraccion"' in html
    assert 'data-indice="aulas-fraccion"' in html
    assert 'data-indice="ausentismo-descripcion"' in html
    assert 'data-indice="aulas-descripcion"' in html
    assert re.search(
        r'class="insp-aviso insp-aviso-ambar d-none"\s+role="status"\s+data-indice="ausentismo-aviso-exceso"',
        html,
    )
    assert '<ul class="insp-leyenda-lista" data-tablero-resultados-leyenda>' in html


def test_tablero_no_usa_apexcharts():
    js = (
        Path(__file__)
        .resolve()
        .parents[1]
        .joinpath("inspecciones", "static", "inspecciones", "tablero", "tablero.js")
        .read_text(encoding="utf-8")
    )

    assert "ApexCharts" not in js
    assert "data-tablero-turnos" in js


def test_base_js_respeta_el_tema_claro_que_renderiza_el_servidor():
    """base.js fuerza el oscuro en todo SISOC; una página renderizada en claro
    (Inspecciones) tiene que conservarlo, si no inputs, tablas y modales salen oscuros.
    """
    js = (
        Path(__file__)
        .resolve()
        .parents[2]
        .joinpath("kernel", "static", "custom", "js", "base.js")
        .read_text(encoding="utf-8")
    )

    assert 'getAttribute("data-bs-theme") !== "light"' in js


def test_cabecera_blanca_dentro_de_la_grilla_y_con_el_rol(panel, gestor):
    gestor.profile.inspecciones_rol = "coordinacion"
    gestor.profile.save(update_fields=["inspecciones_rol"])

    html = panel.get(reverse("inspecciones_panel")).content.decode()

    # la cabecera va dentro de .app-wrapper, al lado de la barra lateral (grilla de AdminLTE)
    assert html.index('<div class="app-wrapper">') < html.index(
        '<header class="app-header insp-cabecera">'
    )
    assert 'class="insp-cabecera-rol">Coordinación<' in html
    assert '<nav class="insp-migas" aria-label="Ubicación">' in html
