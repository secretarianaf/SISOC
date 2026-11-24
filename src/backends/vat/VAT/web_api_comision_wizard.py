"""Web API (G1 v1) del asistente de alta de una comisión de curso (V04.02, U5).

``/api/web/vat/comisiones-asistente/cursos/<curso_id>/`` corre el ``SessionWizardView`` nativo (``ComisionCursoWizardView``):
el ``GET`` reinicia el asistente y devuelve el paso 1; el ``POST`` entrega el paso al almacenamiento nativo del asistente
(sesión), que valida, avanza, retrocede (``wizard_goto_step``) y, en el último paso, ejecuta ``done`` (crea la comisión, sus
horarios y sus sesiones, y encola el mensaje). Cada respuesta trae el contexto del paso actual: con el paso inválido es 400 con
los errores; al terminar es ``{"ok": true, "redirect": <url>}``. Acceso: ``VAT.add_comisioncurso`` y, además, el alcance del
centro del curso que aplica la vista nativa (403 sin alcance, 404 si el curso no existe).
"""

from django.http import HttpResponseRedirect
from rest_framework.response import Response

from VAT.views.comision_curso_wizard import ComisionCursoWizardView
from VAT.web_api_common import (
    VatNativeReadView,
    campo_formulario,
    mensajes_pendientes,
    texto,
)

CAMPOS_INFO = (
    "ubicacion",
    "cupo_total",
    "estado",
    "fecha_inicio",
    "fecha_fin",
    "acepta_lista_espera",
    "cupo_lista_espera",
    "observaciones",
)
CAMPOS_HORARIO = ("dia_semana", "hora_desde", "hora_hasta", "vigente", "DELETE")


def _campo(campo):
    """El campo del formulario del paso con el nombre que envía el navegador (con el prefijo del paso)."""
    cuerpo = {**campo_formulario(campo), "name": campo.html_name}
    if not campo.form.use_required_attribute:
        # Los formularios de un formset no dibujan ``required`` (``BaseFormSet._construct_form``).
        cuerpo["attrs"] = {k: v for k, v in cuerpo["attrs"].items() if k != "required"}
    return cuerpo


def _horario(formulario):
    return {"fields": [_campo(formulario[nombre]) for nombre in CAMPOS_HORARIO]}


class ComisionCursoAsistenteJson(ComisionCursoWizardView):
    """La vista nativa del asistente, con la respuesta de cada paso en JSON en lugar de la plantilla."""

    def render_to_response(self, context, **response_kwargs):
        form = context["form"]
        invalido = form.is_bound and not form.is_valid()
        return Response(self.proyectar(context), status=400 if invalido else 200)

    def proyectar(self, context):
        paso = self.steps.current
        curso = self.curso
        cuerpo = {
            "step": paso,
            "steps": list(self.get_form_list()),
            "management": {
                "name": f"{self.prefix}-current_step",
                "value": paso,
            },
            "estado_label": str(context["estado_label"]),
            "curso": {
                "nombre": texto("{{ c.nombre|default:'-' }}", c=curso),
                "plan": texto("{{ c.plan_estudio|default:'-' }}", c=curso),
                "codigo": texto('{{ c.id|stringformat:"011d" }}', c=curso),
            },
            "urls": {"cancel": context["wizard_cancel_url"]},
            "messages": mensajes_pendientes(self.request),
        }
        form = context["form"]
        if paso == "info":
            cuerpo["fields"] = [_campo(form[nombre]) for nombre in CAMPOS_INFO]
            cuerpo["non_field_errors"] = [str(e) for e in form.non_field_errors()]
        elif paso == "horarios":
            cuerpo["formset"] = {
                "prefix": form.prefix,
                "management": [
                    {"name": campo.html_name, "value": str(campo.value())}
                    for campo in form.management_form
                ],
                "forms": [_horario(f) for f in form.forms],
                "empty": _horario(form.empty_form),
                "non_form_errors": [str(e) for e in form.non_form_errors()],
            }
        else:
            cuerpo["resumen"] = self.resumen(context)
        return cuerpo

    @staticmethod
    def resumen(context):
        """Los textos de la plantilla ``step3_confirmacion.html`` sobre el contexto del paso."""
        datos = context["step1_data"]
        return {
            "ubicacion": texto("{{ d.ubicacion|default:'Sede u Anexos' }}", d=datos),
            "periodo": texto(
                "{% if d.fecha_inicio and d.fecha_fin %}{{ d.fecha_inicio|date:'d/m/Y' }} - "
                "{{ d.fecha_fin|date:'d/m/Y' }}{% else %}-{% endif %}",
                d=datos,
            ),
            "cupo": texto("{{ d.cupo_total|default:'00' }}", d=datos),
            "horarios": [
                {
                    "dia": texto("{{ f.dia }}", f=fila),
                    "horas": texto(
                        "{{ f.hora_desde|time:'H:i' }} a {{ f.hora_hasta|time:'H:i' }}",
                        f=fila,
                    ),
                    "duracion": fila["duracion"],
                    "estado": fila["estado_label"],
                }
                for fila in context["horarios_resumen"]
            ],
            "total": context["horarios_total_label"],
        }


class ComisionCursoAsistenteWebView(VatNativeReadView):
    """``GET`` (paso 1) y ``POST`` (avanzar, retroceder, confirmar) del asistente nativo."""

    http_method_names = ["get", "head", "post"]
    codigos = ["VAT.add_comisioncurso"]

    def get(self, request, **kwargs):
        return self.correr(request, kwargs)

    def post(self, request, **kwargs):
        return self.correr(request, kwargs)

    @staticmethod
    def correr(request, kwargs):
        # El ``dispatch`` nativo trae el curso (404), exige el alcance del centro (403), arma el almacenamiento y despacha.
        django_request = request._request  # pylint: disable=protected-access
        respuesta = ComisionCursoAsistenteJson.as_view()(django_request, **kwargs)
        if isinstance(respuesta, HttpResponseRedirect):
            return Response({"ok": True, "redirect": respuesta["Location"]})
        return respuesta
