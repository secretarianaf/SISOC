"""Cola de revisión de identidad para React (C02.01 y C02.02; G1 v1).

``GET /api/web/ciudadanos/revision/?estado=&page=`` lo sirve el core y corre
``ColaRevisionView`` con su ``dispatch``: permiso ``ciudadanos.revision_identidad`` (403) y,
si la página pedida no existe, el 404 del ``ListView``. Proyecta lo que imprime
``cola_revision.html``. «Revisado» reutiliza ``POST /api/web/ciudadanos/<pk>/marcar-revisado/``
y «Descartar» corre la vista nativa ``descartar_revision`` en
``POST /api/web/ciudadanos/<pk>/descartar-revision/``: escriben lo nativo, dejan su mensaje
en cola y devuelven la redirección (``next``) como ``{"ok": true, "redirect": ...}``.
"""

from django.http import Http404
from django.template.defaultfilters import truncatechars
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from ciudadanos.views import ColaRevisionView, descartar_revision
from ciudadanos.web_ficha import pending_messages
from ciudadanos.web_gestion_despacho import VistaNativaWebView
from core.pagination import build_compact_page_range

VACIO = "-"
SIN_DNI = "SIN_DNI"
NO_VALIDADO = "DNI_NO_VALIDADO_RENAPER"


def _motivo(ciudadano):
    """Motivo y descripción como los imprime el template según el tipo de registro."""
    if ciudadano.tipo_registro_identidad == SIN_DNI:
        texto = ciudadano.get_motivo_sin_dni_display()
        descripcion = ciudadano.motivo_sin_dni_descripcion
    elif ciudadano.tipo_registro_identidad == NO_VALIDADO:
        texto = ciudadano.get_motivo_no_validacion_renaper_display()
        descripcion = ciudadano.motivo_no_validacion_descripcion
    else:
        return {"texto": VACIO, "descripcion": None}
    return {
        "texto": texto or VACIO,
        "descripcion": truncatechars(descripcion, 60) if descripcion else None,
    }


def _fila(ciudadano):
    return {
        "id": ciudadano.pk,
        "nombre_texto": f"{ciudadano.apellido or VACIO}, {ciudadano.nombre or VACIO}",
        "identificador": ciudadano.identificador_interno or VACIO,
        "documento": str(ciudadano.documento) if ciudadano.documento else VACIO,
        "tipo_registro": ciudadano.tipo_registro_identidad,
        "motivo": _motivo(ciudadano),
        "provincia": str(ciudadano.provincia) if ciudadano.provincia else VACIO,
        "estado_revision": ciudadano.estado_revision_manual,
        "editar_url": reverse("ciudadanos_editar", args=[ciudadano.pk]),
    }


def _paginacion(contexto):
    pagina = contexto["page_obj"]
    paginada = bool(contexto["is_paginated"])
    return {
        "paginated": paginada,
        "number": pagina.number,
        "previous": pagina.previous_page_number() if pagina.has_previous() else None,
        "next": pagina.next_page_number() if pagina.has_next() else None,
        "range": [
            "..." if numero in ("...", "…") else numero
            for numero in build_compact_page_range(pagina)
        ],
        "count": pagina.paginator.count if paginada else None,
    }


def _cola(contexto, request):
    return {
        "total_pendientes": contexto["total_pendientes"],
        "total_filtrado": contexto["total_filtrado"],
        "estado": contexto["estado_filtro"],
        "estados": [
            {"value": valor, "label": str(etiqueta)}
            for valor, etiqueta in contexto["filtros_estado"]
        ],
        "filas": [_fila(ciudadano) for ciudadano in contexto["ciudadanos"]],
        "paginacion": _paginacion(contexto),
        "cola_url": reverse("ciudadanos_cola_revision"),
        "messages": pending_messages(request),
    }


class CiudadanoColaRevisionWebView(VistaNativaWebView):
    """``GET /api/web/ciudadanos/revision/``."""

    http_method_names = ["get"]
    vista_nativa = ColaRevisionView

    def get(self, request):
        respuesta = self.despachar(request)
        return Response(_cola(respuesta.context_data, request))


class CiudadanoDescartarRevisionWebView(VistaNativaWebView):
    """``POST .../<pk>/descartar-revision/``: corre la vista nativa ``descartar_revision``.

    Conserva su permiso (``ciudadanos.revision_identidad``, 403 también para un id
    inexistente), su 404, la escritura y su mensaje en cola.
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        try:
            # pylint: disable-next=protected-access
            respuesta = descartar_revision(request._request, pk=pk)
        except Http404 as exc:
            raise NotFound() from exc
        return Response({"ok": True, "redirect": respuesta["Location"]})
