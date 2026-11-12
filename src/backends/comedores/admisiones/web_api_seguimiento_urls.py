"""Rutas de ``/api/web/comedores/admisiones/`` del circuito técnico/legal (AD03).

Ver ``admisiones.web_api_listas``.
"""

from django.urls import path

from admisiones.web_api_listas import LegalesListaWebView, TecnicosListaWebView

urlpatterns = [
    path("tecnicos/", TecnicosListaWebView.as_view(), name="admisiones_web_tecnicos"),
    path("legales/", LegalesListaWebView.as_view(), name="admisiones_web_legales"),
]
