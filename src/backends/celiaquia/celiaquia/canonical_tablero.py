"""Canonical React entry for the Celiaquía Tablero screen.

The JSON projection is the native view context: the same ``construir_tablero``
payload (aggregated, no personal data) and the same ``url_expediente`` rule
(only users with ``view_expediente`` get the link template). Filters apply in
the browser over this data, as in the native page. The URL decorator
(``view_tablero_celiaquia``) authorizes before this wrapper runs.
"""

from django.http import JsonResponse

from celiaquia.canonical_pagos import pending_messages
from celiaquia.canonical_shell import canonical_screen
from celiaquia.views.tablero import TableroCeliaquiaView

_native_tablero = TableroCeliaquiaView.as_view()


def _projection(request, *args, **kwargs):
    response = _native_tablero(request, *args, **kwargs)
    if response.status_code != 200:
        return response
    context = response.context_data
    return JsonResponse(
        {
            "version": 1,
            "datos": context["tablero_datos"],
            "url_expediente": context["url_expediente"],
            "messages": pending_messages(request),
        }
    )


tablero = canonical_screen(_native_tablero, "tablero", _projection)
