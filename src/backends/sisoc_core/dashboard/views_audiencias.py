"""Pantallas de audiencias exclusivamente para tableros."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView, View
from dashboard.forms_asignaciones import (
    AsignacionIndividualForm,
    AsignacionLoteForm,
    RevocarIndividualForm,
)
from dashboard.forms_audiencias import (
    AudienciaForm,
    MiembroIdForm,
    MiembroNombreForm,
    MiembrosLoteForm,
    usuarios_elegibles_para_audiencia,
)
from dashboard.models import AudienciaTableros
from dashboard.services.gestion_concesiones import (
    agregar_concesiones_audiencia,
    revocar_concesion_audiencia,
)
from dashboard.services.estado_asignaciones import marcar_estado_concesiones
from dashboard.services.politicas import configuracion_progresar
from dashboard.views_asignaciones import EquipoDatosMixin


@method_decorator(never_cache, name="dispatch")
class AudienciasDatosView(EquipoDatosMixin, TemplateView):
    template_name = "dashboard_audiencias_datos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["formulario"] = kwargs.get("formulario") or AudienciaForm()
        context["audiencias"] = AudienciaTableros.objects.order_by("nombre", "pk")
        return context

    def post(self, request, *args, **kwargs):
        formulario = AudienciaForm(request.POST)
        if formulario.is_valid():
            audiencia = formulario.save()
            return redirect("dashboard_audiencia_detalle", audiencia_id=audiencia.pk)
        return self.render_to_response(
            self.get_context_data(formulario=formulario), status=400
        )


@method_decorator(never_cache, name="dispatch")
class BuscarMiembrosAudienciaView(EquipoDatosMixin, View):
    def get(self, request, audiencia_id):
        audiencia = get_object_or_404(AudienciaTableros, pk=audiencia_id)
        termino = request.GET.get("q", "").strip()
        if not 1 <= len(termino) <= 150:
            return JsonResponse({"results": []})
        usuarios = (
            usuarios_elegibles_para_audiencia()
            .filter(username__icontains=termino)
            .exclude(pk__in=audiencia.membresias.values("usuario_id"))
            .order_by("username", "pk")
            .values_list("pk", "username")[:25]
        )
        return JsonResponse(
            {"results": [{"id": str(pk), "text": nombre} for pk, nombre in usuarios]}
        )


@method_decorator(never_cache, name="dispatch")
class AudienciaDetalleView(EquipoDatosMixin, TemplateView):
    template_name = "dashboard_audiencia_detalle.html"

    def audiencia(self):
        return get_object_or_404(AudienciaTableros, pk=self.kwargs["audiencia_id"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        audiencia = self.audiencia()
        context.update(
            audiencia=audiencia,
            formulario_nombre=AudienciaForm(instance=audiencia),
            formulario_miembro=kwargs.get("formulario_miembro") or MiembrosLoteForm(),
            formulario_concesion=kwargs.get("formulario_concesion")
            or AsignacionLoteForm(),
            miembros=audiencia.membresias.select_related("usuario").order_by(
                "usuario__username"
            ),
            concesiones=marcar_estado_concesiones(
                audiencia.concesiones.select_related("tablero", "provincia").order_by(
                    "tablero__nombre", "tipo", "pk"
                ),
                configuracion_progresar(),
            ),
            error_operacion=kwargs.get("error_operacion", ""),
        )
        return context

    def post(self, request, *args, **kwargs):
        audiencia = self.audiencia()
        accion = request.POST.get("accion")
        if accion == "agregar_lote":
            return self.agregar_lote(request, audiencia)
        formas = {
            "renombrar": lambda: AudienciaForm(request.POST, instance=audiencia),
            "agregar_miembro": lambda: MiembroNombreForm(request.POST),
            "agregar_miembros": lambda: MiembrosLoteForm(request.POST),
            "quitar_miembro": lambda: MiembroIdForm(request.POST),
            "agregar_concesion": lambda: AsignacionIndividualForm(request.POST),
            "revocar_concesion": lambda: RevocarIndividualForm(request.POST),
        }
        if accion not in formas:
            return self.render_to_response(
                self.get_context_data(error_operacion="Operación inválida."), status=400
            )
        form = formas[accion]()
        if not form.is_valid():
            return self.render_to_response(
                self.get_context_data(
                    error_operacion="Revise los datos de la operación.",
                    formulario_miembro=form if accion == "agregar_miembros" else None,
                ),
                status=400,
            )
        datos = form.cleaned_data
        try:
            with transaction.atomic():
                audiencia = AudienciaTableros.objects.select_for_update().get(
                    pk=audiencia.pk
                )
                if accion == "renombrar":
                    audiencia.nombre = datos["nombre"]
                    audiencia.save(update_fields=["nombre"])
                elif accion == "agregar_miembro":
                    usuario = (
                        usuarios_elegibles_para_audiencia()
                        .filter(username=datos["username"])
                        .first()
                    )
                    if usuario is None:
                        raise ValidationError("El usuario no existe.")
                    audiencia.agregar_miembro(usuario)
                elif accion == "agregar_miembros":
                    for usuario in datos["usuarios"]:
                        audiencia.agregar_miembro(usuario)
                elif accion == "quitar_miembro":
                    usuario = get_object_or_404(get_user_model(), pk=datos["usuario"])
                    audiencia.quitar_miembro(usuario)
                elif accion == "agregar_concesion":
                    agregar_concesiones_audiencia(
                        audiencia,
                        datos["tablero"],
                        datos["tipo"],
                        [p.pk for p in datos["provincias"]],
                    )
                else:
                    revocar_concesion_audiencia(
                        audiencia, datos["tablero"], datos["concesion"]
                    )
        except ValidationError as exc:
            return self.render_to_response(
                self.get_context_data(
                    error_operacion=" ".join(exc.messages),
                    formulario_miembro=form if accion == "agregar_miembros" else None,
                ),
                status=400,
            )
        return redirect("dashboard_audiencia_detalle", audiencia_id=audiencia.pk)

    def agregar_lote(self, request, audiencia):
        formulario = AsignacionLoteForm(request.POST)
        error = "Revise los datos de la operación."
        if formulario.is_valid():
            try:
                formulario.guardar(request, audiencia=audiencia)
            except ValidationError as exc:
                error = " ".join(exc.messages)
            else:
                return redirect(
                    "dashboard_audiencia_detalle", audiencia_id=audiencia.pk
                )
        return self.render_to_response(
            self.get_context_data(
                formulario_concesion=formulario, error_operacion=error
            ),
            status=400,
        )
