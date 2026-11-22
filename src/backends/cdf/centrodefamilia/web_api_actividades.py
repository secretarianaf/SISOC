"""Web API (G1 v1) of the CDF activity page and its participant circuit (CDF-C).

Same access chain as ``centrodefamilia.web_api``: G1 session and web
prerequisites, then ``centrodefamilia.view_centro`` (``permissions_any_required``
predicate). Nothing else is added or removed (decision D1): the native views
only require login besides that URL guard, so an object that belongs to another
centre or activity is served exactly as the HTML page serves it.

Each endpoint runs the native view itself:

- ``ActividadCentroDetailView`` (the ficha: inscritos, lista de espera, costo
  total, ``promo_error`` and whether the actor may take attendance);
- ``ParticipanteActividadCreateView`` (GET: search by document and the
  citizen form; POST: ``post()`` with its enrolment, waitlist and exception
  branches);
- ``ParticipanteActividadDeleteView`` (``dar_de_baja`` and its automatic
  promotion) and ``ParticipanteActividadPromoverView`` (cupo check and the
  first participant by ``fecha_registro``).

The native ``post()`` queues its message and redirects. The API answers that
redirect as JSON (``url`` plus the queued message, which stays queued so the
native page shows it once on arrival); an invalid citizen form answers 400
with the bound values and errors. Nothing is retried: a repeated POST is a new
native request with the native consequences (for example another promotion).
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import formats, timezone
from rest_framework.response import Response

from centrodefamilia.models import ParticipanteActividad
from centrodefamilia.views.actividad import ActividadCentroDetailView
from centrodefamilia.views.participante import (
    ParticipanteActividadCreateView,
    ParticipanteActividadDeleteView,
    ParticipanteActividadPromoverView,
)
from centrodefamilia.web_api import (
    MESSAGE_LEVELS,
    CdfWebView,
    native_view,
    pending_messages,
    rendered,
)
from centrodefamilia.web_api_gestion import _errors, _field


def peek_messages(request):
    """Read the queued messages without consuming them (the next page shows them)."""
    django_request = request._request  # pylint: disable=protected-access
    storage = messages.get_messages(django_request)
    items = [
        {"message": str(item), "level": MESSAGE_LEVELS.get(item.level, "info")}
        for item in storage
    ]
    storage.used = False
    return items


def _redirect_payload(request, respuesta):
    """The native redirect as JSON: where it goes and the message it queued."""
    queued = peek_messages(request)
    return {
        "url": respuesta["Location"],
        "message": queued[-1]["message"] if queued else "",
        "level": queued[-1]["level"] if queued else "info",
    }


def _participante(participante):
    ciudadano = participante.ciudadano
    return {
        "id": participante.pk,
        "apellido": ciudadano.apellido,
        "nombre": ciudadano.nombre,
        "documento": rendered(ciudadano.documento),
        "sexo": str(ciudadano.sexo.sexo) if ciudadano.sexo_id else "",
        "fecha_registro": formats.date_format(
            timezone.localtime(participante.fecha_registro), "d/m/Y"
        ),
        "urls": {"ciudadano": reverse("ciudadanos_ver", args=[ciudadano.pk])},
    }


def _fila_inscrito(participante, actividad):
    fila = _participante(participante)
    fila["urls"]["delete"] = reverse(
        "participanteactividad_delete",
        kwargs={
            "centro_id": actividad.centro_id,
            "actividad_id": actividad.pk,
            "pk": participante.pk,
        },
    )
    return fila


def _fila_espera(participante, actividad):
    fila = _participante(participante)
    fila["urls"]["promover"] = reverse(
        "participanteactividad_promover",
        kwargs={
            "centro_id": actividad.centro_id,
            "actividad_id": actividad.pk,
            "pk": participante.pk,
        },
    )
    return fila


class ActividadDetailWebView(CdfWebView):
    """``GET /api/web/cdf/actividades/<pk>/``: the native ``actividadcentro_detail``."""

    def get(self, request, pk):
        vista = native_view(ActividadCentroDetailView, request, pk=pk)
        vista.object = vista.get_object()
        context = vista.get_context_data()
        actividad = vista.object
        centro = actividad.centro
        return Response(
            {
                "actividad": {
                    "id": actividad.pk,
                    "nombre": actividad.actividad.nombre,
                    "categoria": actividad.actividad.categoria.nombre,
                    "estado_display": str(actividad.get_estado_display()),
                    "horariosdesde": rendered(actividad.horariosdesde),
                    "horarioshasta": rendered(actividad.horarioshasta),
                    "cantidad_personas": rendered(actividad.cantidad_personas),
                    "sexos": [str(s.sexo) for s in actividad.sexoact.all()],
                    "dias": [str(d.nombre) for d in actividad.dias.all()],
                    "precio_total": rendered(context["precio_total"]),
                },
                "centro": {"id": centro.pk, "nombre": centro.nombre},
                "participantes": [
                    _fila_inscrito(p, actividad) for p in context["participantes"]
                ],
                "lista_espera": [
                    _fila_espera(p, actividad) for p in context["lista_espera"]
                ],
                "promo_error": bool(context["promo_error"]),
                "puede_tomar_asistencia": bool(context["puede_tomar_asistencia"]),
                "urls": {
                    "centro_list": reverse("centro_list"),
                    "centro_detail": reverse("centro_detail", args=[centro.pk]),
                    "edit": reverse(
                        "actividadcentro_edit", kwargs={"pk": actividad.pk}
                    ),
                    "create_participante": reverse(
                        "participanteactividad_create",
                        kwargs={
                            "centro_id": centro.pk,
                            "actividad_id": actividad.pk,
                        },
                    ),
                    "asistencia": reverse(
                        "actividadcentro_asistencia", kwargs={"pk": actividad.pk}
                    ),
                },
                "messages": pending_messages(request),
            }
        )


def _create_payload(vista, form, request):
    context = vista.get_context_data(form=form)
    return {
        "query": request.GET.get("query") or "",
        "ciudadanos": [
            {
                "id": c.pk,
                "apellido": c.apellido,
                "nombre": c.nombre,
                "documento": rendered(c.documento),
            }
            for c in context["ciudadanos"]
        ],
        "no_resultados": bool(context["no_resultados"]),
        "fields": [_field(form, name) for name in form.fields],
        **_errors(form),
        "urls": {
            "centro_list": reverse("centro_list"),
            "actividad_list": reverse("actividadcentro_list"),
        },
        "messages": pending_messages(request),
    }


class ParticipanteCrearWebView(CdfWebView):
    """``/api/web/cdf/centros/<c>/actividades/<a>/participantes/``: search form or POST."""

    http_method_names = ["get", "post"]

    def get(self, request, centro_id, actividad_id):
        vista = native_view(
            ParticipanteActividadCreateView,
            request,
            centro_id=centro_id,
            actividad_id=actividad_id,
        )
        vista.object = None
        return Response(_create_payload(vista, vista.get_form(), request))

    def post(self, request, centro_id, actividad_id):
        vista = native_view(
            ParticipanteActividadCreateView,
            request,
            centro_id=centro_id,
            actividad_id=actividad_id,
        )
        django_request = request._request  # pylint: disable=protected-access
        respuesta = vista.post(
            django_request, centro_id=centro_id, actividad_id=actividad_id
        )
        if respuesta.status_code != 302:
            return Response(
                _create_payload(vista, respuesta.context_data["form"], request),
                status=400,
            )
        return Response(_redirect_payload(request, respuesta))


class ParticipanteEliminarWebView(CdfWebView):
    """``.../participantes/<pk>/eliminar/``: the confirmation data or the native baja."""

    http_method_names = ["get", "post"]

    def get(self, request, centro_id, actividad_id, pk):
        participante = get_object_or_404(ParticipanteActividad, pk=pk)
        ciudadano = participante.ciudadano
        return Response(
            {
                "participante": {
                    "id": participante.pk,
                    "apellido": ciudadano.apellido,
                    "nombre": ciudadano.nombre,
                    "documento": rendered(ciudadano.documento),
                },
                "urls": {
                    "centro_list": reverse("centro_list"),
                    "actividad_list": reverse("actividadcentro_list"),
                    "detail": reverse(
                        "actividadcentro_detail",
                        kwargs={"pk": participante.actividad_centro_id},
                    ),
                },
                "messages": pending_messages(request),
            }
        )

    def post(self, request, centro_id, actividad_id, pk):
        vista = native_view(
            ParticipanteActividadDeleteView,
            request,
            centro_id=centro_id,
            actividad_id=actividad_id,
            pk=pk,
        )
        django_request = request._request  # pylint: disable=protected-access
        respuesta = vista.post(
            django_request, centro_id=centro_id, actividad_id=actividad_id, pk=pk
        )
        return Response(_redirect_payload(request, respuesta))


class ParticipantePromoverWebView(CdfWebView):
    """``POST .../lista-espera/<pk>/promover/``: the native promotion (never retried)."""

    http_method_names = ["post"]

    def post(self, request, centro_id, actividad_id, pk):
        vista = native_view(
            ParticipanteActividadPromoverView,
            request,
            centro_id=centro_id,
            actividad_id=actividad_id,
            pk=pk,
        )
        django_request = request._request  # pylint: disable=protected-access
        respuesta = vista.post(
            django_request, centro_id=centro_id, actividad_id=actividad_id, pk=pk
        )
        payload = _redirect_payload(request, respuesta)
        payload["promo_error"] = "promo_error=1" in respuesta["Location"]
        return Response(payload)
