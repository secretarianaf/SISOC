"""API que consume la PWA Sisoc Inspecciones (``/api/inspecciones/``).

Vistas sin lógica: validan la forma del pedido, llaman al service y traducen
sus errores (``inspecciones.services.errores``) a HTTP. Autenticación con el
Token DRF de ``POST /api/users/login/``; sólo usuarios del programa.
"""

from django.http import FileResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from inspecciones.api_permissions import TieneAccesoInspecciones
from inspecciones.api_serializers import (
    ImagenUploadSerializer,
    NotificacionUploadSerializer,
    PdfUploadSerializer,
)
from inspecciones.services.acceso import imagen_visible
from inspecciones.services.actas import (
    detalle_acta,
    listar_actas,
    obtener_pdf,
    subir_pdf,
)
from inspecciones.services.borradores import (
    descartar_borrador,
    guardar_borrador,
    listar_borradores,
)
from inspecciones.services.cierre import finalizar_inspeccion
from inspecciones.services.errores import ErrorInspecciones
from inspecciones.services.escuelas import (
    buscar_escuelas,
    escuelas_asignadas,
    ficha_escuela,
)
from inspecciones.services.imagenes import eliminar_imagen, subir_imagen
from inspecciones.services.notificaciones import (
    archivo_notificacion_visible,
    cargar_notificacion,
)


def _archivo(campo_archivo, *, content_type, nombre, adjunto=False):
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


@extend_schema(tags=["Inspecciones"])
class InspeccionesAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [TieneAccesoInspecciones]
    parser_classes = [JSONParser]

    def handle_exception(self, exc):
        if isinstance(exc, ErrorInspecciones):
            return Response(exc.cuerpo(), status=exc.status_code)
        return super().handle_exception(exc)


class EscuelasAsignadasView(InspeccionesAPIView):
    def get(self, request):
        return Response(escuelas_asignadas(request.user))


class EscuelasBusquedaView(InspeccionesAPIView):
    def get(self, request):
        return Response(buscar_escuelas(request.query_params.get("q", "")))


class EscuelaFichaView(InspeccionesAPIView):
    def get(self, request, codigo):
        return Response(ficha_escuela(codigo, request.user))


class BorradoresView(InspeccionesAPIView):
    def get(self, request):
        return Response(listar_borradores(request.user))


class BorradorView(InspeccionesAPIView):
    def put(self, request, inspeccion_uuid):
        return Response(guardar_borrador(request.user, inspeccion_uuid, request.data))

    def delete(self, request, inspeccion_uuid):
        descartar_borrador(request.user, inspeccion_uuid)
        return Response(status=status.HTTP_204_NO_CONTENT)


class FinalizarView(InspeccionesAPIView):
    def post(self, request, inspeccion_uuid):
        return Response(
            finalizar_inspeccion(request.user, inspeccion_uuid, request.data)
        )


class ImagenBorradorView(InspeccionesAPIView):
    parser_classes = [MultiPartParser, FormParser]

    def put(self, request, inspeccion_uuid, imagen_uuid):
        serializer = ImagenUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        return Response(
            subir_imagen(
                request.user,
                inspeccion_uuid,
                imagen_uuid,
                archivo=datos["archivo"],
                tipo=datos["tipo"],
                descripcion=datos["descripcion"],
                capturada_at=datos["capturada_at"],
            )
        )

    def delete(self, request, inspeccion_uuid, imagen_uuid):
        eliminar_imagen(request.user, inspeccion_uuid, imagen_uuid)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ImagenView(InspeccionesAPIView):
    def get(self, request, imagen_uuid):
        imagen = imagen_visible(request.user, imagen_uuid)
        extension = "png" if imagen.mime == "image/png" else "jpg"
        return _archivo(
            imagen.archivo,
            content_type=imagen.mime,
            nombre=f"{imagen.uuid}.{extension}",
        )


class ActasView(InspeccionesAPIView):
    def get(self, request):
        alcance = request.query_params.get("alcance", "")
        return Response(listar_actas(request.user, alcance=alcance))


class ActaView(InspeccionesAPIView):
    def get(self, request, numero):
        return Response(detalle_acta(request.user, numero))


class ActaPdfView(InspeccionesAPIView):
    parser_classes = [MultiPartParser, FormParser]

    def put(self, request, numero):
        serializer = PdfUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            subir_pdf(request.user, numero, serializer.validated_data["archivo"])
        )

    def get(self, request, numero):
        acta = obtener_pdf(request.user, numero)
        return _archivo(
            acta.pdf,
            content_type="application/pdf",
            nombre=f"{acta.numero}.pdf",
            adjunto=True,
        )


class NotificacionesView(InspeccionesAPIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, numero):
        serializer = NotificacionUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            cargar_notificacion(
                request.user,
                numero,
                serializer.validated_data,
                request.FILES.getlist("archivos"),
            )
        )


class ArchivoNotificacionView(InspeccionesAPIView):
    def get(self, request, archivo_uuid):
        archivo = archivo_notificacion_visible(request.user, archivo_uuid)
        extension = "png" if archivo.mime == "image/png" else "jpg"
        return _archivo(
            archivo.archivo,
            content_type=archivo.mime,
            nombre=f"notificacion-{archivo.orden}.{extension}",
        )
