"""Pantallas de Montos: modelo compartido, operación e historial en Comedores."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from core.models import MontoPrestacionPrograma
from core.forms import MontoPrestacionProgramaForm
from historial.services.historial_service import HistorialService


def _registrar_historial(**kwargs):
    return HistorialService.registrar_historial(**kwargs)


class MontoPrestacionProgramaListView(LoginRequiredMixin, ListView):
    model = MontoPrestacionPrograma
    template_name = "monto_prestacion_list.html"
    context_object_name = "prestaciones"
    paginate_by = 10

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("usuario_creador", "programa")
            .order_by("id")
        )


class MontoPrestacionProgramaContextMixin:
    @staticmethod
    def _list_url():
        return reverse("montoprestacion_listar")

    def _back_button(self):
        return {
            "url": self._list_url(),
            "text": "Volver",
            "type": "outline-light",
        }

    def _breadcrumb_items(self, actual):
        return [
            {"text": "Monto de Prestaciones", "url": self._list_url()},
            {"text": actual, "active": True},
        ]

    def _form_template_context(self, actual):
        return {
            "breadcrumb_items": self._breadcrumb_items(actual),
            "back_button": self._back_button(),
            "action_buttons": [],
            "hidden_fields_send": [],
            "guardar_otro_send": False,
        }


class MontoPrestacionProgramaCreateView(
    MontoPrestacionProgramaContextMixin, LoginRequiredMixin, CreateView
):
    model = MontoPrestacionPrograma
    form_class = MontoPrestacionProgramaForm
    template_name = "monto_prestacion_form.html"
    success_url = reverse_lazy("montoprestacion_listar")

    def form_valid(self, form):
        with transaction.atomic():
            obj = form.save(commit=False)
            if not getattr(obj, "usuario_creador", None):
                obj.usuario_creador = self.request.user
            obj.save()
            self.object = obj
            _registrar_historial(
                accion="Creación de Monto de Prestación",
                instancia=obj,
                diferencias=form.cleaned_data,
            )
        messages.success(self.request, "Monto de Prestación creada correctamente.")
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._form_template_context("Crear Monto de Prestación"))
        return context


class MontoPrestacionProgramaUpdateView(
    MontoPrestacionProgramaContextMixin, LoginRequiredMixin, UpdateView
):
    model = MontoPrestacionPrograma
    form_class = MontoPrestacionProgramaForm
    template_name = "monto_prestacion_form.html"
    success_url = reverse_lazy("montoprestacion_listar")

    def form_valid(self, form):
        with transaction.atomic():
            obj = form.save()
            self.object = obj
            _registrar_historial(
                accion="Edición de Monto de Prestación",
                instancia=obj,
                diferencias=form.cleaned_data,
            )
        messages.success(self.request, "Monto de Prestación actualizado correctamente.")
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._form_template_context("Editar Monto de Prestación"))
        return context


class MontoPrestacionProgramaDeleteView(
    MontoPrestacionProgramaContextMixin, LoginRequiredMixin, DeleteView
):
    model = MontoPrestacionPrograma
    template_name = "monto_prestacion_confirm_delete.html"
    success_url = reverse_lazy("montoprestacion_listar")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = getattr(self, "object", None) or self.get_object()
        context["breadcrumb_items"] = [
            {"text": "Monto de Prestaciones", "url": self._list_url()},
            {"text": "Eliminar Monto de Prestación", "active": True},
        ]
        context["object_title"] = str(obj)
        context["delete_message"] = (
            "¿Desea eliminar este monto de prestación? Esta acción no se puede deshacer."
        )
        context["cancel_url"] = self._list_url()
        return context

    def form_valid(self, form):
        obj = getattr(self, "object", None) or self.get_object()
        self.object = obj
        with transaction.atomic():
            _registrar_historial(
                accion="Eliminación de Prestación",
                instancia=obj,
                diferencias={"programa": getattr(obj, "programa", None)},
            )
            response = super().form_valid(form)
        messages.success(self.request, "Monto de Prestación eliminado correctamente.")
        return response


class MontoPrestacionProgramaDetailView(
    MontoPrestacionProgramaContextMixin, LoginRequiredMixin, DetailView
):
    model = MontoPrestacionPrograma
    template_name = "monto_prestacion_detail.html"
    context_object_name = "prestacion"

    def get_queryset(self):
        return super().get_queryset().select_related("usuario_creador", "programa")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumb_items"] = self._breadcrumb_items("Detalle")
        context["back_button"] = self._back_button()
        context["action_buttons"] = []
        return context
