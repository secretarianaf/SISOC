from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import DetailView, TemplateView

from django.apps import apps

from core.backend_proxy import backend_de_app, pedir_json_a_backend
from dashboard.models import (
    Dashboard,
    Tablero,
    PERMISO_TABLERO_PROGRESAR_CURSO,
    PERMISO_TABLERO_PROGRESAR_CURSO_NACIONAL,
)
from dashboard.comedores_metrics import METRIC_KEYS, actualizar_metricas_comedores
from dashboard.services.tablero_progresar_curso import construir_tablero
from dashboard.services.politicas import (
    configuracion_progresar,
    alcance_progresar_explicito,
    es_embed_externo,
    ids_embeds_nacionales,
)
from iam.services import user_has_permission_code


@method_decorator(never_cache, name="dispatch")
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"
    EMBEDS_PORTADA = {
        "informe-centro-de-familia": "embed_centro_de_familia",
        "informe-comedores": "embed_comedores",
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        actualizadas = actualizar_metricas_comedores(self.request)

        # 1) Datos fijos
        dashboard_data = Dashboard.objects.all()
        context.update({item.llave: item.cantidad for item in dashboard_data})

        context["metricas_comedores_desactualizadas"] = (
            self.request.user.has_perm("dashboard.view_dashboard") and not actualizadas
        )
        context["metricas_comedores_disponibles"] = all(
            key in context for key in METRIC_KEYS
        )
        for key in METRIC_KEYS:
            context.setdefault(key, None)

        # 2) Indicadores dinámicos de Centro de Familia
        context.update(self.metricas_centro_familia())
        context.update(self.embeds_autorizados())

        return context

    def embeds_autorizados(self):
        """Lee las fichas de dashboard.catalogo que load_fixtures ya sincronizó.

        La autorización controla la entrega de cada URL dentro de SISOC.
        """
        usuario = self.request.user
        fichas = [
            ficha
            for ficha in Tablero.objects.filter(
                activo=True, slug__in=self.EMBEDS_PORTADA
            )
            if es_embed_externo(ficha)
        ]
        nacionales = ids_embeds_nacionales(usuario, fichas)
        embeds = dict.fromkeys(self.EMBEDS_PORTADA.values())
        for ficha in fichas:
            if ficha.usuario_puede_ver(usuario, tableros_nacionales=nacionales):
                embeds[self.EMBEDS_PORTADA[ficha.slug]] = ficha.get_embed_url()
        return embeds

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
        self.object = self.get_object()
        return self.object.usuario_puede_ver(self.request.user)

    def get(self, request, *args, **kwargs):
        # La respuesta usa la ficha ya autorizada por test_func.
        if self.object.ruta_interna:
            return redirect(self.object.ruta_interna)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


@method_decorator(never_cache, name="dispatch")
class TableroProgresarCursoView(LoginRequiredMixin, TemplateView):
    """Tablero Becas Progresar · Curso obligatorio.

    La lógica y el recorte por alcance del usuario viven en
    `dashboard/services/tablero_progresar_curso/`; acá queda la pantalla.
    La política activa se comprueba antes de construir los datos.
    """

    template_name = "tablero_progresar_curso.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        configuracion = configuracion_progresar()
        self.alcance_explicito = None
        if configuracion:
            self.alcance_explicito = alcance_progresar_explicito(
                request.user, configuracion
            )
            if not (
                self.alcance_explicito.nacional or self.alcance_explicito.provincias
            ):
                raise PermissionDenied
        elif not request.user.is_superuser and not any(
            user_has_permission_code(request.user, permiso)
            for permiso in (
                PERMISO_TABLERO_PROGRESAR_CURSO,
                PERMISO_TABLERO_PROGRESAR_CURSO_NACIONAL,
            )
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tablero_datos"] = construir_tablero(
            self.request.user, getattr(self, "alcance_explicito", None)
        )
        return context
