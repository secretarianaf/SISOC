"""Web API (G1 v1) of the CDF Informe Cabal screens (CDF01).

Same access chain as ``centrodefamilia.web_api``: G1 session and web
prerequisites, then ``centrodefamilia.view_centro`` (the same predicate as the
native ``permissions_any_required``). After that each endpoint runs the native
view's own ``get_context_data`` / ``get_object`` unchanged, so the history list
(10 per page, ``get_page`` tolerance), the file detail, the per-centre detail
(50 per page, missing centre or file 404) and the registro detail cannot drift
from the HTML pages; this module only projects those contexts to JSON.

The upload preview, the processing and the reprocess actions are native AJAX
endpoints (``informecabal/preview/``, ``informecabal/process/``,
``informecabal/reprocess/``): the React page posts to them exactly as the
native script does, so nothing is duplicated here. Read-only: GET/HEAD only.

``InformeCabalRegistroDetailView`` is a ``DetailView`` of ``CabalArchivo`` whose
template reads ``registro``, a variable the view never sets: the native page
renders empty values. The projection keeps that behaviour and exposes only what
the page really shows.
"""

from django.contrib import messages
from django.template.defaultfilters import date as date_filter
from django.template.defaultfilters import floatformat
from django.urls import reverse
from django.utils import timezone
from rest_framework.response import Response

from centrodefamilia.views.centro import InformeCabalArchivoPorCentroDetailView
from centrodefamilia.views.informecabal import (
    InformeCabalArchivoDetailView,
    InformeCabalListView,
    InformeCabalRegistroDetailView,
)
from centrodefamilia.web_api import CdfWebView, native_view, pending_messages, rendered


def _fecha_hora(value):
    return date_filter(timezone.localtime(value), "d/m/Y H:i")


def _fecha_orden(value):
    return date_filter(timezone.localtime(value), "Y-m-d H:i")


def _alerts(request):
    """The list template draws its own alerts (``alert-{{ tags }}``): consume them here."""
    django_request = request._request  # pylint: disable=protected-access
    return [
        {"message": str(item), "tags": item.tags}
        for item in messages.get_messages(django_request)
    ]


def _archivo(archivo):
    return {
        "id": archivo.pk,
        "nombre_original": archivo.nombre_original,
        "fecha_subida": _fecha_hora(archivo.fecha_subida),
        "fecha_orden": _fecha_orden(archivo.fecha_subida),
        "usuario": archivo.usuario.username,
        "total_filas": archivo.total_filas,
        "total_validas": archivo.total_validas,
        "total_invalidas": archivo.total_invalidas,
        "urls": {"detail": reverse("informecabal_archivo_detail", args=[archivo.pk])},
    }


def _neighbours(page):
    return {
        "has_previous": page.has_previous(),
        "has_next": page.has_next(),
        "previous_page": page.previous_page_number() if page.has_previous() else None,
        "next_page": page.next_page_number() if page.has_next() else None,
    }


class InformeCabalListWebView(CdfWebView):
    """``GET /api/web/cdf/informecabal/?page=``: the native history list."""

    def get(self, request):
        vista = native_view(InformeCabalListView, request)
        page = vista.get_context_data()["archivos"]
        return Response(
            {
                "page": page.number,
                **_neighbours(page),
                "results": [_archivo(archivo) for archivo in page],
                "alerts": _alerts(request),
                "urls": {
                    "list": reverse("informecabal_list"),
                    "preview": reverse("informecabal_preview"),
                    "process": reverse("informecabal_process"),
                    "reprocess": reverse("informecabal_reprocess_center"),
                },
                "messages": [],
            }
        )


def _pago_aceptado(registro):
    return not (registro.motivo_rechazo and registro.motivo_rechazo != "0")


def _registro(posicion, registro):
    return {
        "numero": posicion,
        "nro_comercio": rendered(registro.nro_comercio),
        "razon_social": rendered(registro.razon_social),
        "importe": rendered(registro.importe),
        "fecha_trx": date_filter(registro.fecha_trx, "d/m/Y"),
        "moneda_origen": rendered(registro.moneda_origen),
        "importe_pesos": rendered(registro.importe_pesos),
        "pago_aceptado": _pago_aceptado(registro),
        "impactado": bool(registro.centro_id),
    }


class InformeCabalArchivoWebView(CdfWebView):
    """``GET /api/web/cdf/informecabal/<pk>/``: file data and every processed row."""

    def get(self, request, pk):
        vista = native_view(InformeCabalArchivoDetailView, request, pk=pk)
        vista.object = vista.get_object()
        context = vista.get_context_data()
        archivo = context["archivo"]
        return Response(
            {
                "archivo": {
                    "id": archivo.pk,
                    "nombre_original": archivo.nombre_original,
                    "fecha_subida": _fecha_hora(archivo.fecha_subida),
                    "usuario": archivo.usuario.username,
                    "total_filas": archivo.total_filas,
                    "total_validas": archivo.total_validas,
                    "total_invalidas": archivo.total_invalidas,
                },
                "registros": [
                    _registro(posicion, registro)
                    for posicion, registro in enumerate(context["registros"], 1)
                ],
                "urls": {"list": reverse("informecabal_list")},
                "messages": pending_messages(request),
            }
        )


class InformeCabalRegistroWebView(CdfWebView):
    """``GET /api/web/cdf/informecabal/registro/<pk>/``: the native (empty) registro page."""

    def get(self, request, pk):
        vista = native_view(InformeCabalRegistroDetailView, request, pk=pk)
        vista.object = vista.get_object()
        vista.get_context_data()
        return Response({"messages": pending_messages(request)})


class InformeCabalPorCentroWebView(CdfWebView):
    """``GET /api/web/cdf/centros/<centro_id>/informecabal/<pk>/?page=``: rows of one centre."""

    def get(self, request, centro_id, pk):
        vista = native_view(
            InformeCabalArchivoPorCentroDetailView, request, centro_id=centro_id, pk=pk
        )
        vista.object = vista.get_object()
        context = vista.get_context_data()
        page = context["registros"]
        centro = context["centro"]
        return Response(
            {
                "centro": {"id": centro.pk, "nombre": centro.nombre},
                "count": page.paginator.count,
                "page": page.number,
                "num_pages": page.paginator.num_pages,
                **_neighbours(page),
                "results": [
                    {
                        "numero": posicion,
                        "nro_comercio": rendered(registro.nro_comercio),
                        "razon_social": rendered(registro.razon_social),
                        "importe": "$" + str(floatformat(registro.importe, 2)),
                        "fecha_trx": date_filter(registro.fecha_trx, "d/m/Y"),
                        "pago_aceptado": _pago_aceptado(registro),
                    }
                    for posicion, registro in enumerate(page, 1)
                ],
                "messages": pending_messages(request),
            }
        )
