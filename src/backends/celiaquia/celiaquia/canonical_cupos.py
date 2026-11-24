"""Private projections of the native Cupos screens for their canonical URLs.

Both projections reuse the native data (``CupoService.filas_dashboard`` and
``contexto_provincia``) and expose only what the native templates render to
anyone who passes the URL guard (``celiaquia.view_cupo_dashboard``).
"""

from django.contrib.messages import get_messages
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone

from core.models import Provincia
from celiaquia.canonical_shell import canonical_screen
from celiaquia.forms import CupoBajaLegajoForm, CupoSuspenderLegajoForm
from celiaquia.services.cupo_service import CupoService
from celiaquia.views.cupo import (
    CupoDashboardView,
    CupoProvinciaDetailView,
    contexto_provincia,
)


def _messages(request):
    # Iterating marks the pending messages as consumed, like the native layout.
    return [
        {"level": message.level_tag, "text": str(message)}
        for message in get_messages(request)
    ]


def _provincia(provincia):
    return {"id": provincia.pk, "nombre": str(provincia)}


def _text(value):
    return "" if value is None else str(value)


def _legajo(legajo):
    row = _person_state(legajo)
    # The native template prints ``expediente.codigo``, which Expediente
    # does not define, so the column renders empty. Keep that value.
    row["expediente"] = _text(getattr(legajo.expediente, "codigo", None))
    return row


def _person_state(legajo):
    ciudadano = legajo.ciudadano
    return {
        "id": legajo.pk,
        "documento": _text(ciudadano.documento),
        "nombre": _text(ciudadano.nombre),
        "apellido": _text(ciudadano.apellido),
        "revision_tecnico": _text(legajo.revision_tecnico),
        "resultado_sintys": _text(legajo.resultado_sintys),
        "estado_cupo": _text(legajo.estado_cupo),
        "es_titular_activo": bool(legajo.es_titular_activo),
    }


def _with_actions(legajo, provincia_id):
    row = _legajo(legajo)
    args = [provincia_id, legajo.pk]
    toggle = (
        ("suspender", "cupo_legajo_suspender")
        if legajo.es_titular_activo
        else ("reactivar", "cupo_legajo_reactivar")
    )
    row["actions"] = [
        {"kind": toggle[0], "url": reverse(toggle[1], args=args)},
        {"kind": "baja", "url": reverse("cupo_legajo_baja", args=args)},
    ]
    return row


def _movimiento(movimiento):
    usuario = movimiento.usuario
    legajo = movimiento.legajo
    return {
        "id": movimiento.pk,
        "fecha": timezone.localtime(movimiento.creado_en).strftime("%d/%m/%Y %H:%M"),
        "tipo": movimiento.tipo,
        "delta": movimiento.delta,
        "motivo": movimiento.motivo,
        "usuario": (usuario.get_full_name() or usuario.username) if usuario else "",
        "expediente": _text(getattr(movimiento.expediente, "codigo", None)),
        "legajo": _person_state(legajo) if legajo else None,
    }


def _form_field(form):
    field = form.fields["motivo"]
    return {"name": "motivo", "label": str(field.label), "required": field.required}


def dashboard_projection(request):
    rows = [
        {
            "provincia": _provincia(row["provincia"]),
            "total_asignado": row["total_asignado"],
            "usados": row["usados"],
            "disponibles": row["disponibles"],
            "fuera": row["fuera"],
            "url": reverse("cupo_provincia_detail", args=[row["provincia"].pk]),
        }
        for row in CupoService.filas_dashboard()
    ]
    return JsonResponse(
        {
            "version": 1,
            "rows": rows,
            "urls": {"expedientes": reverse("expediente_list")},
            "messages": _messages(request),
        }
    )


def provincia_projection(request, provincia_id):
    provincia = get_object_or_404(Provincia, pk=provincia_id)
    data = contexto_provincia(provincia)
    pk = provincia.pk
    return JsonResponse(
        {
            "version": 1,
            "provincia": _provincia(provincia),
            "metrics": data["metrics"],
            "ocupados": [_with_actions(leg, pk) for leg in data["ocupados"]],
            "suspendidos": [_with_actions(leg, pk) for leg in data["suspendidos"]],
            "lista_espera": [
                {**_legajo(leg), "actions": []} for leg in data["lista_espera"]
            ],
            "movimientos": [_movimiento(m) for m in data["movimientos"]],
            "forms": {
                "baja": _form_field(CupoBajaLegajoForm()),
                "suspender": _form_field(CupoSuspenderLegajoForm()),
            },
            "urls": {
                "dashboard": reverse("cupo_dashboard"),
                "config": reverse("cupo_provincia_detail", args=[pk]),
                "pagos": reverse("pago_expediente_list", args=[pk]),
                "crear_pago": reverse("pago_expediente_create", args=[pk]),
            },
            # The native page embeds {% csrf_token %} in its regular POST form.
            "csrf_token": get_token(request),
            "messages": _messages(request),
        }
    )


cupos = canonical_screen(CupoDashboardView.as_view(), "cupos", dashboard_projection)
cupo_provincia = canonical_screen(
    CupoProvinciaDetailView.as_view(), "cupo-provincia", provincia_projection
)
