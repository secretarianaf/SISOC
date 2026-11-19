"""Listado de ciudadanos para React (``/ciudadanos/listar``; G1 v1).

``GET /api/web/ciudadanos/listar/`` lo sirve el core y corre ``CiudadanosListView`` con su
``dispatch``: permiso ``ciudadanos.view_ciudadano`` (403), filtros del formulario propio, filtros
combinables, orden por ``pk`` y páginas de 25 sin ``COUNT``. Proyecta lo que imprime
``ciudadano_list.html`` y ``components/search_bar.html``; solo lee. La exportación CSV sigue siendo
la descarga nativa (``ciudadanos_exportar``).
"""

from urllib.parse import quote

from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.formats import localize
from rest_framework.response import Response

from ciudadanos.views import CiudadanosListView
from ciudadanos.web_ficha import pending_messages
from ciudadanos.web_gestion_despacho import VistaNativaWebView
from core.pagination import build_compact_page_range
from core.templatetags.custom_filters import has_any_perm

PERMISO_EXPORTAR = "auth.role_exportar_a_csv"
VACIO = "-"


def _imprimir(valor):
    """``{{ valor }}``: localizado y, sin valor, el texto que imprime Django (``None``)."""
    return force_str(localize(valor))


def _celda(valor, sort_sin_default=False):
    """Texto de ``{{ valor|default:"-" }}`` y valor ``data-*`` con el que ordena ``listSort.js``."""
    impreso = _imprimir(valor) if valor else ""
    # Apellido y nombre imprimen el ``data-*`` sin ``default`` (``None`` incluido).
    return {
        "text": impreso or VACIO,
        "sort": _imprimir(valor) if sort_sin_default else impreso,
    }


def _fila(ciudadano):
    return {
        "id": ciudadano.pk,
        "cells": [
            _celda(ciudadano.apellido, sort_sin_default=True),
            _celda(ciudadano.nombre, sort_sin_default=True),
            _celda(ciudadano.documento),
            _celda(ciudadano.sexo),
            _celda(ciudadano.provincia),
        ],
        "tipo_registro": ciudadano.tipo_registro_identidad,
        "requiere_revision": bool(ciudadano.requiere_revision_manual),
        "ver_url": reverse("ciudadanos_ver", args=[ciudadano.pk]),
    }


def _query_prefix(request):
    """Prefijo de los enlaces de ``components/pagination.html`` (sin ``page``).

    El listado no define ``query``, así que ``busqueda`` tampoco se arrastra.
    """
    return "".join(
        f"{clave}={quote(valor, safe='/')}&"
        for clave, valor in request.GET.items()
        if clave not in ("page", "busqueda")
    )


def _valor(formulario, nombre):
    valor = formulario[nombre].value()
    return "" if valor is None else str(valor)


def _campo(formulario, nombre):
    campo = formulario[nombre]
    etiqueta = force_str(campo.label)
    if etiqueta and etiqueta[-1] not in ":?.!":
        etiqueta += formulario.label_suffix
    return {
        "label": etiqueta,
        "value": _valor(formulario, nombre),
        "options": [
            {"value": str(valor_opcion), "label": str(texto)}
            for valor_opcion, texto in campo.field.choices
        ],
    }


def _paginacion(contexto):
    pagina = contexto["page_obj"]
    return {
        "is_paginated": bool(contexto["is_paginated"]),
        "number": pagina.number,
        "previous": pagina.previous_page_number() if pagina.has_previous() else None,
        "next": pagina.next_page_number() if pagina.has_next() else None,
        "range": [
            "..." if numero in ("...", "…") else numero
            for numero in (
                contexto.get("page_range") or build_compact_page_range(pagina)
            )
        ],
    }


def _listado(contexto, request):
    formulario = contexto["filter_form"]
    return {
        "filters_config": contexto["filters_config"],
        "favorites": {
            "section": "",
            "url": reverse("filtros_favoritos"),
            "detail_url_template": reverse("detalle_filtro_favorito", kwargs={"pk": 0}),
        },
        "filtros": {
            "q": _valor(formulario, "q"),
            "tipo_registro": _campo(formulario, "tipo_registro"),
            "estado_revision": _campo(formulario, "estado_revision"),
            "filters": request.GET.get("filters", ""),
        },
        "results": [_fila(ciudadano) for ciudadano in contexto["object_list"]],
        "page": {**_paginacion(contexto), "query_prefix": _query_prefix(request)},
        "can_export": bool(
            request.user.is_superuser or has_any_perm(request.user, PERMISO_EXPORTAR)
        ),
        "additional_buttons": [
            {
                "label": str(boton.get("label", "")),
                "url": str(boton.get("url", "")),
                "class": str(boton.get("class", "btn btn-primary btn-lg")),
                "title": str(boton.get("title", "")),
            }
            for boton in contexto["additional_buttons"]
        ],
        "urls": {
            "list": contexto["filters_action"],
            "add": reverse("ciudadanos_crear"),
            "export": reverse("ciudadanos_exportar"),
        },
        "messages": pending_messages(request),
    }


class CiudadanoListadoWebView(VistaNativaWebView):
    """``GET /api/web/ciudadanos/listar/``."""

    http_method_names = ["get"]
    vista_nativa = CiudadanosListView

    def get(self, request):
        respuesta = self.despachar(request)
        # pylint: disable-next=protected-access
        return Response(_listado(respuesta.context_data, request._request))
