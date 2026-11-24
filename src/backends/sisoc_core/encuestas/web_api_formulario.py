"""Survey create/edit form for React (E04.C, G1 v1).

``GET /api/web/encuestas/crear/`` and ``GET /api/web/encuestas/<pk>/editar/`` run ``EncuestaCreateView`` (``encuestas.add_encuesta``)
and ``EncuestaUpdateView`` (``encuestas.change_encuesta``) and project the context of ``encuesta_form.html``: the field values
as the widgets render them, the rows of the question editor (``preguntas_json_inicial``) and the choices the editor needs. The
POST of each path runs the native view on the same request: a valid form leaves the native message queued and answers its
redirect; an invalid one is the native re-render, answered with status 400 and the same projection (bound values, field and
non-field errors, the questions the client posted).
"""

from django.urls import reverse
from rest_framework.response import Response

from encuestas.views import EncuestaCreateView, EncuestaUpdateView
from encuestas.web_api_revision import _fecha_hora
from encuestas.web_transport_encuestas import EncuestaNativeWebView, pending_messages

ALTA = ["encuestas.add_encuesta"]
EDICION = ["encuestas.change_encuesta"]
CAMPOS = (
    "titulo",
    "descripcion",
    "es_anonima",
    "modalidad",
    "es_recurrente",
    "intervalo_recordatorio_dias",
    "duracion_ronda_dias",
    "intervalo_recurrencia_dias",
)
BOOLEANOS = ("es_anonima", "es_recurrente")


def _valor(campo):
    valor = campo.value()
    if campo.name in BOOLEANOS:
        return bool(valor)
    return "" if valor is None else str(valor)


def _campo(form, nombre):
    campo = form[nombre]
    atributos = campo.build_widget_attrs({}, campo.field.widget)
    return {
        "value": _valor(campo),
        "errors": [str(error) for error in campo.errors],
        "invalid": atributos.get("aria-invalid") == "true",
        "describedby": atributos.get("aria-describedby", ""),
    }


def _motivo(encuesta):
    if not encuesta.motivo_rechazo:
        return None
    return {
        "texto": encuesta.motivo_rechazo,
        "usuario": str(encuesta.usuario_rechazo),
        "fecha": _fecha_hora(encuesta.fecha_rechazo),
        "estado": encuesta.estado,
    }


def _preguntas(inicial):
    # ``json_script`` prints whatever the native view hands over; the editor only hydrates a list of rows.
    return (
        [fila for fila in inicial if isinstance(fila, dict)]
        if isinstance(inicial, list)
        else []
    )


def proyectar_formulario(context, request):
    """Context of ``encuesta_form.html`` as the template and the editor script read it."""
    form = context["form"]
    encuesta = form.instance
    return {
        "id": encuesta.pk,
        "motivo_rechazo": _motivo(encuesta) if encuesta.pk else None,
        "non_field_errors": [str(error) for error in form.non_field_errors()],
        "fields": {nombre: _campo(form, nombre) for nombre in CAMPOS},
        "preguntas": _preguntas(context["preguntas_json_inicial"]),
        "tipos_pregunta": [
            [valor, str(label)] for valor, label in context["tipos_pregunta"]
        ],
        "operadores_condicion": [
            [valor, str(label)] for valor, label in context["operadores_condicion"]
        ],
        "tipos_con_opciones": context["tipos_pregunta_con_opciones"],
        "tipos_ponderables": context["tipos_pregunta_ponderables"],
        "urls": (
            {"exportar": reverse("encuestas_exportar", args=[encuesta.pk])}
            if encuesta.pk
            else None
        ),
        "messages": pending_messages(request),
    }


class FormularioWebView(EncuestaNativeWebView):
    """Shared GET/POST of both form screens; subclasses name the native view and its permission."""

    http_method_names = ["get", "head", "post", "options"]

    def _kwargs(self, pk):
        return {} if pk is None else {"pk": pk}

    def get(self, request, pk=None):
        response = self.run_native(request, **self._kwargs(pk))
        if self.redirect_result(request, response, consume=False) is not None:
            return Response({"redirect": response["Location"]})
        # pylint: disable-next=protected-access
        return Response(proyectar_formulario(response.context_data, request._request))

    def post(self, request, pk=None):
        response = self.run_native(request, **self._kwargs(pk))
        redirect = self.redirect_result(request, response, consume=False)
        if redirect is not None:
            return redirect
        # pylint: disable-next=protected-access
        body = proyectar_formulario(response.context_data, request._request)
        return Response(body, status=400)


class CrearWebView(FormularioWebView):
    permission_codes = ALTA
    native_view = EncuestaCreateView


class EditarWebView(FormularioWebView):
    permission_codes = EDICION
    native_view = EncuestaUpdateView
