"""JSON projection of the native comunicados pages for the React web API (G1 v1).

These are not the PWA serializers (``comunicados.serializers``): they project
the context of the native views exactly as the templates print it. Dates use
the template filter ``date:"d/m/Y H:i"`` (local time) and the card summary uses
``truncatewords:50``, so React never formats values.
"""

from django import forms
from django.contrib import messages
from django.template.defaultfilters import date as date_filter
from django.template.defaultfilters import truncatewords, urlencode
from django.urls import reverse
from django.utils.timezone import localtime

from comunicados.forms import ALLOWED_ADJUNTO_EXTENSIONS, MAX_ADJUNTO_SIZE_BYTES
from core.pagination import build_compact_page_range

FECHA_HORA = "d/m/Y H:i"
MESSAGE_LEVELS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}


def fecha_hora(valor, formato=FECHA_HORA):
    """``{{ valor|date:formato }}`` (the template renders it in local time)."""
    return date_filter(localtime(valor), formato) if valor else ""


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
        "fecha_creacion": fecha_hora(comunicado.fecha_creacion),
        "modificado_por": nombre_usuario(comunicado.usuario_ultima_modificacion),
        "can_manage": context["can_manage"],
        "permisos": {
            "editar": context["can_edit"],
            "publicar": context["can_publish"],
            "archivar": context["can_archive"],
            "eliminar": context["can_delete"],
        },
    }


def fila_gestion(comunicado, context):
    """One row of ``comunicado_gestion_list.html``; ``acciones`` keeps its conditions."""
    borrador = comunicado.estado == "borrador"
    publicado = comunicado.estado == "publicado"
    editar = borrador and context["can_edit"]
    return {
        "id": comunicado.pk,
        "titulo": comunicado.titulo,
        "titulo_corto": truncatewords(comunicado.titulo, 8),
        "tipo": comunicado.tipo,
        "estado": comunicado.estado,
        "esta_vencido": comunicado.esta_vencido,
        "destacado": comunicado.destacado,
        "fecha_creacion": fecha_hora(comunicado.fecha_creacion, "d/m/Y"),
        "fecha_publicacion": fecha_hora(comunicado.fecha_publicacion, "d/m/Y"),
        "creador": nombre_usuario(comunicado.usuario_creador),
        "acciones": {
            "editar": editar,
            "publicar": editar and context["can_publish"],
            "archivar": publicado and context["can_archive"],
            "destacado": publicado
            and comunicado.tipo != "externo"
            and context["can_toggle_destacado"],
        },
    }


def eliminar_confirmacion(comunicado):
    """``comunicado_confirm_delete.html``: what the confirmation prints."""
    return {
        "id": comunicado.pk,
        "titulo": comunicado.titulo,
        "fecha_creacion": fecha_hora(comunicado.fecha_creacion),
        "creador": nombre_usuario(comunicado.usuario_creador),
        "adjuntos_count": comunicado.adjuntos.count(),
    }


FORM_FIELDS = (
    "tipo",
    "subtipo",
    "fecha_vencimiento",
    "destacado",
    "para_todos_comedores",
    "comedores",
    "organizaciones",
    "titulo",
    "cuerpo",
)
# Order of ``accept=".pdf,.jpg,.jpeg,.png"`` in the native template.
ACCEPT_ORDER = (".pdf", ".jpg", ".jpeg", ".png")
MANAGEMENT_FIELDS = ("TOTAL_FORMS", "INITIAL_FORMS", "MIN_NUM_FORMS", "MAX_NUM_FORMS")


def _valor(bound):
    """What ``{{ form.<field> }}`` renders as the control value."""
    valor, campo = bound.value(), bound.field
    if isinstance(campo, forms.ModelMultipleChoiceField):
        return [str(getattr(item, "pk", item)) for item in valor or []]
    if isinstance(campo.widget, forms.CheckboxInput):
        return bool(valor)
    return "" if valor is None else str(valor)


def _campo(bound):
    campo = bound.field
    datos = {
        "value": _valor(bound),
        "required": bool(
            campo.required and campo.widget.use_required_attribute(bound.initial)
        ),
        "hidden": campo.widget.is_hidden,
        "errors": [str(error) for error in bound.errors],
    }
    if isinstance(campo, forms.ChoiceField) and not isinstance(
        campo, forms.ModelMultipleChoiceField
    ):
        datos["choices"] = [
            {"value": str(valor), "label": str(etiqueta)}
            for valor, etiqueta in campo.choices
        ]
    if getattr(campo, "max_length", None):
        datos["max_length"] = campo.max_length
    return datos


def _adjunto_existente(adjunto_form):
    borrar = adjunto_form["DELETE"]
    return {
        "nombre_original": adjunto_form.instance.nombre_original,
        "url": adjunto_form.instance.archivo.url,
        "hidden": [
            {
                "name": oculto.html_name,
                "value": "" if oculto.value() is None else str(oculto.value()),
            }
            for oculto in adjunto_form.hidden_fields()
        ],
        "delete": {
            "name": borrar.html_name,
            "id": borrar.id_for_label,
            "checked": bool(borrar.value()),
        },
    }


def formulario(context):
    """``comunicado_form.html``: the bound form, its attachments formset and extras."""
    form, formset = context["form"], context["adjuntos_formset"]
    objeto = context.get("object") if context["is_edit"] else None
    gestion = formset.management_form
    return {
        "title": context["titulo_pagina"],
        "is_edit": context["is_edit"],
        "es_tecnico": context["es_tecnico"],
        "fields": {nombre: _campo(form[nombre]) for nombre in FORM_FIELDS},
        "formset": {
            "prefix": formset.prefix,
            "has_forms": bool(formset.forms),
            "management": {
                nombre: str(gestion[nombre].value()) for nombre in MANAGEMENT_FIELDS
            },
            "existing": [_adjunto_existente(f) for f in formset.forms if f.instance.pk],
        },
        "info": (
            {
                "estado": objeto.estado,
                "estado_label": objeto.get_estado_display(),
                "fecha_creacion": fecha_hora(objeto.fecha_creacion),
                "creador": nombre_usuario(objeto.usuario_creador),
            }
            if objeto
            else None
        ),
        "filters_config": context["destinatarios_filters_config"],
        "seleccionados": context["destinatarios_seleccionados"],
        "max_adjunto_bytes": MAX_ADJUNTO_SIZE_BYTES,
        "extensiones": sorted(ALLOWED_ADJUNTO_EXTENSIONS, key=ACCEPT_ORDER.index),
        "attachment_errors": [str(e) for e in form["archivos_adjuntos"].errors],
        "formset_errors": [dict(errores) for errores in formset.errors],
        "non_form_errors": [str(error) for error in formset.non_form_errors()],
    }
