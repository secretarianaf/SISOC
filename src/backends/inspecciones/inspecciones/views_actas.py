"""Pestaña Actas: listado, detalle y archivos del acta (imágenes y PDF).

Las imágenes, la firma, las fotos de la notificación y el PDF se sirven acá,
con la sesión y el permiso del panel; ``/media/inspecciones/`` está bloqueado
en el Nginx y el almacenamiento no tiene URL pública.

La anulación y la marca de prueba son vistas aparte (``views_anulacion``):
el detalle sólo muestra los botones si esas rutas existen.
"""

from django.http import FileResponse
from django.views import View
from django.views.generic import ListView, TemplateView

from inspecciones.forms import ActasFiltroForm
from inspecciones.services.asignaciones import opcion_inspector_por_id
from inspecciones.services.panel_actas import (
    archivo_notificacion_del_acta,
    detalle_acta_panel,
    fila_de_acta,
    imagen_del_acta,
    listar_actas_panel,
    obtener_acta,
    pdf_del_acta,
)
from inspecciones.views import GestionInspeccionesMixin, PanelMixin

POR_PAGINA = 25


def respuesta_archivo(campo_archivo, *, content_type, nombre, adjunto=False):
    respuesta = FileResponse(
        campo_archivo.open("rb"),
        content_type=content_type,
        as_attachment=adjunto,
        filename=nombre,
    )
    # Evidencia con datos personales: que no quede en caches compartidas.
    respuesta["Cache-Control"] = "private, no-store"
    respuesta["X-Content-Type-Options"] = "nosniff"
    return respuesta


class ActasView(PanelMixin, ListView):
    template_name = "inspecciones/actas.html"
    context_object_name = "actas"
    paginate_by = POR_PAGINA
    pestana = "actas"
    titulo = "Actas"
    _filtro = None

    def get_filtro(self):
        if self._filtro is None:
            self._filtro = ActasFiltroForm(self.request.GET or None)
        return self._filtro

    def get_queryset(self):
        filtro = self.get_filtro()
        provincia = filtro.valor("provincia")
        return listar_actas_panel(
            fecha=filtro.valor("fecha"),
            inspector_id=filtro.valor("inspector"),
            provincia_id=provincia.pk if provincia else None,
            estado=filtro.valor("estado") or "",
            numero=filtro.valor("numero") or "",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtro = self.get_filtro()
        context.update(
            filtro=filtro,
            inspector_filtro=opcion_inspector_por_id(filtro.valor("inspector")),
            filas=[fila_de_acta(acta) for acta in context["actas"]],
        )
        return context


class _ActaMixin(GestionInspeccionesMixin):
    def get_acta(self):
        return obtener_acta(self.kwargs["numero"])


class ActaDetalleView(_ActaMixin, PanelMixin, TemplateView):
    template_name = "inspecciones/acta_detalle.html"
    pestana = "actas"

    @property
    def titulo(self):
        return self.kwargs["numero"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(detalle_acta_panel(self.get_acta()))
        return context


class ActaPdfView(_ActaMixin, View):
    def get(self, request, numero):
        acta = pdf_del_acta(self.get_acta())
        return respuesta_archivo(
            acta.pdf,
            content_type="application/pdf",
            nombre=f"{acta.numero}.pdf",
            adjunto=True,
        )


class ActaImagenView(_ActaMixin, View):
    def get(self, request, numero, imagen_uuid):
        imagen = imagen_del_acta(self.get_acta(), imagen_uuid)
        extension = "png" if imagen.mime == "image/png" else "jpg"
        return respuesta_archivo(
            imagen.archivo,
            content_type=imagen.mime,
            nombre=f"{imagen.uuid}.{extension}",
        )


class ActaArchivoNotificacionView(_ActaMixin, View):
    def get(self, request, numero, archivo_uuid):
        archivo = archivo_notificacion_del_acta(self.get_acta(), archivo_uuid)
        extension = "png" if archivo.mime == "image/png" else "jpg"
        return respuesta_archivo(
            archivo.archivo,
            content_type=archivo.mime,
            nombre=f"notificacion-{archivo.orden}.{extension}",
        )
