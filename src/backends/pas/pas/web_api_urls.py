"""Routes of ``/api/web/pas/`` (G1 v1): see ``pas.web_api_views``."""

from django.urls import path

from pas.web_api_cruces import (
    PasCrucesActualizarRenaperWebView,
    PasCrucesExportarSintysWebView,
    PasCrucesImportarSintysWebView,
    PasCrucesWebView,
    PasIncompatibilidadConfirmarWebView,
    PasIncompatibilidadModificarWebView,
)
from pas.web_api_informes import (
    PasInformeDetailWebView,
    PasInformeGenerarCsvWebView,
    PasInformeListWebView,
    PasInformeOpcionesWebView,
    PasInformePrevisualizarWebView,
)
from pas.web_api_titulares_import import PasTitularesImportWebView
from pas.web_api_persona_form import (
    PasPersonaCrearWebView,
    PasPersonaEditarWebView,
    PasPersonaOpcionesWebView,
)
from pas.web_api_views import (
    PasAreaWebView,
    PasCambioEstadoWebView,
    PasFormacionPersonasWebView,
    PasLiquidacionDescargarNominaWebView,
    PasLiquidacionPreliquidacionCsvWebView,
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
        "liquidacion/descargar-nomina/",
        PasLiquidacionDescargarNominaWebView.as_view(),
        name="pas_web_liquidacion_descargar_nomina",
    ),
    path(
        "liquidacion/preliquidacion-csv/",
        PasLiquidacionPreliquidacionCsvWebView.as_view(),
        name="pas_web_liquidacion_preliquidacion_csv",
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
    path(
        "cruces/incompatibilidades/<int:pk>/confirmar/",
        PasIncompatibilidadConfirmarWebView.as_view(),
        name="pas_web_incompatibilidad_confirmar",
    ),
    path(
        "cruces/incompatibilidades/<int:pk>/modificar/",
        PasIncompatibilidadModificarWebView.as_view(),
        name="pas_web_incompatibilidad_modificar",
    ),
    path(
        "titulares/importar/",
        PasTitularesImportWebView.as_view(),
        name="pas_web_titulares_importar",
    ),
    path(
        "personas/opciones/",
        PasPersonaOpcionesWebView.as_view(),
        name="pas_web_personas_opciones",
    ),
    path(
        "personas/crear/",
        PasPersonaCrearWebView.as_view(),
        name="pas_web_persona_crear",
    ),
    path(
        "personas/<int:pk>/",
        PasPersonaEditarWebView.as_view(),
        name="pas_web_persona",
    ),
    path(
        "personas/<int:pk>/editar/",
        PasPersonaEditarWebView.as_view(),
        name="pas_web_persona_editar",
    ),
]
