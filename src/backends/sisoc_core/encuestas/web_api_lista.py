"""Survey list and its row actions for React (E04, G1 v1).

``GET /api/web/encuestas/lista/?filters=&page=`` runs ``EncuestaListView`` (permission
``encuestas.view_encuesta`` or ``encuestas.ver_resultados``, as ``encuestas/urls.py``) and projects the
context of ``encuesta_list.html`` plus the search bar it includes. The row actions run the native views:
``POST .../<pk>/publicar/`` (``solicitar_publicacion``) and ``POST .../rondas/<pk>/cerrar/``
(``cerrar_ronda`` with ``manual=True``); both answer the common ``{ok, redirect, messages}`` contract.
"""

from django.http import HttpResponseRedirect
from django.template.defaultfilters import capfirst
from django.template.defaultfilters import date as date_filter
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.timezone import localtime
from rest_framework.response import Response

from core.pagination import build_compact_page_range
from encuestas.views import EncuestaListView, EncuestaPublicarView, RondaCerrarView
from encuestas.web_transport_encuestas import EncuestaNativeWebView, pending_messages

VER = ["encuestas.view_encuesta", "encuestas.ver_resultados"]


def _fecha(value):
    return date_filter(localtime(value), "d/m/Y") if value else ""


def _query_without_page(request):
    """Prefix of the ``components/pagination.html`` links (``busqueda`` dropped)."""
    return "".join(
        f"{urlencode({clave: valor})}&"
        for clave, valor in request.GET.items()
        if clave not in ("page", "busqueda")
    )


def _fila(encuesta):
    return {
        "id": encuesta.pk,
        "titulo": encuesta.titulo,
        "version": encuesta.version,
        "fecha_creacion": _fecha(encuesta.fecha_creacion),
        "estado": encuesta.estado,
        "estado_label": encuesta.get_estado_display(),
        "tiene_motivo_rechazo": bool(encuesta.motivo_rechazo),
        "modalidad": capfirst(encuesta.modalidad),
        "es_anonima": bool(encuesta.es_anonima),
        "creador": str(encuesta.usuario_creador),
    }


def proyectar_lista(context, request):
    """Context of ``encuesta_list.html`` and its ``components/search_bar.html``."""
    page = context["page_obj"]
    return {
        "filters_config": context["filters_config"],
        "favorites": {
            "section": "",
            "url": reverse("filtros_favoritos"),
            "detail_url_template": reverse("detalle_filtro_favorito", kwargs={"pk": 0}),
        },
        "urls": {
            "list": reverse("encuestas_listar"),
            "add": reverse("encuestas_crear"),
            "importar": reverse("encuestas_importar"),
        },
        "puede_gestionar": bool(context["puede_gestionar"]),
        "puede_aprobar": bool(context["puede_aprobar"]),
        "puede_editar": bool(context["puede_editar"]),
        "puede_ver_resultados": bool(context["puede_ver_resultados"]),
        "pendientes_aprobacion": context["pendientes_aprobacion"],
        "pendientes_url": context["pendientes_url"],
        "results": [_fila(encuesta) for encuesta in context["encuestas"]],
        "page": {
            "is_paginated": context["is_paginated"],
            "number": page.number,
            "count": page.paginator.count,
            "previous": page.previous_page_number() if page.has_previous() else None,
            "next": page.next_page_number() if page.has_next() else None,
            "range": [
                "…" if numero in ("...", "…") else numero
                for numero in build_compact_page_range(page)
            ],
            "query_without_page": _query_without_page(request),
        },
        "messages": pending_messages(request),
    }


class ListaWebView(EncuestaNativeWebView):
    permission_codes = VER
    native_view = EncuestaListView
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        # pylint: disable-next=protected-access
        django_request = request._request
        view = EncuestaListView()
        view.setup(django_request)
        # ``get`` converts the legacy ``busqueda``/``estado`` links into a ``filters`` redirect.
        response = view.get(django_request)
        if isinstance(response, HttpResponseRedirect):
            return Response({"redirect": response["Location"]})
        return Response(proyectar_lista(response.context_data, django_request))


class PublicarWebView(EncuestaNativeWebView):
    permission_codes = ["encuestas.change_encuesta"]
    native_view = EncuestaPublicarView
    http_method_names = ["post", "options"]

    def post(self, request, pk):
        return self.redirect_result(
            request, self.run_native(request, pk=pk), consume=False
        )


class RondaCerrarWebView(EncuestaNativeWebView):
    permission_codes = ["encuestas.change_rondaencuesta"]
    native_view = RondaCerrarView
    http_method_names = ["post", "options"]

    def post(self, request, pk):
        return self.redirect_result(
            request, self.run_native(request, pk=pk), consume=False
        )
