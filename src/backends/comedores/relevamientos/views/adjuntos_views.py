"""Descarga autenticada de los archivos adjuntos de los formularios (#2781)."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.views import View

from relevamientos.models import ArchivoAdjunto


class AdjuntoDescargarView(LoginRequiredMixin, View):
    """Entrega el archivo como descarga; no se sirve por ``/media/``.

    El permiso (``relevamientos.view_relevamiento``, el mismo del detalle de los
    formularios) lo exige la ruta.
    """

    def get(self, request, comedor_pk, pk):
        adjunto = get_object_or_404(ArchivoAdjunto, pk=pk, comedor_id=comedor_pk)
        try:
            archivo = adjunto.archivo.open("rb")
        except (FileNotFoundError, ValueError) as exc:
            raise Http404("El archivo no está disponible.") from exc
        response = FileResponse(
            archivo,
            as_attachment=True,
            filename=adjunto.nombre_original,
            content_type=adjunto.tipo_mime,
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response
