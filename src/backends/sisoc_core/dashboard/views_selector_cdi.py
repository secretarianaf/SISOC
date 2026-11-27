"""Selección validada de CDI para concesiones todavía no aplicadas."""

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView, View
from dashboard.models import AudienciaTableros, Tablero
from dashboard.services.gestion_concesiones import (
    agregar_cdis_audiencia,
    agregar_cdis_usuario,
)
from dashboard.services.selector_cdi import buscar_centros
from dashboard.views_asignaciones import EquipoDatosMixin


@method_decorator(never_cache, name="dispatch")
class BuscarCDIView(EquipoDatosMixin, View):
    def get(self, request, *args, **kwargs):
        pagina = request.GET.get("page", "1")
        try:
            if not pagina.isascii() or not pagina.isdecimal() or len(pagina) > 5:
                raise ValidationError("Página inválida.")
            resultado = buscar_centros(
                request, request.GET.get("q", "").strip(), int(pagina)
            )
        except ValidationError as exc:
            return JsonResponse({"error": " ".join(exc.messages)}, status=400)
        return JsonResponse(
            {
                "results": [
                    {"id": str(centro["id"]), "text": centro["nombre"]}
                    for centro in resultado["centros"]
                ],
                "pagination": {"more": resultado["hay_mas"]},
            }
        )


class SeleccionCDIForm(forms.Form):
    tablero = forms.ModelChoiceField(queryset=Tablero.objects.all())


@method_decorator(never_cache, name="dispatch")
class SeleccionarCDIView(EquipoDatosMixin, TemplateView):
    template_name = "dashboard_seleccionar_cdis.html"

    def sujeto(self):
        tipo = self.kwargs["tipo"]
        if tipo == "usuario":
            return get_object_or_404(get_user_model(), pk=self.kwargs["sujeto_id"])
        if tipo == "audiencia":
            return get_object_or_404(AudienciaTableros, pk=self.kwargs["sujeto_id"])
        raise Http404

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            sujeto=self.sujeto(),
            formulario=SeleccionCDIForm(),
            centros=[],
            error_operacion=kwargs.get("error_operacion", ""),
            busqueda="",
            pagina=1,
            hay_mas=False,
        )
        if self.request.method == "GET":
            busqueda = self.request.GET.get("q", "").strip()
            pagina = self.request.GET.get("pagina", "1")
            try:
                if not pagina.isascii() or not pagina.isdecimal() or len(pagina) > 5:
                    raise ValidationError("Página inválida.")
                resultado = buscar_centros(self.request, busqueda, int(pagina))
                context.update(
                    centros=resultado["centros"],
                    hay_mas=resultado["hay_mas"],
                    busqueda=busqueda,
                    pagina=int(pagina),
                )
            except ValidationError as exc:
                context["error_operacion"] = " ".join(exc.messages)
        return context

    def post(self, request, *args, **kwargs):
        sujeto = self.sujeto()
        form = SeleccionCDIForm(request.POST)
        valores = request.POST.getlist("cdis")
        if (
            not form.is_valid()
            or not valores
            or len(valores) > 100
            or any(
                not valor.isascii() or not valor.isdecimal() or len(valor) > 19
                for valor in valores
            )
        ):
            return self.render_to_response(
                self.get_context_data(
                    error_operacion="Seleccione un tablero y CDI válidos."
                ),
                status=400,
            )
        try:
            ids = [int(valor) for valor in valores]
            if self.kwargs["tipo"] == "usuario":
                agregar_cdis_usuario(request, sujeto, form.cleaned_data["tablero"], ids)
                return redirect("dashboard_asignaciones_usuario", usuario_id=sujeto.pk)
            agregar_cdis_audiencia(request, sujeto, form.cleaned_data["tablero"], ids)
            return redirect("dashboard_audiencia_detalle", audiencia_id=sujeto.pk)
        except ValidationError as exc:
            return self.render_to_response(
                self.get_context_data(error_operacion=" ".join(exc.messages)),
                status=400,
            )
