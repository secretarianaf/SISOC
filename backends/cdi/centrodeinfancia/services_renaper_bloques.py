"""Precarga y bloqueo de identidad RENAPER por bloque de persona en CDI.

Un "bloque" es una persona dentro de un formulario: el niño/a de la nómina, los
responsables legales 1 y 2, o el referente del CDI. RENAPER completa los datos
de identidad del bloque y esos campos quedan bloqueados; teléfono y email siguen
editables. Los valores viajan en un token firmado: el servidor toma los datos
del token y no los del POST, así que no se pueden alterar desde el navegador.
"""

from datetime import date

from django.core import signing

from ciudadanos.api import obtener_datos_ciudadano_desde_renaper
from core.models import Nacionalidad, Sexo

TOKEN_SALT = "centrodeinfancia.renaper_bloque"
# La ficha de nómina es larga: una hora alcanza para completarla sin perder la
# precarga. Si el token vence, los datos quedan como carga manual.
TOKEN_MAX_AGE_SECONDS = 60 * 60
TOKEN_POST_PREFIX = "renaper_token_"

BLOQUE_NINO = "nino"
BLOQUE_RESPONSABLE_1 = "responsable_legal_1"
BLOQUE_RESPONSABLE_2 = "responsable_legal_2"
BLOQUE_REFERENTE = "referente"

BLOQUES_NOMINA = (BLOQUE_NINO, BLOQUE_RESPONSABLE_1, BLOQUE_RESPONSABLE_2)

# El sexo de los responsables usa el catálogo de trabajadores, no el de Sexo.
_SEXO_REGISTRAL_DESDE_SEXO = {
    "Masculino": "varon",
    "Femenino": "mujer",
    "X": "indeterminado",
}


def _campos_responsable(prefijo):
    return {
        "dni": f"{prefijo}_dni",
        "apellido": f"{prefijo}_apellido",
        "nombre": f"{prefijo}_nombre",
        "fecha_nacimiento": f"{prefijo}_fecha_nacimiento",
        "sexo": f"{prefijo}_sexo_registral",
        "nacionalidad": f"{prefijo}_nacionalidad",
        "cuit": f"{prefijo}_cuit",
    }


# Dato de identidad -> campo del formulario, por bloque.
BLOQUES = {
    BLOQUE_NINO: {
        "dni": "dni",
        "apellido": "apellido",
        "nombre": "nombre",
        "fecha_nacimiento": "fecha_nacimiento",
        "sexo": "sexo",
        "nacionalidad": "nacionalidad",
        "cuit": "cuit_nino",
    },
    BLOQUE_RESPONSABLE_1: _campos_responsable(BLOQUE_RESPONSABLE_1),
    BLOQUE_RESPONSABLE_2: _campos_responsable(BLOQUE_RESPONSABLE_2),
    BLOQUE_REFERENTE: {
        "dni": "dni_referente",
        "apellido": "apellido_referente",
        "nombre": "nombre_referente",
        "cuit": "cuil_referente",
    },
}


# Campo de tipo de documento de cada bloque (el referente no tiene).
TIPO_DOCUMENTO_POR_BLOQUE = {
    BLOQUE_NINO: "tipo_documentacion",
    BLOQUE_RESPONSABLE_1: f"{BLOQUE_RESPONSABLE_1}_tipo_documentacion",
    BLOQUE_RESPONSABLE_2: f"{BLOQUE_RESPONSABLE_2}_tipo_documentacion",
}
# Tipos de documentación con DNI argentino. Con cualquier otro no hay nada que
# consultar en RENAPER y el bloque pasa directo a carga manual.
TIPOS_DOCUMENTO_CON_DNI = ("dni_permanente", "dni_temporario", "naturalizacion")

# Cómo arranca cada bloque en la pantalla.
MODO_DNI = "dni"  # solo tipo de documento + DNI + "Validar con RENAPER"
MODO_VERIFICADO = "verificado"  # tarjeta de solo lectura + campos de contacto
MODO_MANUAL = "manual"  # todos los campos editables


def _nombre_por_pk(model, campo, valor):
    if not str(valor or "").isdigit():
        return None
    return model.objects.filter(pk=valor).values_list(campo, flat=True).first()


def identidad_desde_resultado(resultado):
    """Normaliza la respuesta de ``obtener_datos_ciudadano_desde_renaper``."""
    data = resultado.get("data") or {}
    return {
        "dni": data.get("documento") or data.get("dni"),
        "apellido": data.get("apellido"),
        "nombre": data.get("nombre"),
        "fecha_nacimiento": data.get("fecha_nacimiento"),
        "sexo": _nombre_por_pk(Sexo, "sexo", data.get("sexo")),
        "nacionalidad": _nombre_por_pk(
            Nacionalidad, "nacionalidad", data.get("nacionalidad")
        ),
        "cuit": data.get("cuil_cuit"),
    }


def identidad_desde_ciudadano_validado(ciudadano):
    """Identidad confirmada por RENAPER de un ciudadano local ya validado.

    Solo se toman los datos que la validación compara (documento, apellido,
    nombre y fecha de nacimiento); sexo, nacionalidad y CUIL pueden haberse
    cargado a mano.
    """
    if ciudadano.estado_validacion_renaper != ciudadano.RENAPER_VALIDADO:
        return {}
    return {
        "dni": ciudadano.documento,
        "apellido": ciudadano.apellido,
        "nombre": ciudadano.nombre,
        "fecha_nacimiento": ciudadano.fecha_nacimiento,
    }


def valores_bloque(bloque, identidad):
    """Traduce una identidad a ``{campo del form: valor serializable}``."""
    valores = {}
    for dato, campo in BLOQUES[bloque].items():
        valor = identidad.get(dato)
        if dato == "sexo" and bloque != BLOQUE_NINO:
            valor = _SEXO_REGISTRAL_DESDE_SEXO.get(valor)
        if valor in (None, ""):
            continue
        if isinstance(valor, date):
            valor = valor.isoformat()
        valores[campo] = valor
    return valores


def consultar_bloque(bloque, dni):
    """Consulta RENAPER y devuelve los valores a precargar en el bloque."""
    resultado = obtener_datos_ciudadano_desde_renaper(str(dni or "").strip())
    if not resultado.get("success"):
        return {
            "success": False,
            "message": resultado.get("message")
            or "No se encontraron datos en RENAPER.",
        }
    valores = valores_bloque(bloque, identidad_desde_resultado(resultado))
    if not valores:
        return {"success": False, "message": "RENAPER no devolvió datos."}
    return {
        "success": True,
        "message": "Datos obtenidos desde RENAPER.",
        "valores": valores,
    }


def crear_token(bloque, user, valores):
    return signing.dumps(
        {"bloque": bloque, "user_id": user.pk, "values": valores},
        salt=TOKEN_SALT,
    )


def leer_token(token, bloque, user):
    """Valores del token si es vigente, del mismo usuario y del mismo bloque."""
    if not token:
        return {}
    try:
        payload = signing.loads(token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE_SECONDS)
    except signing.BadSignature:
        return {}
    if (
        not isinstance(payload, dict)
        or payload.get("bloque") != bloque
        or payload.get("user_id") != user.pk
        or not isinstance(payload.get("values"), dict)
    ):
        return {}
    permitidos = set(BLOQUES[bloque].values())
    return {
        campo: valor
        for campo, valor in payload["values"].items()
        if campo in permitidos and valor not in (None, "")
    }


def tokens_desde_post(data, user, bloques):
    """Lee los tokens del POST. Devuelve ``({bloque: valores}, {bloque: token})``."""
    valores, tokens = {}, {}
    for bloque in bloques:
        token = data.get(f"{TOKEN_POST_PREFIX}{bloque}")
        valores_token = leer_token(token, bloque, user)
        if valores_token:
            valores[bloque] = valores_token
            tokens[bloque] = token
    return valores, tokens


def bloques_verificados(campos_verificados, bloques):
    """Indica por bloque si alguno de sus campos ya está verificado."""
    campos = set(campos_verificados or [])
    return {
        bloque: bool(campos.intersection(BLOQUES[bloque].values()))
        for bloque in bloques
    }
