"""Lectura del instrumento (cuestionario y catálogos) que publica la app.

Se usa para mostrar las respuestas con etiquetas legibles en el backoffice y
para servir los catálogos a la app. Los archivos son la copia de
`datacalle/instrumento/`; se leen una vez y quedan en memoria.

Regla de oro: las respuestas se guardan como llegan. Si el instrumento local
está desactualizado, se muestra la clave cruda en lugar de perder el dato.

Desde el instrumento 4.0.0 conviven en la base casos de dos generaciones. El
contrato lo resuelve sin que SISOC tenga que recodificar nada: ninguna clave se
renombró ni se borró —las 27 preguntas que dejaron de hacerse quedan marcadas
``soloHistorico``— y los catálogos conservan los códigos retirados con
``retirada: true``. Por eso acá no hay tablas de equivalencia: alcanza con leer
el instrumento vigente, que ya describe el pasado.
"""

import json
from functools import lru_cache
from pathlib import Path

RUTA = Path(__file__).resolve().parent.parent / "instrumento"

# Separadores de una celda de matriz: `r18a29_varon#2` es fila `r18a29`,
# columna `varon`, segunda persona de esa celda (ver `personaEntrevistada`).
SEPARADOR_CELDA = "_"
SEPARADOR_PERSONA = "#"


def _leer(nombre):
    archivo = RUTA / nombre
    if not archivo.exists():
        return {}
    try:
        return json.loads(archivo.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


@lru_cache(maxsize=1)
def get_cuestionario() -> dict:
    return _leer("cuestionario.json")


@lru_cache(maxsize=1)
def get_catalogos() -> dict:
    return _leer("catalogos.json")


@lru_cache(maxsize=1)
def get_diccionario() -> list:
    """Lista plana de las claves que la app puede mandar en ``respuestas``.

    Es la fuente que marca ``soloHistorico`` y la que usamos como respaldo
    cuando una clave guardada no aparece en las páginas del cuestionario.
    """
    datos = _leer("diccionario-respuestas.json")
    return datos if isinstance(datos, list) else []


@lru_cache(maxsize=1)
def get_version() -> str:
    return str(get_cuestionario().get("version") or "")


@lru_cache(maxsize=1)
def _campos_por_id() -> dict:
    """Mapa ``id de campo -> definición``, aplanando las páginas.

    Se completa con el diccionario de respuestas: si una clave guardada no está
    en las páginas del cuestionario local, igual queremos su etiqueta, su
    catálogo y su marca ``soloHistorico``. Las páginas mandan sobre el
    diccionario porque traen la matriz y el tipo de campo.
    """
    paginas = get_cuestionario().get("paginas", [])
    # El diccionario nombra la página por su id (`observacional`) y el
    # cuestionario por su título ("Grupo observado"): la ficha agrupa por
    # título, así que se traduce.
    titulos = {
        pagina.get("id"): pagina.get("titulo", "") for pagina in paginas if pagina
    }

    campos = {}
    for entrada in get_diccionario():
        if not isinstance(entrada, dict):
            continue
        clave = entrada.get("campo")
        if clave:
            slug = entrada.get("pagina", "")
            campos[clave] = dict(entrada, pagina=titulos.get(slug, slug))

    for pagina in paginas:
        for campo in pagina.get("campos", []):
            campo_id = campo.get("id")
            if not campo_id:
                continue
            previo = campos.get(campo_id, {})
            campos[campo_id] = {
                **previo,
                **campo,
                "pagina": pagina.get("titulo", "") or previo.get("pagina", ""),
            }
    return campos


@lru_cache(maxsize=1)
def _etiquetas_por_catalogo() -> dict:
    """Mapa ``catálogo -> {código: etiqueta}``."""
    mapa = {}
    for nombre, definicion in get_catalogos().items():
        if not isinstance(definicion, dict):
            continue
        opciones = definicion.get("opciones") or []
        mapa[nombre] = {
            opcion.get("codigo"): opcion.get("etiqueta")
            for opcion in opciones
            if isinstance(opcion, dict)
        }
    return mapa


@lru_cache(maxsize=1)
def franjas_sin_entrevista() -> tuple:
    """Prefijos etarios de `personaEntrevistada` a los que no se entrevista.

    Sale del propio cuestionario (``estados.rechazada``), que es donde el
    contrato declara la regla, en vez de quedar hardcodeada acá: así la próxima
    sincronización del instrumento la actualiza sola. La lista del 4.0.0 ya
    incluye los prefijos de las versiones anteriores (``r0a13`` / ``r0a14``),
    porque la regla tiene que seguir contando los casos ya guardados.
    """
    rechazada = (get_cuestionario().get("estados") or {}).get("rechazada") or {}
    reglas = rechazada.get("alguna") or [rechazada]
    for regla in reglas:
        if isinstance(regla, dict) and regla.get("campo") == "personaEntrevistada":
            prefijos = regla.get("prefijoEn") or []
            return tuple(str(p) for p in prefijos if p)
    return ()


def etiqueta_de_codigo(catalogo, codigo):
    """Etiqueta de un código de catálogo; el propio código si no se conoce."""
    if codigo in (None, ""):
        return ""
    return _etiquetas_por_catalogo().get(catalogo, {}).get(str(codigo), str(codigo))


def etiqueta_de_celda(valor, matriz):
    """Celda de matriz legible.

    ``r18a29_varon#2`` -> ``Entre 18 y 29 años · Varón (persona 2)``.

    Resuelve igual las filas retiradas (``r19a59``, ``r0a14``, …) porque el
    catálogo las conserva. Si el valor no tiene la forma de celda se devuelve
    tal cual: nunca se oculta lo que llegó.
    """
    if valor in (None, ""):
        return ""
    texto = str(valor)
    celda, _, persona = texto.partition(SEPARADOR_PERSONA)
    fila, separador, columna = celda.partition(SEPARADOR_CELDA)
    if not separador:
        return texto

    matriz = matriz or {}
    partes = [
        etiqueta_de_codigo(matriz.get("filas"), fila),
        etiqueta_de_codigo(matriz.get("columnas"), columna),
    ]
    legible = " · ".join(parte for parte in partes if parte)
    if persona:
        legible = f"{legible} (persona {persona})"
    return legible


def persona_entrevistada_legible(valor):
    """La celda guardada en la columna indexada, con etiquetas del catálogo.

    Es lo que mostramos en el listado de casos, donde hasta ahora se veía el
    código crudo (`r19a59_varon#1`). Las franjas retiradas se leen igual que
    las vigentes.
    """
    campo = _campos_por_id().get("personaEntrevistada") or {}
    return etiqueta_de_celda(valor, campo.get("matriz"))


def _matriz_legible(campo, valor):
    """Conteos de ``grupoObservado``: ``{celda: n}`` -> una línea por celda."""
    matriz = campo.get("matriz") if campo else None
    lineas = []
    for celda, cantidad in valor.items():
        lineas.append(f"{etiqueta_de_celda(celda, matriz)}: {cantidad}")
    return "; ".join(lineas)


def _valor_legible(campo, valor):
    campo = campo or {}
    catalogo = campo.get("catalogo")
    tipo = campo.get("tipo")

    if tipo == "celdaGrupo":
        return etiqueta_de_celda(valor, campo.get("matriz"))
    if isinstance(valor, dict):
        if tipo == "matrizGrupo":
            return _matriz_legible(campo, valor)
        return json.dumps(valor, ensure_ascii=False)
    if isinstance(valor, list):
        if catalogo:
            return ", ".join(etiqueta_de_codigo(catalogo, item) for item in valor)
        return ", ".join(str(item) for item in valor)
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if catalogo:
        return etiqueta_de_codigo(catalogo, valor)
    return str(valor) if valor not in (None, "") else ""


def respuestas_legibles(encuesta):
    """Respuestas del caso agrupadas por página, con etiquetas del instrumento.

    Las claves que el instrumento local no conoce igual se muestran, con su id
    crudo: nunca se oculta un dato que llegó desde la app.

    Las preguntas que el instrumento vigente ya no hace vienen marcadas con
    ``historico``. Se muestran igual —son la lectura del histórico que el
    contrato pide conservar— pero la ficha avisa que no se preguntan más, para
    que nadie lea la ausencia del dato en un caso nuevo como un dato faltante.
    """
    respuestas = encuesta.respuestas or {}
    campos = _campos_por_id()
    paginas = {}
    for clave, valor in respuestas.items():
        campo = campos.get(clave)
        titulo = campo.get("pagina") if campo else "Otros datos"
        etiqueta = campo.get("etiqueta") if campo else clave
        # La firma es una imagen embebida: no tiene sentido volcarla como texto.
        if campo and campo.get("tipo") == "firma":
            legible = "(firma registrada)" if valor else ""
        else:
            legible = _valor_legible(campo, valor)
        paginas.setdefault(titulo or "Otros datos", []).append(
            {
                "clave": clave,
                "etiqueta": etiqueta,
                "valor": legible,
                "historico": bool(campo and campo.get("soloHistorico")),
            }
        )
    return [
        {"titulo": titulo, "items": items} for titulo, items in paginas.items() if items
    ]


def observacion_asentamiento_legible(relevamiento):
    """Códigos del cierre en campo con la etiqueta del catálogo."""
    codigos = relevamiento.observacion_asentamiento or []
    if not isinstance(codigos, list):
        return []
    return [etiqueta_de_codigo("observacionAsentamiento", codigo) for codigo in codigos]
