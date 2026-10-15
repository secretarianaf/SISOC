"""Tablero en vivo de coordinación: página, datos JSON y exportación CSV.

Las tres rutas exigen sesión y ``puede_gestionar`` (403 sin permiso). La
lógica vive en ``inspecciones.services.tablero``; la página se actualiza
consultando ``inspecciones_tablero_datos`` cada 5 segundos (sin WebSockets:
el stack corre con gunicorn síncrono y sin Redis).
"""

from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView

from core.services.csv_export import build_csv_response
from inspecciones.services.tablero import (
    datos_tablero,
    escribir_csv,
    leer_filtros,
    nombre_archivo_csv,
    opciones_filtros,
)
from inspecciones.views import GestionInspeccionesMixin, LayoutInspeccionesMixin

INTERVALO_MS = 5_000


class TableroView(LayoutInspeccionesMixin, GestionInspeccionesMixin, TemplateView):
    template_name = "inspecciones/tablero.html"
    titulo = "Tablero"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filtros"] = leer_filtros(self.request.GET)
        context["opciones"] = opciones_filtros()
        context["intervalo_ms"] = INTERVALO_MS
        return context


class TableroDatosView(GestionInspeccionesMixin, View):
    http_method_names = ["get"]

    def get(self, request):
        response = JsonResponse(datos_tablero(leer_filtros(request.GET)))
        response["Cache-Control"] = "no-store"
        return response


class TableroExportarView(GestionInspeccionesMixin, View):
    http_method_names = ["get"]

    def get(self, request):
        filtros = leer_filtros(request.GET)
        response = build_csv_response(nombre_archivo_csv(filtros))
        response["Cache-Control"] = "no-store"
        escribir_csv(response, filtros)
        return response
