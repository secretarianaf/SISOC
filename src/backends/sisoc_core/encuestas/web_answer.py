"""Session JSON transport for the unchanged pending-survey answer circuit."""

from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from core.templatetags.custom_filters import has_any_group
from encuestas.context_processors import ronda_pendiente
from encuestas.views import DescartarRondaView, PosponerRondaView, ResponderRondaView
from usuarios.web_context import build_legacy_presentation
from usuarios.web_session import resolve_web_access


@method_decorator(csrf_protect, name="dispatch")
class _SurveyTransportMixin:
    """Preserve native action hooks without requiring business-ready access."""

    http_method_names = ["post", "options"]

    def dispatch(self, request, *args, **kwargs):
        access = resolve_web_access(request)
        if access.state not in {"ready", "mandatory_survey_required"}:
            response = JsonResponse(
                {
                    "detail": "Debe completar el requisito de acceso correspondiente.",
                    "state": access.state,
                    "required_action_url": access.required_action_url,
                },
                status=401 if access.state == "unauthenticated" else 403,
            )
        elif (
            request.method == "POST"
            and request.content_type != "application/x-www-form-urlencoded"
        ):
            response = JsonResponse(
                {"detail": "Formato de solicitud no admitido."}, status=415
            )
        else:
            response = super().dispatch(request, *args, **kwargs)
            if response.status_code in (301, 302, 303):
                # Native errors also redirect with a queued message. A redirect
                # is not a successful-save receipt, and no draft is retained.
                converted = JsonResponse({"redirect": response["Location"]})
                converted.cookies = response.cookies
                response = converted
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response


def _question_payload(question):
    condition = None
    if question.pregunta_condicion_id:
        condition = {
            "order": question.pregunta_condicion.orden,
            "operator": question.operador_condicion,
            "value": question.valor_condicion,
        }
    return {
        "id": question.pk,
        "order": question.orden,
        "text": question.texto,
        "type": question.tipo,
        "required": question.obligatoria,
        "condition": condition,
        "options": [
            {"id": option.pk, "value": option.valor, "text": option.texto}
            for option in question.opciones.all()
        ],
    }


def _round_payload(ronda):
    if ronda is None:
        return None
    survey = ronda.encuesta
    return {
        "id": ronda.pk,
        "title": survey.titulo,
        "description": survey.descripcion,
        "mode": survey.modalidad,
        "anonymous": survey.es_anonima,
        "questions": [
            _question_payload(question)
            for question in survey.preguntas.select_related(
                "pregunta_condicion"
            ).prefetch_related("opciones")
        ],
        "actions": {
            "answer": reverse("encuestas_responder", args=[ronda.pk]),
            "postpone": (
                reverse("encuestas_responder_mas_tarde", args=[ronda.pk])
                if survey.modalidad == "postergable"
                else None
            ),
            "dismiss": (
                reverse("encuestas_responder_descartar", args=[ronda.pk])
                if survey.es_opcional
                else None
            ),
        },
    }


@method_decorator(ensure_csrf_cookie, name="dispatch")
class WebPendingSurveyView(_SurveyTransportMixin, View):
    """Project only the source-visible home, frame and first pending modal."""

    http_method_names = ["get", "head", "options"]

    def get(self, request):
        ronda = ronda_pendiente(request).get("ronda_pendiente")
        levels = {
            messages.ERROR: "error",
            messages.WARNING: "warning",
            messages.SUCCESS: "success",
        }
        inet = not request.user.is_superuser and has_any_group(
            request.user, "CFP,CFPJuridicccion,CFPINET"
        )
        return JsonResponse(
            {
                "presentation": build_legacy_presentation(request),
                "home_variant": "inet" if inet else "default",
                "round": _round_payload(ronda),
                "messages": [
                    {
                        "message": str(message),
                        "level": levels.get(message.level, "info"),
                    }
                    for message in messages.get_messages(request)
                ],
            }
        )


class WebAnswerSurveyView(_SurveyTransportMixin, ResponderRondaView):
    """Use registrar_respuesta through its original redirect/message hook."""


class WebPostponeSurveyView(_SurveyTransportMixin, PosponerRondaView):
    """Keep eligibility and reminder timing in the original service."""


class WebDismissSurveyView(_SurveyTransportMixin, DescartarRondaView):
    """Keep optional-only dismissal in the original service."""
