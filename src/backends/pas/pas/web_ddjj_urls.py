"""Public DDJJ JSON routes; outside ``/api/`` so the web session middleware applies."""

from django.urls import path

from pas.web_ddjj import PasDDJJFormularioDatosView, PasDDJJFormularioEnvioView

urlpatterns = [
    path(
        "pas/ddjj/formulario/<uuid:token>/datos",
        PasDDJJFormularioDatosView.as_view(),
        name="pas_ddjj_formulario_datos",
    ),
    path(
        "pas/ddjj/formulario/<uuid:token>/enviar",
        PasDDJJFormularioEnvioView.as_view(),
        name="pas_ddjj_formulario_enviar",
    ),
]
