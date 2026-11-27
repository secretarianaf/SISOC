"""Tablero de seguimiento de Celiaquía."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import TemplateView

from celiaquia.services.tablero_service import (  # pylint: disable=no-name-in-module
    construir_tablero,
)


class TableroCeliaquiaView(LoginRequiredMixin, TemplateView):
    template_name = "celiaquia/tablero.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        provincias = getattr(self.request, "_provincias_tablero_celiaquia", None)
        context["tablero_datos"] = construir_tablero(provincias_visibles=provincias)
        # El enlace al expediente solo sirve a quien puede abrirlo.
        context["url_expediente"] = (
            reverse("expediente_detail", args=[0])
            if self.request.user.has_perm("celiaquia.view_expediente")
            else ""
        )
        return context
