"""Transporte de contratos internos; adaptadores locales para settings_all.

Los handlers pertenecen al dueño y aplican sus autorizaciones. El registro no
es una fuente de identidad ni un sustituto de los controles del servicio.
"""

import logging
from dataclasses import dataclass

import requests

from core.backend_proxy import backend_de_app, outbound_headers, reenviar_a_backend

logger = logging.getLogger(__name__)
_local_handlers = {}


@dataclass(frozen=True)
class RespuestaInterna:
    status: int
    data: object


def registrar_servicio_interno(path, handler):
    """Registra una implementación del dueño para composición local."""
    anterior = _local_handlers.get(path)
    if anterior is not None and anterior is not handler:
        raise ValueError(f"Ya existe un servicio interno para {path}.")
    _local_handlers[path] = handler


def pedir_json_interno(request, app_label, path, *, method="GET", data=None):
    """Una llamada acotada, sin reintentar mutaciones ni aceptar URLs del cliente."""
    backend = backend_de_app(app_label)
    if backend is None:
        handler = _local_handlers.get(path)
        if handler is None:
            return RespuestaInterna(503, None)
        # No suprimir errores de programación en un adaptador local.
        return handler(request, data)
    headers = outbound_headers(request)
    headers["content-type"] = "application/json"
    try:
        with requests.request(
            method,
            backend["origin"].rstrip("/") + path,
            headers=headers,
            json=data if method != "GET" else None,
            timeout=4,
            allow_redirects=False,
        ) as response:
            try:
                payload = response.json()
            except ValueError:
                return RespuestaInterna(503, None)
            return RespuestaInterna(response.status_code, payload)
    except requests.RequestException:
        logger.warning("Servicio interno no disponible: %s %s", method, path)
        return RespuestaInterna(503, None)


def reenviar_operacion_usuario(request, *, user_id=None, body=None):
    """HTML/POST completo al dueño; la identidad del objeto sale de la ruta."""
    from urllib.parse import urlencode  # pylint: disable=import-outside-toplevel
    from django.http import HttpResponse  # pylint: disable=import-outside-toplevel

    path = "/interno/usuarios/operacion/"
    backend = backend_de_app("pwa")
    if backend is not None:
        query = urlencode({"user_id": user_id}) if user_id is not None else ""
        return reenviar_a_backend(
            request,
            backend,
            path=path.lstrip("/"),
            query_string=query,
            body=body,
            uncertain_on_failure=request.method == "POST",
        )
    handler = _local_handlers.get(path)
    if handler is None:
        return HttpResponse("Espacios comunitarios no está disponible.", status=503)
    return handler(request, {"user_id": user_id})
