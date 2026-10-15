"""Layout de Inspecciones en el backoffice: pantalla clara como el mockup.

El resto de SISOC no cambia: sigue en oscuro, con su cabecera azul y su script
que fuerza el tema.
"""

import pytest
from django.urls import reverse

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
