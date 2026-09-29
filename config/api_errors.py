"""Errores en JSON bajo ``/api/``.

Los clientes de la API (la app territorial, GESTIONAR) esperan siempre un cuerpo
``{"detail": "..."}``: un 404 de ruteo o un 500 con la página HTML de SISOC los
deja sin un motivo legible. Fuera de ``/api/`` se conservan las páginas de
siempre.
"""

import re

from django.http import Http404, JsonResponse
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.views import exception_handler as drf_exception_handler

API_PREFIX = "/api/"
DETALLE_NO_ENCONTRADO = "No encontrado."
DETALLE_ERROR_INTERNO = "Error interno del servidor."

# Mensaje que arma ``django.shortcuts.get_object_or_404`` (y ``get_object()`` de
# DRF): "No Comedor matches the given query.". Los 404 con texto propio en
# español se respetan.
_MENSAJE_404_DJANGO = re.compile(r"^No \w+ matches the given query\.$")


def es_ruta_api(request):
    path = getattr(request, "path", "") or ""
    return path.startswith(API_PREFIX)


def api_exception_handler(exc, context):
    """``EXCEPTION_HANDLER`` de DRF: el 404 genérico de Django, en español.

    DRF copia el texto del ``Http404`` al ``detail``; bajo ``/api/`` se reemplaza
    el mensaje por defecto (en inglés y con el nombre del modelo) por
    ``DETALLE_NO_ENCONTRADO``. El resto del comportamiento es el de DRF.
    """
    if isinstance(exc, Http404) and es_ruta_api(context.get("request")):
        mensaje = str(exc.args[0]) if exc.args else ""
        if not mensaje or _MENSAJE_404_DJANGO.match(mensaje):
            exc = NotFound(DETALLE_NO_ENCONTRADO)
    return drf_exception_handler(exc, context)


def respuesta_json_404():
    return JsonResponse(
        {"detail": DETALLE_NO_ENCONTRADO}, status=status.HTTP_404_NOT_FOUND
    )


def respuesta_json_500():
    return JsonResponse(
        {"detail": DETALLE_ERROR_INTERNO},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
