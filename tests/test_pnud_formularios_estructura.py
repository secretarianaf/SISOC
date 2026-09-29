"""Definición de los formularios PNUD para el backoffice (estructura literal, 1.1.50).

El JSON vendorizado lo genera la app territorial. Estos tests fijan que la versión
con la estructura literal del documento (encabezado, casillas, ranking, SI/NO)
sigue mostrando todas las respuestas guardadas en su sección, con su etiqueta.
"""

from relevamientos.pnud_formularios import (
    definiciones,
    formatear_valor,
    respuestas_por_seccion,
)

# Nombres que la app muestra pero no guarda en ``datos``: no tienen que figurar.
SOLO_MOSTRAR = {
    "organizacion_solicitante",
    "nombre_espacio",
    "id_sisoc",
    "id_relevamiento",
    "tecnico_nombre",
    "modalidad_entrega",
}

# Claves de ``datos`` que llegan como ítems de un ranking o de casillas.
COMBUSTIBLES = (
    "combustible_gas_red",
    "combustible_electricidad",
    "combustible_garrafa",
    "combustible_lena_carbon",
    "combustible_otros",
)


def _campos(formulario):
    return [
        campo
        for seccion in definiciones()[formulario]["sections"]
        for campo in seccion["fields"]
    ]


def _seccion(secciones, titulo_inicio):
    return next(s for s in secciones if s["titulo"].startswith(titulo_inicio))


def test_bool_usa_etiquetas_si_no_del_papel():
    assert formatear_valor({"type": "bool"}, True) == "Sí"
    assert formatear_valor({"type": "bool"}, False) == "No"
    campo = {"type": "bool", "etiquetasSiNo": ["SI", "NO"]}
    assert formatear_valor(campo, True) == "SI"
    assert formatear_valor(campo, False) == "NO"
    # Un valor no booleano sigue su camino habitual.
    assert formatear_valor(campo, "texto") == "texto"


def test_json_trae_etiquetas_si_no_en_las_preguntas_en_mayuscula():
    for formulario in ("iia", "iib"):
        agua = next(c for c in _campos(formulario) if c["name"] == "agua_potable")
        assert agua["etiquetasSiNo"] == ["SI", "NO"]
    donaciones = next(c for c in _campos("iia") if c["name"] == "recibe_donaciones")
    assert "etiquetasSiNo" not in donaciones


def test_json_sin_campos_solo_para_mostrar_ni_nombres_repetidos():
    for formulario in ("secos", "iia1", "iib1", "iia", "iib"):
        nombres = [c["name"] for c in _campos(formulario)]
        assert not SOLO_MOSTRAR & set(nombres), formulario
        assert len(nombres) == len(set(nombres)), formulario
        assert "comedor" not in nombres


def test_ranking_y_casillas_se_muestran_en_su_seccion_con_su_etiqueta():
    datos = {
        "agua_potable": True,
        "tiene_heladera": True,
        "tiene_freezer": False,
        "combustible_garrafa": 1,
        "combustible_gas_red": 2,
    }
    secciones = respuestas_por_seccion("iia", datos)

    assert not [s for s in secciones if s["titulo"] == "Otros datos"]
    espacio = _seccion(secciones, "7. DATOS SOBRE EL ESPACIO FÍSICO")
    filas = {f["etiqueta"]: f["valor"] for f in espacio["filas"]}
    assert filas["Heladeras"] == "Sí"
    assert filas["Freezer"] == "No"
    assert filas["Gas envasado en garrafa o tubo"] == "1"
    assert filas["Gas de red"] == "2"
    assert filas["7.2.2 ¿Cuentan con agua potable dentro del espacio?"] == "SI"


def test_json_lista_todas_las_claves_de_combustible_de_ii_a():
    nombres = {c["name"] for c in _campos("iia")}
    assert set(COMBUSTIBLES) <= nombres
    assert not set(COMBUSTIBLES) & {c["name"] for c in _campos("iib")}


def test_secos_frecuencia_de_recepcion_en_su_propio_bloque():
    datos = {"retira_punto_distribucion": True, "recepcion_semanal": True}
    titulos = [s["titulo"] for s in respuestas_por_seccion("secos", datos)]
    assert titulos == [
        "4. MODALIDAD DE RECEPCIÓN DE MERCADERÍA",
        "5. FRECUENCIA DE RECEPCIÓN DE MERCADERÍA",
    ]


def test_tabla_prestaciones_conserva_sus_columnas():
    datos = {
        "prestaciones": [
            {
                "id": "x",
                "dia": "Lunes",
                "comida": "Almuerzo",
                "ap_total": 40,
                "de_presencial": 35,
                "de_vianda": 5,
            }
        ]
    }
    tabla = respuestas_por_seccion("iia1", datos)[0]["filas"][0]
    assert tabla["tipo"] == "tabla"
    assert tabla["columnas"] == [
        "Día",
        "PREST.",
        "AP",
        "DE — P (Presencial)",
        "DE — V (Vianda)",
    ]
    assert tabla["filas"] == [["Lunes", "ALM (Almuerzo)", "40", "35", "5"]]
