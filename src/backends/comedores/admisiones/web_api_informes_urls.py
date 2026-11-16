"""Rutas de ``/api/web/comedores/admisiones/informes/`` (G1 v1).

Ver ``admisiones.web_api_informes``.
"""

from django.urls import path

from admisiones.web_api_informe_acciones import (
    InformeDocxEditadoWebView,
    InformeRevisionWebView,
)
from admisiones.web_api_informe_complementario import InformeComplementarioWebView
from admisiones.web_api_informe_formulario import InformeFormularioWebView
from admisiones.web_api_informe_guardar import InformeGuardarWebView
from admisiones.web_api_informes import InformeDetailWebView

urlpatterns = [
    path(
        "complementario/<str:tipo>/<int:pk>/",
        InformeComplementarioWebView.as_view(),
        name="informe_complementario_web",
    ),
    path(
        "<str:tipo>/<int:pk>/docx-editado/",
        InformeDocxEditadoWebView.as_view(),
        name="informe_tecnico_web_docx_editado",
    ),
    path(
        "<str:tipo>/<int:pk>/revision/",
        InformeRevisionWebView.as_view(),
        name="informe_tecnico_web_revision",
    ),
    path(
        "<str:tipo>/admision/<int:admision_id>/formulario/",
        InformeFormularioWebView.as_view(),
        name="informe_tecnico_web_formulario_crear",
    ),
    path(
        "<str:tipo>/admision/<int:admision_id>/guardar/",
        InformeGuardarWebView.as_view(),
        name="informe_tecnico_web_guardar_crear",
    ),
    path(
        "<str:tipo>/<int:pk>/guardar/",
        InformeGuardarWebView.as_view(),
        name="informe_tecnico_web_guardar_editar",
    ),
    path(
        "<str:tipo>/<int:pk>/formulario/",
        InformeFormularioWebView.as_view(),
        name="informe_tecnico_web_formulario_editar",
    ),
    path(
        "<str:tipo>/<int:pk>/",
        InformeDetailWebView.as_view(),
        name="informe_tecnico_web_detalle",
    ),
]
