"""Web API (G1 v1) of the CDF referente user generation (CDF04.03).

Same access chain as ``centrodefamilia.web_api``: G1 session and web
prerequisites, then ``centrodefamilia.view_centro`` (403). After that the
native ``GenerarUsuarioCDFView.dispatch`` runs unchanged: missing centre 404
(before the predicate), then ``puede_generar_usuario_cdf`` (delegation,
territory and quota) 403.

The POST runs the native ``form_valid``: ``generar_usuario_delegado`` with the
``AccesoCDF`` callback and the quota check, exactly as the HTML page. Its
success message is consumed here (the native result page shows it once) and
returned as ``message``. The 201 body is the CR1 projection only: username,
email, the temporary password, whether the email was sent and whether another
user can be generated. It is ``private, no-store`` and never logged. No retries.
"""

from rest_framework.response import Response

from centrodefamilia.access import GRUPO_CDF_REFERENTE_CENTRO
from centrodefamilia.views.generar_usuario import GenerarUsuarioCDFView
from centrodefamilia.web_api import CdfWebView, native_view, pending_messages
from centrodefamilia.web_api_gestion import _errors, _field

RESULT_TEMPLATE = "centros/usuario_cdf_generado.html"


class _GuardedGenerar(GenerarUsuarioCDFView):
    """The native view; its GET only answers after ``dispatch`` (404, then 403)."""

    def get(self, request, *args, **kwargs):
        return None


def _form_payload(vista, form, request):
    centro = vista.centro
    return {
        "centro": {"id": centro.pk, "nombre": centro.nombre},
        "grupo": GRUPO_CDF_REFERENTE_CENTRO,
        "usuarios_restantes": vista.get_context_data(form=form)["usuarios_restantes"],
        "initial": vista.get_initial(),
        "fields": [_field(form, name) for name in form.fields],
        **_errors(form),
        "messages": pending_messages(request),
    }


class CentroGenerarUsuarioWebView(CdfWebView):
    """``/api/web/cdf/centros/<pk>/generar-usuario/``: form data or the native creation."""

    http_method_names = ["get", "post"]

    def _dispatch(self, request, pk):
        vista = native_view(_GuardedGenerar, request, pk=pk)
        django_request = request._request  # pylint: disable=protected-access
        return vista, vista.dispatch(django_request, pk=pk)

    def get(self, request, pk):
        vista, _ = self._dispatch(request, pk)
        return Response(_form_payload(vista, vista.get_form(), request))

    def post(self, request, pk):
        vista, respuesta = self._dispatch(request, pk)
        if getattr(respuesta, "template_name", None) != RESULT_TEMPLATE:
            return Response(
                _form_payload(vista, respuesta.context_data["form"], request),
                status=400,
            )
        context = respuesta.context_data
        usuario = context["usuario"]
        queued = pending_messages(request)
        return Response(
            {
                "usuario": {"username": usuario.username, "email": usuario.email},
                "password": context["password"],
                "email_enviado": context["email_enviado"],
                "puede_generar_otro": context["puede_generar_otro"],
                "message": queued[-1]["message"] if queued else "",
            },
            status=201,
        )
