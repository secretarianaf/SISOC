"""Contrato validado con el servicio dueño de centros CDI."""

from django.core.exceptions import ValidationError

from core.internal_services import pedir_json_interno

RUTA_SELECTOR = "/centrodeinfancia/interno/tableros/centros/"


def _id_valido(valor):
    return (
        isinstance(valor, int)
        and not isinstance(valor, bool)
        and 0 < valor <= 9223372036854775807
    )


def _consultar(request, params, limite):
    respuesta = pedir_json_interno(
        request, "centrodeinfancia", RUTA_SELECTOR, params=params
    )
    datos = respuesta.data
    if respuesta.status != 200 or not isinstance(datos, dict):
        raise ValidationError("No se pudieron validar los CDI. Intente nuevamente.")
    centros, hay_mas = datos.get("centros"), datos.get("hay_mas")
    if (
        not isinstance(centros, list)
        or len(centros) > limite
        or not isinstance(hay_mas, bool)
    ):
        raise ValidationError("La respuesta de CDI no es válida.")
    ids = set()
    for centro in centros:
        if not isinstance(centro, dict) or set(centro) != {"id", "nombre"}:
            raise ValidationError("La respuesta de CDI no es válida.")
        identificador, nombre = centro["id"], centro["nombre"]
        if (
            not _id_valido(identificador)
            or not isinstance(nombre, str)
            or not nombre
            or len(nombre) > 255
            or identificador in ids
        ):
            raise ValidationError("La respuesta de CDI no es válida.")
        ids.add(identificador)
    return datos


def buscar_centros(request, busqueda, pagina):
    if (
        not isinstance(busqueda, str)
        or len(busqueda) > 100
        or isinstance(pagina, bool)
        or not isinstance(pagina, int)
        or not 1 <= pagina <= 10000
    ):
        raise ValidationError("La búsqueda de CDI no es válida.")
    return _consultar(request, {"q": busqueda, "pagina": str(pagina)}, 25)


def validar_centros(request, ids):
    valores = list(ids)
    if (
        not valores
        or len(valores) > 100
        or any(not _id_valido(x) for x in valores)
        or len(set(valores)) != len(valores)
    ):
        raise ValidationError("Seleccione CDI válidos sin duplicados.")
    datos = _consultar(request, {"ids": ",".join(str(x) for x in valores)}, 100)
    recibidos = frozenset(centro["id"] for centro in datos["centros"])
    if datos["hay_mas"] or recibidos != frozenset(valores):
        raise ValidationError("Uno o más CDI no están activos o ya no existen.")
    return recibidos
