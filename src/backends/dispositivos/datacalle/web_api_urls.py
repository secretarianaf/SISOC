"""Rutas de ``/api/web/dispositivos/datacalle/`` (G1 v1).

Ver ``datacalle.web_api`` (operativos: listado, ficha, alta, edición, cierre y
baja; DC01.01-DC01.03 de #2785). ``<uuid:pk>`` como la ruta nativa: un id que
no es UUID da 404.
"""

from django.urls import path

from datacalle.web_api import (
    DispositivosOpcionesWebView,
    RelevadoresOpcionesWebView,
    RelevamientoCerrarWebView,
    RelevamientoCreateFormWebView,
    RelevamientoCreateWebView,
    RelevamientoDeleteWebView,
    RelevamientoDetailWebView,
    RelevamientoListWebView,
    RelevamientoUpdateFormWebView,
    RelevamientoUpdateWebView,
)

urlpatterns = [
    path(
        "relevamientos/",
        RelevamientoListWebView.as_view(),
        name="web_datacalle_relevamientos",
    ),
    path(
        "relevamientos/formulario/",
        RelevamientoCreateFormWebView.as_view(),
        name="web_datacalle_formulario",
    ),
    path(
        "relevamientos/crear/",
        RelevamientoCreateWebView.as_view(),
        name="web_datacalle_crear",
    ),
    path(
        "relevamientos/<uuid:pk>/",
        RelevamientoDetailWebView.as_view(),
        name="web_datacalle_detalle",
    ),
    path(
        "relevamientos/<uuid:pk>/formulario/",
        RelevamientoUpdateFormWebView.as_view(),
        name="web_datacalle_formulario_edicion",
    ),
    path(
        "relevamientos/<uuid:pk>/editar/",
        RelevamientoUpdateWebView.as_view(),
        name="web_datacalle_editar",
    ),
    path(
        "relevamientos/<uuid:pk>/cerrar/",
        RelevamientoCerrarWebView.as_view(),
        name="web_datacalle_cerrar",
    ),
    path(
        "relevamientos/<uuid:pk>/eliminar/",
        RelevamientoDeleteWebView.as_view(),
        name="web_datacalle_eliminar",
    ),
    path(
        "opciones/dispositivos/",
        DispositivosOpcionesWebView.as_view(),
        name="web_datacalle_opciones_dispositivos",
    ),
    path(
        "opciones/relevadores/",
        RelevadoresOpcionesWebView.as_view(),
        name="web_datacalle_opciones_relevadores",
    ),
]
