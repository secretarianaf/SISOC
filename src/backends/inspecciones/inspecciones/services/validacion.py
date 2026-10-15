"""Validación del formulario v1 en el servidor.

Misma regla que la app (``pwa/src/features/formulario/validacion.ts``) más las
del contrato (§7): la app ya valida, pero el cierre no confía en el cliente.
Las claves de error son las rutas del cable (``respuestas.f09``,
``escuela.cue``), para que la app pueda señalar el campo.

Reglas clave (especificación §14 y §15):

- ``cerrada`` exige ``f05 = no`` y ``f05 = no`` implica ``cerrada``;
  ``no_ingreso`` exige ``f05 = si`` y ``que_ocurrio``.
- Con ``cerrada`` o ``no_ingreso`` no se exigen F07 a F12 y lo que falta **no**
  se convierte en cero: se guarda tal cual llegó.
- Cero es una respuesta explícita; ``null`` con condición es "sin dato".
- Las advertencias (presentes > previstos, etc.) se aceptan con justificación.
"""

import re

from inspecciones.services.formularios import limites, turnos_validos

SI_NO = ("si", "no")
SI_NO_NO_CONSTATADO = ("si", "no", "no_constatado")
RESULTADOS = ("constatado", "parcial", "cerrada", "no_ingreso")
SIN_CONSTATACION = ("cerrada", "no_ingreso")
MOTIVOS_EXCEPCION = ("negativa", "ausente", "otra")
SOLO_DIGITOS = re.compile(r"^\d+$")

# (clave de la cantidad, condición alternativa a "dato", etiqueta del error)
CANTIDADES = (
    ("f09", "no_informado", "No informado"),
    ("f10", "no_constatado", "No constatado"),
    ("f11", "no_informado", "No informado"),
    ("f12", "no_constatado", "No constatado"),
)


def _obj(valor):
    return valor if isinstance(valor, dict) else {}


def _texto(valor):
    return valor if isinstance(valor, str) else ""


def _vacio(valor):
    return not _texto(valor).strip()


def _es_entero(valor):
    if isinstance(valor, bool):
        return False
    if isinstance(valor, int):
        return True
    return isinstance(valor, float) and valor.is_integer()


def valor_conocido(cantidad):
    """Valor de una cantidad, o ``None`` si no hay dato (cero sí es dato)."""
    c = _obj(cantidad)
    valor = c.get("valor")
    if c.get("condicion", "dato") != "dato" or valor is None:
        return None
    if not _es_entero(valor) or valor < 0:
        return None
    return int(valor)


def advertencias(respuestas):
    """Claves de ``justificaciones`` que la respuesta exige justificar."""
    r = _obj(respuestas)
    if r.get("resultado") not in ("constatado", "parcial"):
        return []
    previsto = valor_conocido(r.get("f09"))
    presente = valor_conocido(r.get("f10"))
    aulas_previstas = valor_conocido(r.get("f11"))
    aulas = valor_conocido(r.get("f12"))
    claves = []
    if previsto is not None and presente is not None and presente > previsto:
        claves.append("presentes_superan")
    if aulas_previstas is not None and aulas is not None and aulas > aulas_previstas:
        claves.append("aulas_superan")
    if r.get("f07") == "no" and presente is not None and presente > 0:
        claves.append("sin_personal_con_presentes")
    if r.get("f08") == "no" and aulas is not None and aulas > 0:
        claves.append("sin_estudiantes_con_aulas")
    return claves


def _validar_escuela(payload, turnos_visitados_hoy, errores):
    escuela = _obj(payload.get("escuela"))
    if _vacio(escuela.get("nombre")):
        errores["escuela.nombre"] = "El nombre de la escuela es obligatorio."
    if escuela.get("cue_desconocido") is True:
        if _vacio(escuela.get("motivo_sin_cue")):
            errores["escuela.motivo_sin_cue"] = "Indicá por qué no se conoce el CUE."
    elif _vacio(escuela.get("cue")):
        errores["escuela.cue"] = "Ingresá el CUE o marcá que no lo conocés."
    elif not SOLO_DIGITOS.match(_texto(escuela.get("cue")).strip()):
        errores["escuela.cue"] = "El CUE lleva solo números."
    for campo, mensaje in (
        ("domicilio", "El domicilio es obligatorio."),
        ("localidad", "La localidad es obligatoria."),
        ("distrito", "El distrito es obligatorio."),
    ):
        if _vacio(escuela.get(campo)):
            errores[f"escuela.{campo}"] = mensaje
    turno = payload.get("turno")
    if not turno:
        errores["turno"] = "Elegí el turno inspeccionado."
    elif turno not in turnos_validos():
        errores["turno"] = "Turno inválido."
    elif turno in turnos_visitados_hoy and _vacio(payload.get("motivo_nueva_visita")):
        errores["motivo_nueva_visita"] = (
            "Ya hay una visita hoy en este turno: indicá el motivo de la nueva."
        )


def _validar_coordenadas(ubicacion, errores):
    lat = ubicacion.get("lat")
    lng = ubicacion.get("lng")
    if lat is None or lng is None:
        errores["ubicacion"] = "Falta capturar la ubicación."
        return
    numeros = all(
        isinstance(v, (int, float)) and not isinstance(v, bool) for v in (lat, lng)
    )
    if not numeros or not (-90 <= lat <= 90 and -180 <= lng <= 180):
        errores["ubicacion"] = "Las coordenadas no son válidas."


def _validar_ubicacion(payload, errores):
    ubicacion = payload.get("ubicacion")
    if not isinstance(ubicacion, dict):
        errores["ubicacion"] = (
            "Registrá la ubicación por GPS o indicá por qué no se puede."
        )
        return
    fuente = ubicacion.get("fuente")
    if fuente == "gps":
        _validar_coordenadas(ubicacion, errores)
    elif fuente == "manual":
        if _vacio(ubicacion.get("motivo_sin_gps")):
            errores["ubicacion.motivo_sin_gps"] = (
                "Indicá por qué no se pudo obtener la ubicación."
            )
    else:
        errores["ubicacion.fuente"] = "Fuente de ubicación inválida."


def _validar_ingreso(r, errores):
    f04 = _obj(r.get("f04"))
    if not f04.get("imagen_uuid") and _vacio(f04.get("motivo_sin_foto")):
        errores["respuestas.f04"] = (
            "Sacá la foto del ingreso o indicá por qué no se puede."
        )
    f05 = r.get("f05")
    resultado = r.get("resultado")
    if f05 not in SI_NO:
        errores["respuestas.f05"] = "Indicá si la escuela está abierta."
    if resultado not in RESULTADOS:
        errores["respuestas.resultado"] = "Elegí el resultado de la constatación."
    elif resultado == "cerrada" and f05 != "no":
        errores["respuestas.resultado"] = "Escuela cerrada exige Abierta = No."
    elif f05 == "no" and resultado != "cerrada":
        errores["respuestas.resultado"] = (
            "Abierta = No implica que la escuela estaba cerrada."
        )
    if resultado == "no_ingreso":
        if f05 != "si":
            errores["respuestas.resultado"] = "No dejó ingresar exige Abierta = Sí."
        if _vacio(r.get("que_ocurrio")):
            errores["respuestas.que_ocurrio"] = "Contá qué ocurrió."
    if resultado == "parcial" and _vacio(r.get("motivo_parcial")):
        errores["respuestas.motivo_parcial"] = (
            "Indicá por qué la constatación fue parcial."
        )
    f06 = _obj(r.get("f06"))
    if f06.get("nadie") is not True:
        if _vacio(f06.get("nombre")):
            errores["respuestas.f06.nombre"] = (
                "Ingresá el nombre o marcá Nadie atiende."
            )
        if _vacio(f06.get("funcion")):
            errores["respuestas.f06.funcion"] = "Ingresá la función o rol."


def _validar_cantidad(  # pylint: disable=too-many-arguments
    cantidad, *, obligatoria, campo, alternativa, etiqueta, errores
):
    c = _obj(cantidad)
    condicion = c.get("condicion", "dato")
    if condicion == "dato":
        valor = c.get("valor")
        if valor is None:
            if obligatoria:
                errores[campo] = f"Ingresá la cantidad o marcá {etiqueta}."
        elif not _es_entero(valor) or valor < 0:
            errores[campo] = "Tiene que ser un número entero, cero o mayor."
    elif condicion == alternativa:
        if _vacio(c.get("motivo")):
            errores[f"{campo}.motivo"] = "Indicá el motivo."
    else:
        errores[campo] = "Condición inválida."


def _validar_constatacion(r, errores):
    resultado = r.get("resultado")
    if resultado not in ("constatado", "parcial"):
        # Escuela cerrada o ingreso denegado: no se exigen F07 a F12.
        return
    completa = resultado == "constatado"
    for clave, mensaje in (
        ("f07", "Respondé si hay personal educativo."),
        ("f08", "Respondé si hay estudiantes."),
    ):
        valor = r.get(clave)
        if valor is None:
            if completa:
                errores[f"respuestas.{clave}"] = mensaje
        elif valor not in SI_NO_NO_CONSTATADO:
            errores[f"respuestas.{clave}"] = "Opción inválida."
    for clave, alternativa, etiqueta in CANTIDADES:
        _validar_cantidad(
            r.get(clave),
            obligatoria=completa,
            campo=f"respuestas.{clave}",
            alternativa=alternativa,
            etiqueta=etiqueta,
            errores=errores,
        )
    justificaciones = _obj(r.get("justificaciones"))
    for clave in advertencias(r):
        if _vacio(justificaciones.get(clave)):
            errores[f"respuestas.justificaciones.{clave}"] = "Escribí la justificación."


def imagenes_adicionales(payload):
    return [
        im
        for im in payload.get("imagenes") or []
        if isinstance(im, dict) and im.get("tipo") == "adicional"
    ]


def _validar_imagenes(payload, r, errores):
    tope = limites()
    if len(_texto(r.get("f16"))) > tope["max_observaciones"]:
        errores["respuestas.f16"] = (
            f"Máximo {tope['max_observaciones']} caracteres de observaciones."
        )
    if len(imagenes_adicionales(payload)) > tope["max_imagenes_adicionales"]:
        errores["respuestas.f15"] = (
            f"Hasta {tope['max_imagenes_adicionales']} imágenes adicionales."
        )


def _validar_firma(payload, errores):
    firma = payload.get("firma")
    if not isinstance(firma, dict):
        errores["firma"] = "Falta la firma o el motivo por el que no se firma."
        return
    tipo = firma.get("tipo")
    if tipo == "firma":
        if _vacio(firma.get("nombre")):
            errores["firma.nombre"] = "Ingresá nombre y apellido de quien firma."
        if _vacio(firma.get("cargo")):
            errores["firma.cargo"] = "Ingresá el cargo."
        if firma.get("conformidad") is not True:
            errores["firma.conformidad"] = (
                "Quien firma tiene que leer el resumen y dar conformidad."
            )
        if _vacio(firma.get("imagen_uuid")):
            errores["firma.imagen_uuid"] = "Falta la firma."
        if _vacio(firma.get("texto_mostrado")):
            errores["firma.texto_mostrado"] = "Falta el texto de conformidad mostrado."
    elif tipo == "excepcion":
        if firma.get("motivo_tipo") not in MOTIVOS_EXCEPCION:
            errores["firma.motivo_tipo"] = "Elegí qué pasó."
        if _vacio(firma.get("motivo")):
            errores["firma.motivo"] = "Indicá el motivo."
    else:
        errores["firma"] = "Falta la firma o el motivo por el que no se firma."


def validar_inspeccion(payload, *, turnos_visitados_hoy=()):
    """Errores del estado final de la inspección (vacío si se puede cerrar)."""
    errores = {}
    if not isinstance(payload, dict):
        return {"": "El cuerpo debe ser un objeto JSON."}
    respuestas = _obj(payload.get("respuestas"))
    _validar_escuela(payload, turnos_visitados_hoy, errores)
    _validar_ubicacion(payload, errores)
    _validar_ingreso(respuestas, errores)
    _validar_constatacion(respuestas, errores)
    _validar_imagenes(payload, respuestas, errores)
    _validar_firma(payload, errores)
    return errores
