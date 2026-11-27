"""Administración específica del catálogo por el equipo de Datos."""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView

from dashboard.forms_datos import TableroOperativoForm
from dashboard.models import Tablero
from dashboard.services.equipo_datos import puede_administrar_tableros


@method_decorator(never_cache, name="dispatch")
class AdministracionDatosView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Solo permite modificar campos operativos, nunca los técnicos."""

    template_name = "dashboard_administracion_datos.html"
    raise_exception = True

    def test_func(self):
        return puede_administrar_tableros(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bound_form = kwargs.get("bound_form")
        context["formularios"] = [
            (
                bound_form
                if bound_form and bound_form.instance.pk == tablero.pk
                else TableroOperativoForm(
                    instance=tablero, auto_id=f"id_{tablero.pk}_%s"
                )
            )
            for tablero in Tablero.objects.all()
        ]
        return context

    def post(self, request, *args, **kwargs):
        tablero_id = request.POST.get("tablero", "")
        if not tablero_id.isascii() or not tablero_id.isdecimal():
            raise Http404
        tablero = get_object_or_404(Tablero, pk=tablero_id)
        form = TableroOperativoForm(
            request.POST, instance=tablero, auto_id=f"id_{tablero.pk}_%s"
        )
        if form.is_valid():
            actualizado = form.save(commit=False)
            actualizado.save(update_fields=("nombre", "activo", "visible_menu"))
            return redirect("dashboard_administracion_datos")
        return self.render_to_response(
            self.get_context_data(bound_form=form), status=400
        )
