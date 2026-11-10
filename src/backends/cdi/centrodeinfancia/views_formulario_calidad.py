"""Vistas del Formulario de Calidad de los CDI (200_CalidadCDI)."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, ListView

from centrodeinfancia.access import (
    aplicar_scope_centros_cdi,
    puede_editar_formulario_calidad,
    puede_ver_formularios_calidad,
)
from centrodeinfancia.formulario_calidad_schema import (
    CARTEL_INICIAL,
    CHECKBOX,
    SECCIONES,
    pregunta_visible,
)
from centrodeinfancia.forms_formulario_calidad import FormularioCalidadCDIForm
from centrodeinfancia.models import CentroDeInfancia, FormularioCalidadCDI
from centrodeinfancia.services_formulario_calidad import (
    FormularioIncompletoError,
    enviar_formulario,
    guardar_borrador,
    obtener_borrador,
)

ACCION_GUARDAR = "guardar"
ACCION_ENVIAR = "enviar"


def _obtener_centro_o_404(user, pk):
    queryset = aplicar_scope_centros_cdi(
        CentroDeInfancia.objects.select_related("provincia", "departamento"), user
    )
    return get_object_or_404(queryset, pk=pk)


def _texto_opcion(pregunta, valor):
    if valor is None:
        return "-"
    return dict(pregunta.choices).get(valor, str(valor))


def construir_detalle(formulario):
    """Respuestas legibles por sección; omite lo que el pase condicional ocultó."""
    secciones = []
    for seccion in SECCIONES:
        items = []
        for pregunta in seccion.preguntas:
            if not pregunta_visible(pregunta, formulario):
                continue
            item = {"pregunta": pregunta, "valor": None, "filas": []}
            if pregunta.tipo == CHECKBOX:
                seleccion = [
                    etiqueta
                    for fila, etiqueta in pregunta.filas
                    if getattr(formulario, pregunta.nombre_campo(fila))
                ]
                item["valor"] = ", ".join(seleccion) or "-"
            elif pregunta.filas:
                for fila, etiqueta in pregunta.filas:
                    valor = getattr(formulario, pregunta.nombre_campo(fila))
                    item["filas"].append(
                        {
                            "etiqueta": etiqueta,
                            "valor": (
                                _texto_opcion(pregunta, valor)
                                if pregunta.opciones
                                else ("-" if valor is None else valor)
                            ),
                        }
                    )
            else:
                valor = getattr(formulario, pregunta.nombre_campo())
                item["valor"] = (
                    _texto_opcion(pregunta, valor)
                    if pregunta.opciones
                    else ("-" if valor is None else valor)
                )
            if pregunta.campo_especificar:
                item["especificar"] = getattr(formulario, pregunta.campo_especificar)
            items.append(item)
        secciones.append({"seccion": seccion, "items": items})
    return secciones


def contexto_legajo_calidad(user, centro):
    """Datos de la tarjeta "Formulario de Calidad" del legajo del CDI."""
    puede_ver = puede_ver_formularios_calidad(user, centro)
    puede_editar = puede_editar_formulario_calidad(user, centro)
    enviados = FormularioCalidadCDI.objects.none()
    if puede_ver:
        enviados = FormularioCalidadCDI.objects.filter(
            centro=centro, estado=FormularioCalidadCDI.Estado.ENVIADO
        ).select_related("enviado_por")
    return {
        "calidad_puede_ver": puede_ver,
        "calidad_puede_editar": puede_editar,
        "calidad_borrador": obtener_borrador(centro) if puede_editar else None,
        "calidad_total": enviados.count() if puede_ver else 0,
        "calidad_recientes": list(enviados[:3]) if puede_ver else [],
    }


class FormularioCalidadCentroMixin(LoginRequiredMixin):
    def get_centro(self):
        if not hasattr(self, "_centro"):
            self._centro = _obtener_centro_o_404(self.request.user, self.kwargs["pk"])
        return self._centro


class FormularioCalidadListView(FormularioCalidadCentroMixin, ListView):
    template_name = "centrodeinfancia/formulario_calidad_list.html"
    context_object_name = "formularios"
    paginate_by = 10

    def get_queryset(self):
        centro = self.get_centro()
        if not puede_ver_formularios_calidad(self.request.user, centro):
            raise PermissionDenied
        return FormularioCalidadCDI.objects.filter(
            centro=centro, estado=FormularioCalidadCDI.Estado.ENVIADO
        ).select_related("enviado_por")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        centro = self.get_centro()
        puede_editar = puede_editar_formulario_calidad(self.request.user, centro)
        context.update(
            {
                "centro": centro,
                "puede_editar": puede_editar,
                "borrador": obtener_borrador(centro) if puede_editar else None,
                "volver_url": reverse(
                    "centrodeinfancia_detalle", kwargs={"pk": centro.pk}
                ),
            }
        )
        return context


class FormularioCalidadDetailView(FormularioCalidadCentroMixin, DetailView):
    template_name = "centrodeinfancia/formulario_calidad_detail.html"
    context_object_name = "formulario"
    pk_url_kwarg = "form_pk"

    def get_queryset(self):
        centro = self.get_centro()
        if not puede_ver_formularios_calidad(self.request.user, centro):
            raise PermissionDenied
        return FormularioCalidadCDI.objects.filter(
            centro=centro, estado=FormularioCalidadCDI.Estado.ENVIADO
        ).select_related("enviado_por", "jurisdiccion", "departamento")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["centro"] = self.get_centro()
        context["detalle"] = construir_detalle(self.object)
        return context


class FormularioCalidadCargarView(FormularioCalidadCentroMixin, View):
    """Alta o continuación del borrador vigente del CDI."""

    template_name = "centrodeinfancia/formulario_calidad_form.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not puede_editar_formulario_calidad(
            request.user, self.get_centro()
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_instance(self):
        return obtener_borrador(self.get_centro()) or FormularioCalidadCDI(
            centro=self.get_centro()
        )

    def render_form(self, form, errores=None):
        return render(
            self.request,
            self.template_name,
            {
                "centro": self.get_centro(),
                "form": form,
                "secciones": form.secciones(errores),
                "errores": errores or {},
                "cartel_inicial": CARTEL_INICIAL,
                "es_borrador_existente": bool(form.instance.pk),
            },
        )

    def get(self, request, *args, **kwargs):
        return self.render_form(FormularioCalidadCDIForm(instance=self.get_instance()))

    def post(self, request, *args, **kwargs):
        centro = self.get_centro()
        form = FormularioCalidadCDIForm(request.POST, instance=self.get_instance())
        if not form.is_valid():
            messages.error(request, "Revisá los valores marcados.")
            return self.render_form(form)

        formulario = form.save(commit=False)
        if request.POST.get("accion") == ACCION_ENVIAR:
            try:
                enviar_formulario(formulario, centro, request.user)
            except FormularioIncompletoError as exc:
                messages.warning(
                    request,
                    "Se guardó el avance como borrador. Para enviarlo, completá "
                    f"las {len(exc.errores)} preguntas marcadas en rojo.",
                )
                form = FormularioCalidadCDIForm(instance=formulario)
                return self.render_form(form, exc.errores)
            messages.success(request, "Formulario de Calidad enviado correctamente.")
            return redirect(
                "centrodeinfancia_calidad_detalle",
                pk=centro.pk,
                form_pk=formulario.pk,
            )

        guardar_borrador(formulario, centro, request.user)
        messages.success(
            request, "Formulario guardado como borrador. Podés completarlo luego."
        )
        return redirect("centrodeinfancia_detalle", pk=centro.pk)
