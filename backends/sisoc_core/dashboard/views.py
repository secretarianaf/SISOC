from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import DetailView, TemplateView

from django.apps import apps

from core.backend_proxy import backend_de_app, pedir_json_a_backend
from dashboard.models import Dashboard, Tablero


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 1) Datos fijos
        dashboard_data = Dashboard.objects.all()
        context.update({item.llave: item.cantidad for item in dashboard_data})

        # 2) Indicadores dinámicos de Centro de Familia
        context.update(self.metricas_centro_familia())

        return context

    METRICAS_CDF_VACIAS = {
        "participantes_total": 0,
        "centros_adheridos_totales": 0,
        "centros_faro_totales": 0,
        "actividades_totales": 0,
    }

    def metricas_centro_familia(self):
        """En el mismo proceso si CDF está instalado; si no, a su backend."""
        if apps.is_installed("centrodefamilia"):
            from centrodefamilia.api import (  # pylint: disable=import-outside-toplevel
                obtener_metricas_dashboard,
            )

            return obtener_metricas_dashboard().__dict__
        backend = backend_de_app("centrodefamilia")
        datos = (
            pedir_json_a_backend(
                self.request, backend, "/centrodefamilia/metricas-dashboard/"
            )
            if backend
            else None
        )
        return {**self.METRICAS_CDF_VACIAS, **(datos or {})}


class TableroEmbedView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Muestra tableros embebidos configurados desde el admin."""

    model = Tablero
    template_name = "dashboard_tablero.html"
    slug_url_kwarg = "slug"
    context_object_name = "tablero"
    raise_exception = True

    def get_queryset(self):
        return Tablero.objects.filter(activo=True)

    def test_func(self):
        tablero = self.get_object()
        return tablero.usuario_puede_ver(self.request.user)
