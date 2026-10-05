"""El instrumento 4.0.0 y los casos 3.1.0 guardados, leídos a la vez.

El formulario FINAL en papel reemplazó el instrumento entero: 19 claves nuevas,
27 que dejan de preguntarse y una matriz etaria con otros códigos. Nada se
renombró ni se borró, así que la base queda con casos de las dos generaciones y
el backoffice tiene que leer los dos sin tablas de equivalencia.

Estos tests no tocan la base: leen los JSON de `datacalle/instrumento/` y
arman la `Encuesta` en memoria.
"""

import json
from pathlib import Path

import pytest

from datacalle.models import Encuesta, Relevamiento
from datacalle.services.instrumento import (
    etiqueta_de_celda,
    franjas_sin_entrevista,
    get_version,
    observacion_asentamiento_legible,
    persona_entrevistada_legible,
    respuestas_legibles,
)

pytestmark = pytest.mark.smoke

RUTA_INSTRUMENTO = Path(__file__).resolve().parents[1] / "datacalle" / "instrumento"


def _items(encuesta):
    """`{clave: item}` aplanando las páginas que devuelve `respuestas_legibles`."""
    return {
        item["clave"]: item
        for pagina in respuestas_legibles(encuesta)
        for item in pagina["items"]
    }


# Caso 4.0.0 recortado del ejemplo del contrato
# (`contrato/ejemplos/encuesta-completa.json`): sólo las claves que nacen con el
# papel, más la matriz y la celda.
RESPUESTAS_4_0_0 = {
    "grupoObservado": {"r18a29_varon": 1, "r6a13_mujer": 1},
    "personaEntrevistada": "r18a29_varon#1",
    "asentamientoConsumoProblematico": "no",
    "asentamientoSaludMental": "si",
    "tieneDocumento": "si",
    "documentoTipo": "dniArgentino",
    "vivioSiempreLocalidad": "no",
    "tieneDiscapacidad": "si",
    "cualDiscapacidad": "Dificultad para caminar desde un accidente",
    "tieneHijos": "si",
    "cantidadHijos": 2,
    "cantidadHijosConviven": 1,
    "conQuienesVive": ["pareja", "otrosFamiliares"],
    "dondeDuermeEstaNoche": "viaPublica",
    "primeraVezCalle": "no",
    "desdeCuandoCalle": "1a2anios",
    "motivosCalle": ["perdioTrabajo", "finAlquiler"],
    "ingresoAdicional": "si",
    "tipoIngresoAdicional": ["programaSocial"],
    "programaSocialCual": ["volverAlTrabajo"],
    "programaSocialHijosCual": ["auh"],
}

# Caso ya guardado con el instrumento anterior: franja retirada y preguntas que
# el papel sacó (`soloHistorico`).
RESPUESTAS_HISTORICAS = {
    "personaEntrevistada": "r19a59_varon#1",
    "grupoObservado": {"r19a59_varon": 2, "r0a14_mujer": 1},
    "tiempoEnCalle": "masTresAnios",
    "motivoPrincipalCalle": "laboralesEconomicos",
    "dificultadVer": "mucha",
    "paisEmisor": "bolivia",
    "edadPrimeraVezCalle": 25,
}


def test_la_copia_local_esta_en_la_version_del_contrato():
    assert get_version() == "4.0.0"
    diccionario = json.loads(
        (RUTA_INSTRUMENTO / "diccionario-respuestas.json").read_text(encoding="utf-8")
    )
    assert len(diccionario) == 88
    assert sum(1 for campo in diccionario if campo["soloHistorico"]) == 27


def test_un_caso_4_0_0_se_lee_con_las_claves_nuevas():
    items = _items(Encuesta(respuestas=RESPUESTAS_4_0_0))

    # Las 19 claves que nacen tienen que resolver etiqueta de pregunta...
    assert items["tieneDocumento"]["etiqueta"].startswith("2.")
    assert items["cantidadHijos"]["valor"] == "2"
    # ...y etiqueta de catálogo, incluidos los dos catálogos nuevos de la 25.
    assert items["dondeDuermeEstaNoche"]["valor"].startswith("Vía pública")
    assert items["programaSocialCual"]["valor"] == "Volver al trabajo"
    assert (
        items["programaSocialHijosCual"]["valor"]
        == "Asignación Universal Por Hijo (AUH)"
    )
    assert items["conQuienesVive"]["valor"] == "Pareja / cónyuge, Otro/S familiar/es"
    assert items["desdeCuandoCalle"]["valor"] == "Entre 1 y 2 años"

    # La indocumentación ya no se lee de `documentoTipo`: la 2 es su propia
    # pregunta y la 3 pasó a ser sólo "¿cuál?".
    assert items["tieneDocumento"]["valor"] == "Sí"
    assert items["documentoTipo"]["valor"] == "DNI/CI argentino"

    # Ninguna clave nueva cae en el cajón de "no la conozco" ni se marca
    # retirada: si eso pasara, la copia local quedó en una versión vieja.
    assert all(not item["historico"] for item in items.values())
    paginas = respuestas_legibles(Encuesta(respuestas=RESPUESTAS_4_0_0))
    assert "Otros datos" not in {pagina["titulo"] for pagina in paginas}


def test_un_caso_historico_se_sigue_leyendo_y_se_marca_la_pregunta_retirada():
    items = _items(Encuesta(respuestas=RESPUESTAS_HISTORICAS))

    # El valor guardado no se toca ni se recodifica: se muestra con su etiqueta,
    # que sale del catálogo retirado pero conservado. `tiempoEnCalle` NO se
    # traduce a la escala nueva (`desdeCuandoCalle`): no son comparables.
    assert items["tiempoEnCalle"]["valor"] == "Más de tres años"
    assert items["motivoPrincipalCalle"]["valor"].startswith("Problemas laborales")
    assert items["dificultadVer"]["valor"] == "Sí, mucha dificultad"
    assert items["paisEmisor"]["valor"] == "Bolivia"

    # Y se avisa que esa pregunta ya no se hace, para que la ausencia del dato
    # en un caso nuevo no se lea como dato faltante.
    assert items["tiempoEnCalle"]["historico"] is True
    assert items["dificultadVer"]["historico"] is True
    assert items["paisEmisor"]["historico"] is True
    assert items["personaEntrevistada"]["historico"] is False


def test_la_matriz_etaria_se_lee_con_las_franjas_viejas_y_las_nuevas():
    nuevas = _items(Encuesta(respuestas=RESPUESTAS_4_0_0))
    viejas = _items(Encuesta(respuestas=RESPUESTAS_HISTORICAS))

    assert nuevas["personaEntrevistada"]["valor"] == (
        "Entre 18 y 29 años · Varón (persona 1)"
    )
    assert viejas["personaEntrevistada"]["valor"] == (
        "Entre 19 y 59 años · Varón (persona 1)"
    )

    # El conteo del grupo deja de salir como JSON crudo.
    assert nuevas["grupoObservado"]["valor"] == (
        "Entre 18 y 29 años · Varón: 1; Entre 6 y 13 años · Mujer: 1"
    )
    assert "Entre 0 y 14 años · Mujer: 1" in viejas["grupoObservado"]["valor"]


def test_una_celda_desconocida_se_muestra_cruda_en_vez_de_perderse():
    matriz = {"filas": "rangoEtario2026", "columnas": "generoObservado"}

    assert etiqueta_de_celda("", matriz) == ""
    assert etiqueta_de_celda("rXaY_varon#1", matriz) == "rXaY · Varón (persona 1)"
    # Sin la forma de celda se devuelve tal cual: nunca se oculta lo que llegó.
    assert etiqueta_de_celda("loQueSea", matriz) == "loQueSea"
    assert persona_entrevistada_legible("r65mas_mujer") == "65 años o más · Mujer"


def test_el_cierre_en_campo_muestra_la_etiqueta_del_catalogo():
    """Las dos filas nuevas del cuadro del asentamiento también se leen."""
    relevamiento = Relevamiento(
        observacion_asentamiento=["consumoProblematico", "alteracionesSaludMental"]
    )

    assert observacion_asentamiento_legible(relevamiento) == [
        "Indicios de consumo problemático",
        "Indicios de alteraciones en la salud mental",
    ]
    assert observacion_asentamiento_legible(Relevamiento()) == []


def test_los_prefijos_sin_entrevista_salen_del_cuestionario():
    """La regla la declara el contrato; acá no se hardcodea ninguna franja."""
    prefijos = franjas_sin_entrevista()

    # Las dos del papel FINAL...
    assert "r0a5" in prefijos
    assert "r6a13" in prefijos
    # ...y las de los casos anteriores, que el contrato dejó a propósito para
    # que la misma regla cuente las dos generaciones.
    assert "r0a13" in prefijos
    assert "r0a14" in prefijos
    # 14–17 sí se entrevista: con el papel no hay más formulario abreviado.
    assert not any(prefijo.startswith("r14a17") for prefijo in prefijos)
