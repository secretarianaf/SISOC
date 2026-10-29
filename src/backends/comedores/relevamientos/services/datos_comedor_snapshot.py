"""Snapshot de los datos generales del comedor al momento de un relevamiento (#2797).

El detalle de un relevamiento mostraba datos "en vivo" del comedor, de modo que
editar el comedor cambiaba lo que decían los relevamientos ya finalizados. Al
finalizar, el relevamiento guarda una copia de esos datos en
``Relevamiento.datos_comedor_snapshot``.

``armar_snapshot`` solo usa acceso por atributo, así que sirve tanto con los
modelos reales como con los históricos de una migración.
"""

ESTADOS_FINALIZADOS = ("Finalizado", "Finalizado/Excepciones")

CAMPOS_PERSONA = ("nombre", "apellido", "documento", "mail", "celular", "funcion")
CAMPOS_COMEDOR = (
    "nombre",
    "comienzo",
    "calle",
    "numero",
    "entre_calle_1",
    "entre_calle_2",
    "partido",
    "barrio",
    "codigo_postal",
)


def _nombre_de(objeto):
    return getattr(objeto, "nombre", None) if objeto is not None else None


def _datos_persona(persona):
    return {campo: getattr(persona, campo, None) for campo in CAMPOS_PERSONA}


def armar_snapshot(comedor, responsable=None):
    """Arma el dict plano (serializable a JSON) con los datos del comedor."""
    datos = {campo: getattr(comedor, campo, None) for campo in CAMPOS_COMEDOR}
    datos["provincia"] = _nombre_de(comedor.provincia)
    datos["municipio"] = _nombre_de(comedor.municipio)
    datos["localidad"] = _nombre_de(comedor.localidad)
    datos["programa"] = _nombre_de(comedor.programa)
    datos["referente"] = _datos_persona(comedor.referente)
    datos["responsable"] = _datos_persona(responsable)
    return datos


def esta_finalizado(estado):
    return estado in ESTADOS_FINALIZADOS
