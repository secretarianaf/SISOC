"""Contrato de lectura CDI para la administración de tableros de Datos."""

from collections.abc import Mapping

from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import View

from centrodeinfancia.models import CentroDeInfancia
from core.internal_services import RespuestaInterna
from iam.roles_datos import puede_administrar_tableros

RUTA_SELECTOR = "/centrodeinfancia/interno/tableros/centros/"
LIMITE = 100


def _leer_parametros(parametros):
    parametros = parametros or {}
    if not isinstance(parametros, Mapping):
        raise ValidationError("Parámetros inválidos.")
    ids_texto = parametros.get("ids", "")
    busqueda = parametros.get("q", "")
    pagina_texto = parametros.get("pagina", "1")
    if (
        not isinstance(ids_texto, str)
        or not isinstance(pagina_texto, str)
        or not isinstance(busqueda, str)
    ):
        raise ValidationError("Parámetros inválidos.")
    busqueda = busqueda.strip()
    if (
        len(busqueda) > 100
        or len(ids_texto) > 2000
        or len(pagina_texto) > 5
        or not pagina_texto.isascii()
        or not pagina_texto.isdecimal()
    ):
        raise ValidationError("Parámetros inválidos.")
    pagina = int(pagina_texto)
    if pagina < 1 or pagina > 10000:
        raise ValidationError("Página inválida.")
    ids = []
    if ids_texto:
        partes = ids_texto.split(",")
        if len(partes) > LIMITE or any(
            not p.isascii()
            or not p.isdecimal()
            or len(p) > 19
            or not 0 < int(p) <= 9223372036854775807
            for p in partes
        ):
            raise ValidationError("Identificadores inválidos.")
        ids = [int(p) for p in partes]
        if len(set(ids)) != len(ids):
            raise ValidationError("Identificadores repetidos.")
    return ids, busqueda, pagina


def consultar_centros(request, parametros):
    """Filtra en CDI y no confía en la autorización del servicio llamante."""
    if not puede_administrar_tableros(request.user):
        return RespuestaInterna(403, {"error": "Acceso denegado."})
    try:
        ids, busqueda, pagina = _leer_parametros(parametros)
    except ValidationError as exc:
        return RespuestaInterna(400, {"error": " ".join(exc.messages)})
    centros = CentroDeInfancia.objects.filter(estado=CentroDeInfancia.Estado.ACTIVO)
    if ids:
        centros = centros.filter(pk__in=ids).order_by("pk")
        resultado = list(centros.values("id", "nombre"))
        return RespuestaInterna(200, {"centros": resultado, "hay_mas": False})
    if busqueda:
        centros = centros.filter(nombre__icontains=busqueda)
    inicio = (pagina - 1) * 25
    resultado = list(
        centros.order_by("nombre", "pk").values("id", "nombre")[inicio : inicio + 26]
    )
    return RespuestaInterna(
        200, {"centros": resultado[:25], "hay_mas": len(resultado) > 25}
    )


@method_decorator(never_cache, name="dispatch")
class SelectorTablerosView(View):
    """Devuelve exclusivamente la identificación mínima de centros activos."""

    http_method_names = ["get", "head"]

    def get(self, request):
        respuesta = consultar_centros(request, request.GET)
        return JsonResponse(respuesta.data, status=respuesta.status)
