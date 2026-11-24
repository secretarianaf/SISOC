"""Web API (G1 v1) of the organization documents (O02).

The history, upload, additional-document, state, expiry and GDE operations run
the native views themselves (``views.py``): the same dupla scope, capacity
rules, validations, persisted effects, GDE replication to the admisiones and
Django error texts. The native JSON answer carries a rendered HTML row; this
API discards it and returns the row as data (``fila``) instead. Access is
today's: any of ``ORGANIZACION_DOCUMENTACION_PERMS`` (see
``docs/registro/decisiones/2026-11-10-2785-brechas-acceso-conservadas.md``).
Files are served by their direct media URL, as today. The legajo table
(``legajo/documentacion.html``) is delivered as a section
(``web_api_secciones``).
"""

import json

from django.shortcuts import get_object_or_404
from django.template.defaultfilters import date as formato_fecha
from django.urls import reverse
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.web_gate import WebGatePermission
from gestion_organizaciones import views
from gestion_organizaciones.web_api import OrganizacionListAccess
from gestion_organizaciones.web_api_secciones import seccion
from organizaciones.models import (
    ArchivoOrganizacion,
    DocumentacionOrganizacion,
    Organizacion,
)


def _fila(row, organizacion, puede_validar, puede_enviar):
    """One table row of ``documentacion_organizacion_row.html`` as data."""
    documentacion, archivo = row["documentacion"], row["archivo"]
    personalizado = bool(row["es_personalizado"])
    vencimiento = None
    if archivo and archivo.fecha_vencimiento:
        vencimiento = {
            "date": formato_fecha(archivo.fecha_vencimiento, "d/m/Y"),
            "iso": archivo.fecha_vencimiento.isoformat(),
            "status": (
                "vencido"
                if archivo.esta_vencido
                else "por_vencer" if archivo.esta_por_vencer else "vigente"
            ),
        }
    return {
        "row_id": f"custom-{archivo.pk}" if personalizado else documentacion.pk,
        "name": archivo.nombre_personalizado if personalizado else documentacion.nombre,
        "mandatory": bool(documentacion and documentacion.obligatorio),
        "custom": personalizado,
        "document_id": documentacion.pk if documentacion else None,
        "history_url": (
            reverse(
                "organizacion_documento_historial",
                args=[organizacion.pk, documentacion.pk],
            )
            if archivo and not personalizado
            else None
        ),
        "can_validate": puede_validar,
        "can_send": puede_enviar,
        "file": archivo
        and {
            "id": archivo.pk,
            "state": archivo.estado,
            "observations": archivo.observaciones or "",
            "url": archivo.archivo.url,
            "expiry": vencimiento,
            "gde": archivo.numero_gde or "",
        },
    }


def _capacidades(user, organizacion):
    return (
        views._puede_validar_documentacion_organizacion(  # pylint: disable=protected-access
            user, organizacion
        ),
        views._puede_enviar_documentacion_organizacion(  # pylint: disable=protected-access
            user, organizacion
        ),
    )


@seccion("organizaciones/partials/legajo/documentacion.html")
def seccion_documentacion(contexto):
    """``legajo/documentacion.html``: the catalog and additional rows."""
    organizacion = contexto["organizacion"]
    validar = bool(contexto.get("puede_validar_documentacion_organizacion"))
    enviar = bool(contexto.get("puede_enviar_documentacion_organizacion"))
    return {
        "kind": "documentos",
        "organization_id": organizacion.pk,
        "category": contexto.get("documentacion_organizacion_categoria")
        or "Tipo documental",
        "can_validate": validar,
        "can_send": enviar,
        "rows": [
            _fila(row, organizacion, validar, enviar)
            for row in contexto.get("documentacion_organizacion") or []
        ],
    }


def _fila_de_archivo(request, archivo):
    """The row ``_render_fila_documentacion_y_row_id`` would render for ``archivo``."""
    organizacion = archivo.organizacion
    if archivo.documentacion_id:
        row = views._build_documentacion_organizacion_row(  # pylint: disable=W0212
            organizacion, archivo.documentacion
        )
        row["es_personalizado"] = False
    else:
        row = {
            "documentacion": None,
            "archivo": archivo,
            "historial": [],
            "es_personalizado": True,
        }
    return _fila(row, organizacion, *_capacidades(request.user, organizacion))


class _DocumentosView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, OrganizacionListAccess]
    renderer_classes = [JSONRenderer]


class HistorialWebView(_DocumentosView):
    """``GET .../<id>/documentacion/<doc_id>/historial/``: the native queryset."""

    http_method_names = ["get", "head"]

    def get(self, request, pk, documentacion_id):
        organizacion = get_object_or_404(
            views._filtrar_organizaciones_por_dupla(  # pylint: disable=W0212
                Organizacion.objects.all(), request.user
            ),
            pk=pk,
        )
        documentacion = get_object_or_404(
            DocumentacionOrganizacion, pk=documentacion_id
        )
        archivos = ArchivoOrganizacion.objects.filter(
            organizacion=organizacion, documentacion=documentacion
        ).order_by("-creado", "-id")
        return Response(
            {
                "organization": {"id": organizacion.pk, "name": organizacion.nombre},
                "document": {"id": documentacion.pk, "name": documentacion.nombre},
                "files": [
                    {
                        "id": archivo.pk,
                        "created": formato_fecha(
                            timezone.localtime(archivo.creado), "d/m/Y H:i"
                        ),
                        "state": archivo.estado,
                        "expiry": (
                            formato_fecha(archivo.fecha_vencimiento, "d/m/Y")
                            if archivo.fecha_vencimiento
                            else "-"
                        ),
                        "observations": archivo.observaciones or "-",
                        "url": archivo.archivo.url,
                    }
                    for archivo in archivos
                ],
                "urls": {
                    "list": reverse("organizaciones"),
                    "legajo": reverse("organizacion_detalle", args=[organizacion.pk]),
                },
            }
        )


class _OperacionWebView(_DocumentosView):
    """POST that runs a native JSON view and returns its row as data."""

    http_method_names = ["post"]
    nativa = None

    def post(self, request, **kwargs):
        respuesta = self.nativa(  # pylint: disable=not-callable
            request._request, **kwargs  # pylint: disable=protected-access
        )
        datos = json.loads(respuesta.content)
        if respuesta.status_code != 200 or not datos.get("success"):
            return Response(
                {"error": datos.get("error", "")}, status=respuesta.status_code
            )
        return Response({"fila": self.fila(request, datos, kwargs)})

    @staticmethod
    def fila(request, datos, kwargs):
        raise NotImplementedError


class _SobreArchivo(_OperacionWebView):
    @staticmethod
    def fila(request, datos, kwargs):
        archivo = ArchivoOrganizacion.objects.select_related(
            "organizacion", "documentacion"
        ).get(pk=kwargs["archivo_id"])
        return _fila_de_archivo(request, archivo)


class EstadoWebView(_SobreArchivo):
    """``POST .../documentacion/<archivo_id>/estado/``."""

    nativa = staticmethod(views.actualizar_estado_documento_organizacion)


class VencimientoWebView(_SobreArchivo):
    """``POST .../documentacion/<archivo_id>/vencimiento/``."""

    nativa = staticmethod(views.actualizar_vencimiento_documento_organizacion)


class NumeroGdeWebView(_SobreArchivo):
    """``POST .../documentacion/<archivo_id>/numero-gde/`` (replicates to admisiones)."""

    nativa = staticmethod(views.actualizar_numero_gde_documento_organizacion)


class SubirWebView(_OperacionWebView):
    """``POST .../<id>/documentacion/<doc_id>/subir/`` (multipart)."""

    nativa = staticmethod(views.subir_documento_organizacion)

    def post(self, request, pk, documentacion_id):  # pylint: disable=arguments-differ
        return super().post(
            request, organizacion_id=pk, documentacion_id=documentacion_id
        )

    @staticmethod
    def fila(request, datos, kwargs):
        organizacion = Organizacion.objects.get(pk=kwargs["organizacion_id"])
        documentacion = DocumentacionOrganizacion.objects.get(
            pk=kwargs["documentacion_id"]
        )
        row = views._build_documentacion_organizacion_row(  # pylint: disable=W0212
            organizacion, documentacion
        )
        row["es_personalizado"] = False
        return _fila(row, organizacion, *_capacidades(request.user, organizacion))


class PersonalizadaWebView(_OperacionWebView):
    """``POST .../<id>/documentacion/personalizada/`` (multipart)."""

    nativa = staticmethod(views.agregar_documento_personalizado_organizacion)

    def post(self, request, pk):  # pylint: disable=arguments-differ
        return super().post(request, organizacion_id=pk)

    @staticmethod
    def fila(request, datos, kwargs):
        archivo = ArchivoOrganizacion.objects.select_related(
            "organizacion", "documentacion"
        ).get(pk=datos["archivo_id"])
        return _fila_de_archivo(request, archivo)
