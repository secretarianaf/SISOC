"""Botón "Consultas" (Mesa de Ayuda) de ``includes/header.html`` según la sección.

CDI tiene su canal; Situación de Calle (dispositivos y datacalle) el suyo
(#2938). El resto de SISOC no muestra el botón.
"""

from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory

CDI = "https://consultas.capitalhumano.gob.ar/canales/sisoc-cdi"
SITUACION_CALLE = (
    "https://consultas.capitalhumano.gob.ar/canales/equipo-situacion-de-calle"
)


def _header(route):
    request = RequestFactory().get("/")
    request.user = AnonymousUser()
    request.resolver_match = SimpleNamespace(route=route)
    return render_to_string("includes/header.html", {"request": request})


@pytest.mark.parametrize(
    "route",
    [
        "dispositivos/",
        "dispositivos/<int:pk>/",
        "dispositivos/mapa/",
        "datacalle/relevamientos/",
        "datacalle/relevamientos/<uuid:pk>/",
        "datacalle/casos/<uuid:pk>/",
    ],
)
def test_situacion_de_calle_muestra_su_mesa_de_ayuda(route):
    html = _header(route)

    assert f'href="{SITUACION_CALLE}"' in html
    assert CDI not in html
    assert 'target="_blank"' in html


def test_cdi_mantiene_su_canal():
    html = _header("centrodeinfancia/listar")

    assert f'href="{CDI}"' in html
    assert SITUACION_CALLE not in html


@pytest.mark.parametrize("route", ["comedores/", "inicio/", ""])
def test_el_resto_no_muestra_consultas(route):
    html = _header(route)

    assert "consultas.capitalhumano.gob.ar" not in html
