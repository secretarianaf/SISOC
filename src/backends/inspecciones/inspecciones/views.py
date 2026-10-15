"""Backoffice mínimo de Inspecciones escolares: importar escuelas y asignaciones."""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.views.generic.edit import FormView

from inspecciones.access import puede_gestionar
from inspecciones.forms import ImportarCSVForm
from inspecciones.services.importacion import (
    importar_asignaciones,
    importar_escuelas,
)
from inspecciones.services.panel import resumen_panel


class GestionInspeccionesMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return puede_gestionar(self.request.user)


class PanelInspeccionesView(GestionInspeccionesMixin, FormView):
    """Panel con los dos importadores. Cada subclase procesa uno."""

    template_name = "inspecciones/panel.html"
    form_class = ImportarCSVForm
    importador = None
    titulo_resultado = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["resumen"] = resumen_panel()
        context.setdefault("form_escuelas", ImportarCSVForm(prefix="escuelas"))
        context.setdefault("form_asignaciones", ImportarCSVForm(prefix="asignaciones"))
        context["breadcrumb_items"] = [{"text": "Inspecciones escolares"}]
        return context

    def post(self, request, *args, **kwargs):
        return self.http_method_not_allowed(request, *args, **kwargs)


class _ImportarView(PanelInspeccionesView):
    prefijo = ""

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "prefix": self.prefijo}

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        contexto = {f"form_{self.prefijo}": form}
        if form.is_valid():
            try:
                resultado = self.importar(form.cleaned_data["archivo"])
            except ValidationError as exc:
                form.add_error("archivo", exc)
            else:
                contexto["resultado"] = resultado
                contexto["titulo_resultado"] = self.titulo_resultado
                contexto[f"form_{self.prefijo}"] = ImportarCSVForm(prefix=self.prefijo)
        return self.render_to_response(self.get_context_data(**contexto))

    def importar(self, archivo):
        raise NotImplementedError


class ImportarEscuelasView(_ImportarView):
    prefijo = "escuelas"
    titulo_resultado = "Importación de escuelas"

    def importar(self, archivo):
        return importar_escuelas(archivo)


class ImportarAsignacionesView(_ImportarView):
    prefijo = "asignaciones"
    titulo_resultado = "Importación de asignaciones"

    def importar(self, archivo):
        return importar_asignaciones(archivo, actor=self.request.user)
