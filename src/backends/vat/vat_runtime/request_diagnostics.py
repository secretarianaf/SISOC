"""Diagnóstico de peticiones del proceso VAT con datos mínimos."""

import logging
import os
from contextvars import ContextVar
from dataclasses import dataclass, field
from time import monotonic
from uuid import uuid4

logger = logging.getLogger(__name__)
METODOS_HTTP = frozenset(
    {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "CONNECT"}
)


@dataclass
class Peticion:
    metodo: str
    correlacion: str = field(default_factory=lambda: uuid4().hex)
    inicio: float = field(default_factory=monotonic)
    ruta: str = "sin_resolver"

    @property
    def duracion_ms(self):
        return (monotonic() - self.inicio) * 1000


peticion_activa = ContextVar("vat_peticion_activa", default=None)


class DiagnosticoPeticionMiddleware:
    """Usa solo patrones de URL declarados en Django y un ID del servidor."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        metodo = request.method if request.method in METODOS_HTTP else "OTRO"
        peticion = Peticion(metodo)
        token = peticion_activa.set(peticion)
        try:
            response = self.get_response(request)
            logger.info(
                "vat_request id=%s metodo=%s ruta=%s estado=%d duracion_ms=%.1f pid=%d",
                peticion.correlacion,
                peticion.metodo,
                peticion.ruta,
                response.status_code,
                peticion.duracion_ms,
                os.getpid(),
            )
            return response
        finally:
            peticion_activa.reset(token)

    def process_view(self, request, _view_func, _view_args, _view_kwargs):
        # route es metadato del URLconf, no el path ni los valores capturados.
        peticion_activa.get().ruta = request.resolver_match.route or "/"
