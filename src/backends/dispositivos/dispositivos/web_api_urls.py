"""Rutas de ``/api/web/dispositivos/`` de Dispositivos (G1 v1).

Ver ``dispositivos.web_api`` (listado, legajo, mapa y ubicación; DS01.01 y
DS02.01 de #2785).
"""

from django.urls import path

from dispositivos.web_api import (
    DispositivoDetailWebView,
    DispositivoListWebView,
    DispositivoLocationWebView,
    DispositivoMapWebView,
    DispositivoOptionsWebView,
)

urlpatterns = [
    # The root ``/api/web/dispositivos/`` stays free: the core keeps it as the
    # vertical name guard (``test_vertical_names_do_not_collide_...``).
    path(
        "listado/",
        DispositivoListWebView.as_view(),
        name="web_dispositivos_list",
    ),
    path(
        "options/",
        DispositivoOptionsWebView.as_view(),
        name="web_dispositivos_options",
    ),
    path("mapa/", DispositivoMapWebView.as_view(), name="web_dispositivos_mapa"),
    path(
        "<int:pk>/",
        DispositivoDetailWebView.as_view(),
        name="web_dispositivos_detail",
    ),
    path(
        "<int:pk>/ubicacion/",
        DispositivoLocationWebView.as_view(),
        name="web_dispositivos_ubicacion",
    ),
]
