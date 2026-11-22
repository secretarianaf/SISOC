"""Rutas de ``/api/web/cdi/`` de los formularios CDI (G1 v1).

Ver ``centrodeinfancia.web_api_usuario_generar`` (generar usuario) y
``centrodeinfancia.web_api_formularios`` (consulta RENAPER por bloque).
"""

from django.urls import path

from centrodeinfancia.web_api_formularios import renaper_bloque_web
from centrodeinfancia.web_api_usuario_generar import UsuarioGenerarWebView

urlpatterns = [
    path(
        "centros/<int:pk>/usuarios/generar/",
        UsuarioGenerarWebView.as_view(),
        name="centrodeinfancia_web_usuario_generar",
    ),
    path(
        "renaper/<str:bloque>/",
        renaper_bloque_web,
        name="centrodeinfancia_web_renaper_bloque",
    ),
]
