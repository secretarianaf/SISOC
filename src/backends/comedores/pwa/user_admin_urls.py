"""Contrato interno del ABM compuesto, sin prefijo en el proxy público."""

from django.urls import path
from pwa.user_admin_views import operacion_usuario_http

urlpatterns = [path("operacion/", operacion_usuario_http)]
