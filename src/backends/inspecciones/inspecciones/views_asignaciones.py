"""Pestaña Asignaciones: listado por jornada, alta de a una y baja."""

from datetime import timedelta

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import urlencode
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.edit import FormView

from inspecciones.forms import (
    AsignacionesFiltroForm,
    AsignacionForm,
    ImportarArchivoForm,
)
from inspecciones.models import AsignacionEscuela
from inspecciones.services.asignaciones import (
    asignaciones_de_jornada,
    crear_asignacion,
    opcion_inspector,
    opcion_inspector_por_id,
    otras_asignaciones,
    quitar_asignacion,
)
from inspecciones.services.catalogo import opcion_escuela, opcion_escuela_por_id
from inspecciones.services.formato import hoy, nombre_actor
from inspecciones.views import PanelMixin, es_parcial

POR_PAGINA = 25


def _url_jornada(fecha, parametros):
    datos = {k: v for k, v in parametros.items() if k not in ("fecha", "page")}
    datos["fecha"] = fecha.isoformat()
    return reverse("inspecciones_asignaciones") + "?" + urlencode(datos)


class AsignacionesView(PanelMixin, TemplateView):
    template_name = "inspecciones/asignaciones.html"
    pestana = "asignaciones"
    titulo = "Asignaciones"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtro = AsignacionesFiltroForm(self.request.GET or None)
        fecha = filtro.valor("fecha") or hoy()
        provincia = filtro.valor("provincia")
        inspector_id = filtro.valor("inspector")
        escuela_id = filtro.valor("escuela")
        filas, totales = asignaciones_de_jornada(
            fecha,
            inspector_id=inspector_id,
            escuela_id=escuela_id,
            provincia_id=provincia.pk if provincia else None,
            estado=filtro.valor("estado") or "",
            estado_acta=filtro.valor("estado_acta") or "",
        )
        pagina = Paginator(filas, POR_PAGINA).get_page(self.request.GET.get("page"))
        parametros = self.request.GET
        context.update(
            filtro=filtro,
            fecha=fecha,
            es_hoy=fecha == hoy(),
            url_anterior=_url_jornada(fecha - timedelta(days=1), parametros),
            url_siguiente=_url_jornada(fecha + timedelta(days=1), parametros),
            url_hoy=_url_jornada(hoy(), parametros),
            filas=pagina.object_list,
            page_obj=pagina,
            is_paginated=pagina.has_other_pages(),
            totales=totales,
            inspector_filtro=opcion_inspector_por_id(inspector_id),
            escuela_filtro=opcion_escuela_por_id(escuela_id),
            form_importar=ImportarArchivoForm(),
        )
        return context


class AsignacionCrearView(PanelMixin, FormView):
    """Alta de a una, en el modal ("Asignar" y "Asignar y cargar otra")."""

    form_class = AsignacionForm
    titulo = "Nueva asignación"
    pestana = "asignaciones"

    def get_template_names(self):
        if es_parcial(self.request):
            return ["inspecciones/partials/asignacion_form.html"]
        return ["inspecciones/asignacion_form_page.html"]

    def get_initial(self):
        inicial = super().get_initial()
        fecha = self.request.GET.get("fecha")
        if fecha:
            inicial["fecha"] = fecha
        return inicial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context["form"]
        context["form_action"] = self.request.path
        if form.is_bound and hasattr(form, "cleaned_data"):
            inspector = form.cleaned_data.get("inspector")
            escuela = form.cleaned_data.get("escuela")
            context["inspector_inicial"] = (
                opcion_inspector(inspector) if inspector else None
            )
            context["escuela_inicial"] = opcion_escuela(escuela) if escuela else None
        return context

    def form_invalid(self, form):
        respuesta = super().form_invalid(form)
        if es_parcial(self.request):
            respuesta.status_code = 400
        return respuesta

    def form_valid(self, form):
        datos = form.cleaned_data
        otros = otras_asignaciones(
            datos["escuela"], datos["fecha"], excluir_inspector_id=datos["inspector"].pk
        )
        try:
            crear_asignacion(
                escuela=datos["escuela"],
                inspector=datos["inspector"],
                fecha=datos["fecha"],
                actor=self.request.user,
            )
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        mensaje = (
            f"Se asignó {datos['escuela'].nombre} a {nombre_actor(datos['inspector'])}"
            f" para el {datos['fecha']:%d/%m/%Y}."
        )
        if otros:
            mensaje += f" También la tiene asignada {', '.join(otros)} (otra visita)."
        otra = "otra" in self.request.POST
        if es_parcial(self.request):
            if not otra:
                messages.success(self.request, mensaje)
            return JsonResponse({"ok": True, "mensaje": mensaje, "otra": otra})
        messages.success(self.request, mensaje)
        if otra:
            return redirect(
                reverse("inspecciones_asignacion_nueva")
                + "?"
                + urlencode({"fecha": datos["fecha"].isoformat()})
            )
        return redirect(_url_jornada(datos["fecha"], {}))


class AsignacionQuitarView(PanelMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        asignacion = get_object_or_404(AsignacionEscuela, pk=pk)
        try:
            quitar_asignacion(asignacion, actor=request.user)
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
        else:
            messages.success(
                request,
                f"Se quitó la asignación de {asignacion.escuela.nombre} a "
                f"{nombre_actor(asignacion.inspector)}.",
            )
        return redirect(_url_jornada(asignacion.fecha, {}))
