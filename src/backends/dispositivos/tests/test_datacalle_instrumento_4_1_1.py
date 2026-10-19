"""Instrumento DataCalle 4.1.1: "Programa Local / Provincial" en la 25, #2724.

El área reemplaza la subopción de "Programa Social" "Volver al trabajo" por
"Programa Local / Provincial". La app usa un código nuevo
(`programaLocalProvincial`) y retira `volverAlTrabajo`, que los casos ya
guardados conservan. Sin la copia nueva la ficha mostraría la clave cruda.
"""

import pytest

from datacalle.models import Encuesta
from datacalle.services.instrumento import (
    get_catalogos,
    get_version,
    respuestas_legibles,
)


def _valor(encuesta, clave):
    for pagina in respuestas_legibles(encuesta):
        for item in pagina["items"]:
            if item["clave"] == clave:
                return item["valor"]
    raise AssertionError(f"{clave} no está en la ficha")


@pytest.mark.smoke
def test_la_copia_local_esta_en_4_1_1():
    assert get_version() == "4.1.1"
    opciones = get_catalogos()["programaSocialPropio"]["opciones"]
    vigentes = [o["codigo"] for o in opciones if not o.get("retirada")]
    assert vigentes == ["programaLocalProvincial", "acompanamientoSocial", "otros"]


@pytest.mark.smoke
def test_la_ficha_muestra_programa_local_provincial():
    caso = Encuesta(respuestas={"programaSocialCual": ["programaLocalProvincial"]})

    assert _valor(caso, "programaSocialCual") == "Programa Local / Provincial"


@pytest.mark.smoke
def test_un_caso_con_volver_al_trabajo_se_sigue_leyendo():
    caso = Encuesta(respuestas={"programaSocialCual": ["volverAlTrabajo"]})

    assert _valor(caso, "programaSocialCual") == "Volver al trabajo"
    # Se conserva retirada en el catálogo de la 25: si una sincronización la
    # borra, los casos viejos pasan a mostrar la clave cruda.
    opciones = get_catalogos()["programaSocialPropio"]["opciones"]
    retirada = next(o for o in opciones if o["codigo"] == "volverAlTrabajo")
    assert retirada.get("retirada") is True
