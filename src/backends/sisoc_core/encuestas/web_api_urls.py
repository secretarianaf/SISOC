"""Routes of ``/api/web/encuestas/`` (G1 v1): encuestas management in the core."""

from django.urls import path

from encuestas.web_api_lista import ListaWebView, PublicarWebView, RondaCerrarWebView
from encuestas.web_api_resultados import ResultadosWebView
from encuestas.web_api_revision import (
    AprobarWebView,
    RechazarWebView,
    RevisionWebView,
)
from encuestas.web_api_segmentacion import (
    EncuestaImportarWebView,
    SegmentacionAgregarWebView,
    SegmentacionQuitarWebView,
    SegmentacionTipoWebView,
    SegmentacionWebView,
)

urlpatterns = [
    path(
        "<int:pk>/revision/", RevisionWebView.as_view(), name="encuestas_web_revision"
    ),
    path("<int:pk>/aprobar/", AprobarWebView.as_view(), name="encuestas_web_aprobar"),
    path(
        "<int:pk>/rechazar/", RechazarWebView.as_view(), name="encuestas_web_rechazar"
    ),
    path("lista/", ListaWebView.as_view(), name="encuestas_web_lista"),
    path(
        "<int:pk>/publicar/", PublicarWebView.as_view(), name="encuestas_web_publicar"
    ),
    path(
        "rondas/<int:pk>/cerrar/",
        RondaCerrarWebView.as_view(),
        name="encuestas_web_ronda_cerrar",
    ),
    path(
        "<int:pk>/resultados/",
        ResultadosWebView.as_view(),
        name="encuestas_web_resultados",
    ),
    path("importar/", EncuestaImportarWebView.as_view(), name="encuestas_web_importar"),
    path(
        "<int:pk>/segmentacion/",
        SegmentacionWebView.as_view(),
        name="encuestas_web_segmentacion",
    ),
    path(
        "<int:pk>/segmentacion/tipo/",
        SegmentacionTipoWebView.as_view(),
        name="encuestas_web_segmentacion_tipo",
    ),
    path(
        "<int:pk>/segmentacion/agregar/",
        SegmentacionAgregarWebView.as_view(),
        name="encuestas_web_segmentacion_agregar",
    ),
    path(
        "<int:pk>/segmentacion/<int:destinatario_pk>/quitar/",
        SegmentacionQuitarWebView.as_view(),
        name="encuestas_web_segmentacion_quitar",
    ),
]
