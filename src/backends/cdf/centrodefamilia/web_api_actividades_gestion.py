"""Web API (G1 v1) of the CDF activity list and the activity catalog form (CDF-B).

Same access chain as ``centrodefamilia.web_api``: G1 session and web
prerequisites, then ``centrodefamilia.view_centro``. Nothing else is added or
removed (decision D1): ``ActividadCentroListView`` and ``ActividadCreateView``
only require login besides that URL guard (the ``test_func`` of the catalog
view is never evaluated, so superuser is not an effective gate).

- ``GET /api/web/cdf/actividades/?centro=``: the native list, without paging,
  ordered by centre and activity name, optionally filtered by centre.
- ``/api/web/cdf/actividades/nueva/``: the catalog form (``ActividadForm``:
  category and name) and its native ``post()``; a valid POST saves and the
  native view redirects to the centre list without queuing a message.

Nothing is retried.
"""

from django.urls import reverse
from rest_framework.response import Response

from centrodefamilia.views.actividad import (
    ActividadCentroListView,
    ActividadCreateView,
)
from centrodefamilia.web_api import (
    CdfWebView,
    native_view,
    pending_messages,
    rendered,
)
from centrodefamilia.web_api_gestion import _errors, _field


def plain_field(form, name):
    """The field payload plus the widget attributes the plain ``{{ form.field }}`` renders."""
    payload = _field(form, name)
    payload["html"] = {
        key: str(value)
        for key, value in form.fields[name].widget.attrs.items()
        if key in ("class", "placeholder")
    }
    return payload


def _fila(actividad):
    return {
        "id": actividad.pk,
        "centro": actividad.centro.nombre,
        "actividad": actividad.actividad.nombre,
        "dias": [str(dia.nombre) for dia in actividad.dias.all()],
        # The template prints the related manager when there are no days.
        "dias_vacio": str(actividad.dias),
        "horariosdesde": rendered(actividad.horariosdesde),
        "horarioshasta": rendered(actividad.horarioshasta),
        "estado_display": str(actividad.get_estado_display()),
        "urls": {
            "detail": reverse("actividadcentro_detail", kwargs={"pk": actividad.pk})
        },
    }


class ActividadListWebView(CdfWebView):
    """``GET /api/web/cdf/actividades/``: the native ``actividadcentro_list``."""

    def get(self, request):
        vista = native_view(ActividadCentroListView, request)
        vista.object_list = vista.get_queryset()
        context = vista.get_context_data()
        return Response(
            {
                "headers": [
                    {
                        "title": header["title"],
                        "sortable": bool(header.get("sortable")),
                        "sort_key": header.get("sort_key", header["title"]),
                    }
                    for header in context["table_headers"]
                ],
                "results": [_fila(a) for a in context["actividades"]],
                "messages": pending_messages(request),
            }
        )


def _catalogo_payload(form, request):
    return {
        "fields": [plain_field(form, name) for name in form.fields],
        **_errors(form),
        "urls": {"cancel": reverse("centro_list")},
        "messages": pending_messages(request),
    }


class ActividadCatalogoWebView(CdfWebView):
    """``/api/web/cdf/actividades/nueva/``: the catalog form or the native save."""

    http_method_names = ["get", "post"]

    def get(self, request):
        vista = native_view(ActividadCreateView, request)
        vista.object = None
        return Response(_catalogo_payload(vista.get_form(), request))

    def post(self, request):
        vista = native_view(ActividadCreateView, request)
        django_request = request._request  # pylint: disable=protected-access
        respuesta = vista.post(django_request)
        if respuesta.status_code != 302:
            return Response(
                _catalogo_payload(respuesta.context_data["form"], request),
                status=400,
            )
        return Response({"url": respuesta["Location"]})
