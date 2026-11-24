"""Canonical React entry for the Celiaquía Pagos list and detail screens.

The JSON projections reuse the native querysets and lookups. These URLs carry
no permission decorator (pre-existing); the wrapper adds or removes no guard.
The respuesta upload is a regular multipart POST that the native view handles
and answers with a redirect; its feedback arrives through Django messages.
"""

from django.contrib.messages import get_messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone

from celiaquia.canonical_shell import canonical_screen
from celiaquia.forms import PagoRespuestaUploadForm
from celiaquia.models import PagoExpediente
from celiaquia.views.pago import PagoExpedienteListView, PagoExpedienteDetailView

_native_list = PagoExpedienteListView.as_view()
_native_detail = PagoExpedienteDetailView.as_view()


def pending_messages(request):
    """Consume pending Django messages, as the native base template does."""
    return [
        {"level": message.level_tag, "text": str(message)}
        for message in get_messages(request)
    ]


def _provincia(provincia):
    return {"id": provincia.id, "nombre": str(provincia)}


def _totals(pago):
    return {
        "candidatos": pago.total_candidatos,
        "validados": pago.total_validados,
        "excluidos": pago.total_excluidos,
    }


def _list_projection(request, *args, **kwargs):
    context = _native_list(request, *args, **kwargs).context_data
    provincia = context["provincia"]
    rows = [
        {
            "id": pago.id,
            "periodo": pago.periodo,
            "estado": pago.estado,
            **_totals(pago),
            "creado": timezone.localtime(pago.creado_en).strftime("%Y-%m-%d"),
            "url": reverse("pago_expediente_detail", args=[pago.id]),
        }
        for pago in context["pagos"]
    ]
    return JsonResponse(
        {
            "version": 1,
            "provincia": _provincia(provincia),
            "rows": rows,
            "urls": {
                "volver": reverse("cupo_provincia_detail", args=[provincia.id]),
                "crear": reverse("pago_expediente_create", args=[provincia.id]),
            },
            "messages": pending_messages(request),
        }
    )


def _detail_projection(request, pago_id):
    # Same lookup as PagoExpedienteDetailView.get.
    pago = get_object_or_404(PagoExpediente, pk=pago_id)
    field = PagoRespuestaUploadForm().fields["archivo"]
    return JsonResponse(
        {
            "version": 1,
            "pago": {
                "id": pago.id,
                "provincia": _provincia(pago.provincia),
                "periodo": pago.periodo,
                "estado": pago.estado,
                **_totals(pago),
            },
            "urls": {
                "volver": reverse("cupo_provincia_detail", args=[pago.provincia.id]),
                "archivo_envio": (
                    reverse("pago_expediente_export", args=[pago.id])
                    if pago.archivo_envio
                    else None
                ),
                "exportar_nomina": reverse("pago_nomina_export_actual", args=[pago.id]),
            },
            "upload": {
                "action": reverse("pago_expediente_detail", args=[pago.id]),
                "field": "archivo",
                "label": str(field.label),
                "required": field.required,
            },
            "nomina": [
                {
                    "documento": row.documento,
                    "nombre": row.nombre,
                    "apellido": row.apellido,
                    "estado": row.estado,
                    "observacion": row.observacion,
                }
                for row in pago.nomina.all()
            ],
            "messages": pending_messages(request),
        }
    )


pagos = canonical_screen(_native_list, "pagos", _list_projection)
pago_detalle = canonical_screen(_native_detail, "pago-detalle", _detail_projection)
