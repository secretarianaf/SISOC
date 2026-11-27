"""Administración de asignaciones individuales para el equipo de Datos."""

from collections import defaultdict

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView

from dashboard.forms_asignaciones import (
    AsignacionIndividualForm,
    AsignacionLoteForm,
    RevocarIndividualForm,
)
from dashboard.models import ConcesionTablero, MiembroAudienciaTableros
from dashboard.services.equipo_datos import puede_administrar_tableros
from dashboard.services.estado_asignaciones import marcar_estado_concesiones
from dashboard.services.politicas import configuracion_progresar
from dashboard.services.gestion_concesiones import (
    agregar_concesiones,
    revocar_concesion,
)


class EquipoDatosMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return puede_administrar_tableros(self.request.user)


@method_decorator(never_cache, name="dispatch")
class BuscarUsuariosDatosView(EquipoDatosMixin, TemplateView):
    template_name = "dashboard_buscar_usuarios_datos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        busqueda = self.request.GET.get("q", "").strip()[:100]
        usuarios = get_user_model().objects.order_by("-date_joined", "-pk")
        if busqueda:
            usuarios = (
                get_user_model()
                .objects.filter(username__icontains=busqueda)
                .order_by("username", "pk")
            )
        pagina = Paginator(usuarios, 25).get_page(self.request.GET.get("page"))
        pagina.object_list = list(pagina.object_list)
        self._cargar_asignaciones(pagina.object_list)
        context.update(busqueda=busqueda, pagina=pagina)
        return context

    @staticmethod
    def _cargar_asignaciones(usuarios):
        if not usuarios:
            return

        usuarios_por_id = {usuario.pk: usuario for usuario in usuarios}
        miembros_por_audiencia = defaultdict(list)
        for audiencia_id, usuario_id in MiembroAudienciaTableros.objects.filter(
            usuario_id__in=usuarios_por_id
        ).values_list("audiencia_id", "usuario_id"):
            miembros_por_audiencia[audiencia_id].append(usuarios_por_id[usuario_id])

        for usuario in usuarios:
            usuario.asignaciones_tableros = []

        concesiones = (
            ConcesionTablero.objects.filter(
                Q(usuario_id__in=usuarios_por_id)
                | Q(audiencia_id__in=miembros_por_audiencia)
            )
            .select_related("tablero", "provincia", "audiencia")
            .order_by("tablero__nombre", "tipo", "pk")
        )
        for concesion in marcar_estado_concesiones(
            concesiones, configuracion_progresar()
        ):
            if concesion.usuario_id:
                usuarios_por_id[concesion.usuario_id].asignaciones_tableros.append(
                    concesion
                )
            else:
                for miembro in miembros_por_audiencia[concesion.audiencia_id]:
                    miembro.asignaciones_tableros.append(concesion)


@method_decorator(never_cache, name="dispatch")
class AsignacionesUsuarioView(EquipoDatosMixin, TemplateView):
    template_name = "dashboard_asignaciones_usuario.html"

    def usuario(self):
        return get_object_or_404(get_user_model(), pk=self.kwargs["usuario_id"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = self.usuario()
        context["usuario_objetivo"] = usuario
        context["formulario"] = kwargs.get("formulario") or AsignacionLoteForm()
        context["error_operacion"] = kwargs.get("error_operacion", "")
        configuracion = configuracion_progresar()
        context["individuales"] = marcar_estado_concesiones(
            ConcesionTablero.objects.filter(usuario=usuario)
            .select_related("tablero", "provincia")
            .order_by("tablero__nombre", "tipo", "pk"),
            configuracion,
        )
        context["audiencias"] = marcar_estado_concesiones(
            ConcesionTablero.objects.filter(audiencia__membresias__usuario=usuario)
            .select_related("tablero", "audiencia", "provincia")
            .order_by("tablero__nombre", "tipo", "pk"),
            configuracion,
        )
        return context

    def post(self, request, *args, **kwargs):
        usuario = self.usuario()
        accion = request.POST.get("accion")
        formularios = {
            "agregar": AsignacionIndividualForm,
            "agregar_lote": AsignacionLoteForm,
            "revocar": RevocarIndividualForm,
        }
        clase = formularios.get(accion)
        formulario = clase(request.POST) if clase else None
        lote = formulario if accion == "agregar_lote" else None
        if formulario is None or not formulario.is_valid():
            return self.render_to_response(
                self.get_context_data(
                    formulario=lote,
                    errores_legacy=formulario.errors if accion == "agregar" else None,
                    error_operacion="Revise los datos de la operación.",
                ),
                status=400,
            )
        datos = formulario.cleaned_data
        try:
            if accion == "agregar_lote":
                formulario.guardar(request, usuario=usuario)
            elif accion == "agregar":
                agregar_concesiones(
                    usuario,
                    datos["tablero"],
                    datos["tipo"],
                    [p.pk for p in datos["provincias"]],
                )
            else:
                revocar_concesion(usuario, datos["tablero"], datos["concesion"])
        except ValidationError as exc:
            return self.render_to_response(
                self.get_context_data(
                    formulario=lote, error_operacion=" ".join(exc.messages)
                ),
                status=400,
            )
        return redirect("dashboard_asignaciones_usuario", usuario_id=usuario.pk)
