"""Pestaña Escuelas: listado paginado, alta y edición en un modal."""

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import urlencode
from django.views.generic import ListView
from django.views.generic.edit import FormView

from inspecciones.forms import EscuelaForm, EscuelasFiltroForm, ImportarArchivoForm
from inspecciones.models import Escuela
from inspecciones.services.catalogo import (
    contar_a_revisar,
    guardar_escuela,
    listar_escuelas,
)
from inspecciones.services.geografia import opcion_localidad_por_id
from inspecciones.views import PanelMixin, es_parcial

POR_PAGINA = 25


class EscuelasView(PanelMixin, ListView):
    """Listado del catálogo con buscador, filtros y chip "A revisar"."""

    template_name = "inspecciones/escuelas.html"
    context_object_name = "escuelas"
    paginate_by = POR_PAGINA
    pestana = "escuelas"
    _filtro = None

    def get_filtro(self):
        if self._filtro is None:
            self._filtro = EscuelasFiltroForm(self.request.GET or None)
        return self._filtro

    def _provincia_id(self):
        provincia = self.get_filtro().valor("provincia")
        return provincia.pk if provincia else None

    def get_queryset(self):
        filtro = self.get_filtro()
        provincia_id = self._provincia_id()
        return listar_escuelas(
            texto=filtro.valor("q") or "",
            provincia_id=provincia_id,
            localidad_id=filtro.valor("localidad") if provincia_id else None,
            a_revisar=bool(filtro.valor("a_revisar")),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtro = self.get_filtro()
        provincia_id = self._provincia_id()
        context.update(
            filtro=filtro,
            a_revisar_activo=bool(filtro.valor("a_revisar")),
            contador_a_revisar=contar_a_revisar(provincia_id=provincia_id),
            localidad_filtro=(
                opcion_localidad_por_id(
                    filtro.valor("localidad"), provincia_id=provincia_id
                )
                if provincia_id
                else None
            ),
            form_importar=ImportarArchivoForm(),
            parametros_sin_revisar=self._parametros(sin="a_revisar"),
            # Link "Abrir para editar" del aviso de Cueanexo repetido.
            editar_id=(self.request.GET.get("editar") or "").isdigit()
            and int(self.request.GET["editar"]),
        )
        return context

    def _parametros(self, *, sin):
        datos = {k: v for k, v in self.request.GET.items() if k not in (sin, "page")}
        return urlencode(datos)


class _EscuelaFormView(PanelMixin, FormView):
    """Alta y edición: el mismo formulario, en el modal o como página."""

    form_class = EscuelaForm
    escuela = None

    def get_template_names(self):
        if es_parcial(self.request):
            return ["inspecciones/partials/escuela_form.html"]
        return ["inspecciones/escuela_form_page.html"]

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "escuela": self.escuela}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context["form"]
        localidad_id = (
            form.data.get("localidad")
            if form.is_bound
            else (self.escuela.localidad_vinculada_id if self.escuela else None)
        )
        context.update(
            escuela=self.escuela,
            form_action=self.request.path,
            localidad_inicial=opcion_localidad_por_id(localidad_id),
        )
        return context

    def form_invalid(self, form):
        respuesta = super().form_invalid(form)
        if es_parcial(self.request):
            respuesta.status_code = 400
        return respuesta

    def form_valid(self, form):
        escuela = guardar_escuela(self.escuela or Escuela(), form.cleaned_data)
        otra = "otra" in self.request.POST
        mensaje = self.mensaje_exito(escuela)
        if es_parcial(self.request):
            if not otra:
                messages.success(self.request, mensaje)
            return JsonResponse({"ok": True, "mensaje": mensaje, "otra": otra})
        messages.success(self.request, mensaje)
        if otra:
            return redirect("inspecciones_escuela_nueva")
        return redirect(
            reverse("inspecciones_panel") + "?" + urlencode({"q": escuela.cueanexo})
        )

    def mensaje_exito(self, escuela):
        raise NotImplementedError


class EscuelaCrearView(_EscuelaFormView):
    titulo = "Nueva escuela"

    def mensaje_exito(self, escuela):
        return f"Se agregó la escuela {escuela.nombre} ({escuela.cueanexo})."


class EscuelaEditarView(_EscuelaFormView):
    titulo = "Editar escuela"

    def get_form_kwargs(self):
        # Se busca acá y no en ``setup``: primero se verifica el permiso.
        if self.escuela is None:
            self.escuela = get_object_or_404(Escuela, pk=self.kwargs["pk"])
        return super().get_form_kwargs()

    def mensaje_exito(self, escuela):
        return f"Se guardaron los cambios de {escuela.nombre} ({escuela.cueanexo})."
