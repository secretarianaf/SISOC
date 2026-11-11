"""Routes of ``/api/web/pas/`` (G1 v1): see ``pas.web_api_views``."""

from django.urls import path

from pas.web_api_views import (
    PasAreaWebView,
    PasFormacionPersonasWebView,
    PasPanelWebView,
    PasPersonaListWebView,
)

urlpatterns = [
    path(
        "areas/formacion/",
        PasAreaWebView.as_view(area_key="formacion"),
        name="pas_web_area_formacion",
    ),
    path(
        "areas/mesa-ayuda/",
        PasAreaWebView.as_view(area_key="mesa-ayuda"),
        name="pas_web_area_mesa_ayuda",
    ),
    path(
        "areas/liquidacion/",
        PasAreaWebView.as_view(area_key="liquidacion"),
        name="pas_web_area_liquidacion",
    ),
    path(
        "formacion/personas/",
        PasFormacionPersonasWebView.as_view(),
        name="pas_web_formacion_personas",
    ),
    path("personas/", PasPersonaListWebView.as_view(), name="pas_web_personas"),
    path("panel/", PasPanelWebView.as_view(), name="pas_web_panel"),
    path("panel/<int:pk>/", PasPanelWebView.as_view(), name="pas_web_panel_persona"),
]
