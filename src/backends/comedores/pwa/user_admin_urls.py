"""Contrato interno del ABM compuesto, sin prefijo en el proxy público."""

from django.urls import path
from core.internal_services import registrar_servicio_interno
from pwa.user_admin_views import operacion_usuario_http
from pwa.web_user_form import operacion_usuario_web, operacion_usuario_web_http

# Same operation for the React screen: JSON out, the same owner and checks.
registrar_servicio_interno("/interno/usuarios/operacion-web/", operacion_usuario_web)

urlpatterns = [
    path("operacion/", operacion_usuario_http),
    path("operacion-web/", operacion_usuario_web_http),
]
