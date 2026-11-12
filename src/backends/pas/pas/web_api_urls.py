"""Routes of ``/api/web/pas/`` (G1 v1): see ``pas.web_api_views``."""

from django.urls import path

from pas.web_api_cruces import (
    PasCrucesActualizarRenaperWebView,
    PasCrucesExportarSintysWebView,
    PasCrucesImportarSintysWebView,
    PasCrucesWebView,
)
from pas.web_api_informes import (
    PasInformeDetailWebView,
    PasInformeGenerarCsvWebView,
    PasInformeListWebView,
    PasInformeOpcionesWebView,
    PasInformePrevisualizarWebView,
)
from pas.web_api_views import (
    PasAreaWebView,
    PasCambioEstadoWebView,
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
    path(
        "personas/<int:pk>/cambiar-estado/",
        PasCambioEstadoWebView.as_view(),
        name="pas_web_persona_cambiar_estado",
    ),
    path("informes/", PasInformeListWebView.as_view(), name="pas_web_informes"),
    path(
        "informes/opciones/",
        PasInformeOpcionesWebView.as_view(),
        name="pas_web_informes_opciones",
    ),
    path(
        "informes/previsualizar/",
        PasInformePrevisualizarWebView.as_view(),
        name="pas_web_informes_previsualizar",
    ),
    path(
        "informes/generar/",
        PasInformeGenerarCsvWebView.as_view(),
        name="pas_web_informes_generar",
    ),
    path(
        "informes/<int:pk>/",
        PasInformeDetailWebView.as_view(),
        name="pas_web_informe",
    ),
    path("cruces/", PasCrucesWebView.as_view(), name="pas_web_cruces"),
    path(
        "cruces/exportar-sintys/",
        PasCrucesExportarSintysWebView.as_view(),
        name="pas_web_cruces_exportar_sintys",
    ),
    path(
        "cruces/importar-sintys/",
        PasCrucesImportarSintysWebView.as_view(),
        name="pas_web_cruces_importar_sintys",
    ),
    path(
        "cruces/actualizar-renaper/",
        PasCrucesActualizarRenaperWebView.as_view(),
        name="pas_web_cruces_actualizar_renaper",
    ),
]
