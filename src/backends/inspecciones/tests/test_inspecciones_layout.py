"""Layout de Inspecciones en el backoffice: pantalla clara como el mockup.

El resto de SISOC no cambia: sigue en oscuro, con su cabecera azul y su script
que fuerza el tema.
"""

from pathlib import Path

import pytest
from django.urls import reverse

from inspecciones.services.formato import iniciales

pytestmark = pytest.mark.django_db


def test_sisoc_sigue_en_oscuro_fuera_de_inspecciones(panel):
    respuesta = panel.get(reverse("inicio"))

    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    assert 'data-bs-theme="dark"' in html
    assert "bg-body-tertiary dark-mode" in html
    assert 'localStorage.setItem("theme", "dark")' in html
    assert 'class="main-header"' in html
    assert "sidebar-brand" not in html
    assert "insp-cabecera" not in html


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
    assert '<aside class="app-sidebar shadow" data-bs-theme="dark">' in html
    assert "sidebar-brand" in html
    assert 'class="app-header navbar insp-cabecera"' in html
    assert '<a href="/inicio/">Inicio</a>' in html
    assert '<strong aria-current="page">Inspecciones escolares</strong>' in html
    assert 'aria-label="Cerrar sesión"' in html


def test_tablero_usa_el_mismo_layout(panel):
    html = panel.get(reverse("inspecciones_tablero")).content.decode()

    assert 'data-bs-theme="light"' in html
    assert 'class="app-header navbar insp-cabecera"' in html
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
    css = Path(__file__).resolve().parents[1].joinpath(
        "inspecciones", "static", "inspecciones", "css", "panel.css"
    ).read_text(encoding="utf-8")

    assert 'body.dark-mode [data-bs-theme="light"]' not in css
    assert ".insp-cuerpo" in css
    assert ".insp-cabecera" in css
    assert ".insp-seccion-barra" in css
