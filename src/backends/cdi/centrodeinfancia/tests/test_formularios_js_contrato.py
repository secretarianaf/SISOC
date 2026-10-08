"""Contrato entre los formularios CDI renderizados y su JavaScript.

Los campos condicionales (pueblo originario, discapacidad, CUD, funciones por
subcomponente) se muestran por JS. Si el JS busca un id que el template no
genera, la fila queda oculta y el modelo rechaza el guardado sin que se vea el
error: así se perdió el dato "Indígena" en la nómina de niños. Estos tests
renderizan cada formulario y verifican que existan todos los ids que su JS usa.
"""

import re
from datetime import date, timedelta
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from centrodeinfancia.models import CentroDeInfancia
from ciudadanos.models import Ciudadano
from core.models import Provincia


JS_DIR = Path(__file__).resolve().parent.parent / "static" / "custom" / "js"
PATRON_IDS_JS = re.compile(
    r"getElementById\(\s*[\"']([\w-]+)[\"']\s*\)"
    r"|querySelector(?:All)?\(\s*[\"']#([\w-]+)"
)


def _ids_usados_por(js_nombre):
    contenido = (JS_DIR / js_nombre).read_text(encoding="utf-8")
    return {a or b for a, b in PATRON_IDS_JS.findall(contenido)}


def _ids_renderizados(html):
    return set(re.findall(r'\bid="([\w-]+)"', html))


@pytest.fixture
def centro():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    return CentroDeInfancia.objects.create(
        nombre="CDI Contrato JS", provincia=provincia
    )


@pytest.fixture
def cliente_super(client):
    user = User.objects.create_user(
        username="contrato-js", password="x", is_superuser=True, is_staff=True
    )
    client.force_login(user)
    return client


def _html_alta(cliente, url_name, centro, edad_anios):
    """Alta con un ciudadano elegido, que es cuando la vista muestra el form."""
    ciudadano = Ciudadano.objects.create(
        apellido="Ramirez",
        nombre="Sofia",
        fecha_nacimiento=date.today() - timedelta(days=365 * edad_anios),
        documento=44555666,
    )
    url = reverse(url_name, kwargs={"pk": centro.pk})
    respuesta = cliente.get(f"{url}?ciudadano_id={ciudadano.pk}")
    assert respuesta.status_code == 200
    assert respuesta.context.get("mostrar_formulario")
    return respuesta.content.decode("utf-8")


def _html_alta_nino(cliente, centro):
    return _html_alta(cliente, "centrodeinfancia_nomina_crear", centro, 2)


def _html_alta_trabajador(cliente, centro):
    return _html_alta(cliente, "centrodeinfancia_trabajador_crear", centro, 30)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("js_nombre", "renderizar"),
    [
        ("destinatarioForm.js", _html_alta_nino),
        ("trabajadorForm.js", _html_alta_trabajador),
    ],
    ids=["ninos", "trabajadores"],
)
def test_todos_los_ids_que_usa_el_js_existen_en_el_formulario(
    cliente_super, centro, js_nombre, renderizar
):
    ids_js = _ids_usados_por(js_nombre)
    assert ids_js, f"No se detectaron ids en {js_nombre}: revisar el patrón."

    faltantes = ids_js - _ids_renderizados(renderizar(cliente_super, centro))

    assert (
        not faltantes
    ), f"{js_nombre} busca ids que el formulario no renderiza: {sorted(faltantes)}"
