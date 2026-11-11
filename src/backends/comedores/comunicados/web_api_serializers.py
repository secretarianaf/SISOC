"""JSON projection of the native comunicados pages for the React web API (G1 v1).

These are not the PWA serializers (``comunicados.serializers``): they project
the context of the native views exactly as the templates print it. Dates use
the template filter ``date:"d/m/Y H:i"`` (local time) and the card summary uses
``truncatewords:50``, so React never formats values.
"""

from django.contrib import messages
from django.template.defaultfilters import date as date_filter
from django.template.defaultfilters import truncatewords, urlencode
from django.urls import reverse
from django.utils.timezone import localtime

from core.pagination import build_compact_page_range

FECHA_HORA = "d/m/Y H:i"
MESSAGE_LEVELS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}


def fecha_hora(valor):
    """``{{ valor|date:"d/m/Y H:i" }}`` (the template renders it in local time)."""
    return date_filter(localtime(valor), FECHA_HORA) if valor else ""


def nombre_usuario(usuario):
    """``get_full_name|default:username`` of the templates."""
    if usuario is None:
        return ""
    return usuario.get_full_name() or usuario.username


def pending_messages(request):
    """Consume queued Django messages exactly as the native page would."""
    return [
        {"message": str(m), "level": MESSAGE_LEVELS.get(m.level, "info")}
        for m in messages.get_messages(request)
    ]


def _query_without_page(request):
    """Prefix of ``components/pagination.html`` links (``page`` and ``busqueda`` dropped)."""
    return "".join(
        f"{clave}={urlencode(valor)}&"
        for clave, valor in request.GET.items()
        if clave not in ("page", "busqueda")
    )


def pagina(context, request):
    """``page_obj`` and ``is_paginated`` of a native ``ListView`` context."""
    page = context["page_obj"]
    return {
        "is_paginated": context["is_paginated"],
        "number": page.number,
        "num_pages": page.paginator.num_pages,
        "count": page.paginator.count,
        "previous": page.previous_page_number() if page.has_previous() else None,
        "next": page.next_page_number() if page.has_next() else None,
        "range": [
            "…" if numero in ("...", "…") else numero
            for numero in build_compact_page_range(page)
        ],
        "query_without_page": _query_without_page(request),
    }


def tarjeta_publicada(comunicado):
    """One card of ``comunicado_list.html``."""
    return {
        "id": comunicado.pk,
        "titulo": comunicado.titulo,
        "cuerpo_resumen": truncatewords(comunicado.cuerpo, 50),
        "destacado": comunicado.destacado,
        "fecha_publicacion": fecha_hora(comunicado.fecha_publicacion),
        "creador": nombre_usuario(comunicado.usuario_creador),
        "adjuntos_count": comunicado.adjuntos_count,
        "detail_url": reverse("comunicados_ver", args=[comunicado.pk]),
    }


def detalle(comunicado, context):
    """``comunicado_detail.html``: header, metadata, body and attachments."""
    return {
        "id": comunicado.pk,
        "titulo": comunicado.titulo,
        "cuerpo": comunicado.cuerpo,
        "estado": comunicado.estado,
        "estado_label": comunicado.get_estado_display(),
        "destacado": comunicado.destacado,
        "fecha_publicacion": fecha_hora(comunicado.fecha_publicacion),
        "fecha_vencimiento": fecha_hora(comunicado.fecha_vencimiento),
        "esta_vencido": comunicado.esta_vencido,
        "creador": nombre_usuario(comunicado.usuario_creador),
        "adjuntos": [
            {
                "id": adjunto.pk,
                "nombre_original": adjunto.nombre_original,
                "url": adjunto.archivo.url,
            }
            for adjunto in comunicado.adjuntos.all()
        ],
        "can_manage": context["can_manage"],
        "permisos": {
            "editar": context["can_edit"],
            "publicar": context["can_publish"],
            "archivar": context["can_archive"],
            "eliminar": context["can_delete"],
        },
    }
