"""Publication review for React (E04.B, G1 v1).

``GET /api/web/encuestas/<pk>/revision/`` runs ``EncuestaRevisionView`` (``encuestas.aprobar_encuesta`` or
``encuestas.change_encuesta``) and projects the context of ``encuesta_revision.html``. ``POST .../aprobar/``
runs ``EncuestaAprobarView`` (``publicar``) and ``POST .../rechazar/`` runs ``EncuestaRechazarView``
(``rechazar_publicacion``), both ``aprobar_encuesta`` only. A service rejection keeps its native redirect
and message (left queued for the page the client navigates to); an invalid reason is the native 400 with the
form errors.
"""

from django.template.defaultfilters import capfirst
from django.template.defaultfilters import date as date_filter
from django.utils.timezone import localtime
from rest_framework.response import Response

from encuestas.views import (
    EncuestaAprobarView,
    EncuestaRechazarView,
    EncuestaRevisionView,
)
from encuestas.web_transport_encuestas import EncuestaNativeWebView, pending_messages

REVISAR = ["encuestas.aprobar_encuesta", "encuestas.change_encuesta"]
APROBAR = ["encuestas.aprobar_encuesta"]


def _fecha_hora(value):
    return date_filter(localtime(value), "d/m/Y H:i") if value else ""


def _segmentacion(segmentacion):
    if not segmentacion:
        return None
    return {
        "tipo": segmentacion.tipo,
        "label": segmentacion.get_tipo_display(),
        "destinatarios": [
            f"{item.get_tipo_documento_display()}: {item.numero_documento}"
            for item in segmentacion.destinatarios.all()
        ],
        "usuarios": [
            {
                "id": usuario.pk,
                "username": usuario.get_username(),
                "full_name": usuario.get_full_name(),
            }
            for usuario in segmentacion.usuarios.all()
        ],
        "grupos": [grupo.name for grupo in segmentacion.grupos.all()],
    }


def _pregunta(numero, pregunta):
    condicion = None
    if pregunta.pregunta_condicion_id:
        condicion = (
            f"Se muestra si «{pregunta.pregunta_condicion.texto}» "
            f"{pregunta.get_operador_condicion_display().lower()} "
            f"«{pregunta.valor_condicion}»."
        )
    return {
        "numero": numero,
        "tipo": pregunta.tipo,
        "tipo_label": pregunta.get_tipo_display(),
        "obligatoria": bool(pregunta.obligatoria),
        "texto": pregunta.texto,
        "condicion": condicion,
        "pondera": bool(pregunta.pondera),
        "puntaje_si": pregunta.puntaje_si,
        "puntaje_no": pregunta.puntaje_no,
        "opciones": [
            {"texto": opcion.texto, "puntaje": opcion.puntaje}
            for opcion in pregunta.opciones.all()
        ],
    }


def proyectar_revision(context, request):
    """Context of ``encuesta_revision.html`` as the template prints it."""
    encuesta = context["encuesta"]
    return {
        "id": encuesta.pk,
        "titulo": encuesta.titulo,
        "version": encuesta.version,
        "estado": encuesta.estado,
        "estado_label": encuesta.get_estado_display(),
        "creador": str(encuesta.usuario_creador),
        "motivo_rechazo": (
            {
                "texto": encuesta.motivo_rechazo,
                "usuario": str(encuesta.usuario_rechazo),
                "fecha": _fecha_hora(encuesta.fecha_rechazo),
            }
            if encuesta.motivo_rechazo
            else None
        ),
        "descripcion": encuesta.descripcion or "",
        "modalidad": capfirst(encuesta.modalidad),
        "es_anonima": bool(encuesta.es_anonima),
        "disponible_pwa": bool(encuesta.disponible_pwa),
        "duracion_ronda_dias": encuesta.duracion_ronda_dias,
        "es_recurrente": bool(encuesta.es_recurrente),
        "intervalo_recurrencia_dias": encuesta.intervalo_recurrencia_dias,
        "intervalo_recordatorio_dias": encuesta.intervalo_recordatorio_dias or 0,
        "segmentacion": _segmentacion(context["segmentacion"]),
        "preguntas": [
            _pregunta(numero, pregunta)
            for numero, pregunta in enumerate(context["preguntas"], 1)
        ],
        "solicitada_por": str(encuesta.usuario_ultima_modificacion),
        "fecha_solicitud": _fecha_hora(encuesta.fecha_ultima_modificacion),
        "puede_aprobar": request.user.has_perm("encuestas.aprobar_encuesta"),
        "messages": pending_messages(request),
    }


class RevisionWebView(EncuestaNativeWebView):
    permission_codes = REVISAR
    native_view = EncuestaRevisionView
    http_method_names = ["get", "head", "options"]

    def get(self, request, pk):
        response = self.run_native(request, pk=pk)
        # pylint: disable-next=protected-access
        return Response(proyectar_revision(response.context_data, request._request))


class AprobarWebView(EncuestaNativeWebView):
    permission_codes = APROBAR
    native_view = EncuestaAprobarView
    http_method_names = ["post", "options"]

    def post(self, request, pk):
        return self.redirect_result(
            request, self.run_native(request, pk=pk), consume=False
        )


class RechazarWebView(EncuestaNativeWebView):
    permission_codes = APROBAR
    native_view = EncuestaRechazarView
    http_method_names = ["post", "options"]

    def post(self, request, pk):
        response = self.run_native(request, pk=pk)
        result = self.redirect_result(request, response, consume=False)
        if result is not None:
            return result
        form = response.context_data["rechazo_form"]
        return Response({"errors": form.errors.get_json_data()}, status=400)
