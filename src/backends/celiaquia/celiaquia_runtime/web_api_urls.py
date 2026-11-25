"""API web del backend Celiaquía (``/api/web/celiaquia/``, G1 v1)."""

from django.urls import path

from ciudadanos.web_aportes import AporteCiudadanoWebView

urlpatterns = [
    # Aporte de Celiaquía a Ciudadano 360 (C04).
    path(
        "ciudadanos/<int:pk>/aportes/<str:aporte>/",
        AporteCiudadanoWebView.as_view(backend="celiaquia"),
        name="celiaquia_web_ciudadano_aporte",
    ),
]
