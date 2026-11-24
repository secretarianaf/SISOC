"""Web API (G1 v1) of "Generar usuario" of a CDI (CDI01.01) for the React page.

``GenerarUsuarioCDIView`` is inherited, so the form, the RENAPER block (signed
token, locked identity), the cupo, the responsable rule, the CDI-A3 scope and
``generar_usuario_delegado`` stay the native ones. Access, in order: G1, the
URL permission (``centrodeinfancia.view_centrodeinfancia``) and the native
dispatch (404 unknown centre, 403 when ``puede_generar_usuario_cdi`` fails).

GET returns the form. A valid POST creates the user and answers what the
native result page shows (user name, email, mail status and the temporary
password) once, in this response only: ``private, no-store``, never stored,
never part of a GET. An invalid form returns 400 with its errors.
"""

from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from centrodeinfancia.services_renaper_bloques import BLOQUE_USUARIO
from centrodeinfancia.views_usuario_cdi import GenerarUsuarioCDIView
from centrodeinfancia.web_api import pending_messages
from centrodeinfancia.web_api_formularios import (
    TransporteFormularioMixin,
    bloque_renaper_web,
    campo_web,
    privada,
)

PERMISO_VER = "centrodeinfancia.view_centrodeinfancia"
RESULTADO = "centrodeinfancia/usuario_cdi_generado.html"
CAMPOS = ("dni", "first_name", "last_name", "cuil", "email")


def _centro(centro):
    return {
        "id": centro.pk,
        "nombre": centro.nombre,
        "url": reverse("centrodeinfancia_detalle", args=[centro.pk]),
    }


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class UsuarioGenerarWebView(TransporteFormularioMixin, GenerarUsuarioCDIView):
    """``/api/web/cdi/centros/<pk>/usuarios/generar/``: native generation."""

    permission_codes = (PERMISO_VER,)

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form), status=400)

    def form_valid(self, form):
        response = super().form_valid(form)
        if not (
            isinstance(response, TemplateResponse)
            and response.template_name == RESULTADO
        ):
            return response
        datos = response.context_data
        usuario = datos["usuario"]
        return privada(
            JsonResponse(
                {
                    "ok": True,
                    "centro": _centro(datos["centro"]),
                    "usuario": {"username": usuario.username, "email": usuario.email},
                    "password": datos["password"],
                    "email_enviado": bool(datos["email_enviado"]),
                    "puede_generar_otro": bool(datos["puede_generar_otro"]),
                    "urls": {
                        "generar": reverse(
                            "centrodeinfancia_generar_usuario",
                            args=[datos["centro"].pk],
                        )
                    },
                    "messages": pending_messages(self.request),
                }
            )
        )

    def render_to_response(self, context, **response_kwargs):
        form = context["form"]
        token = context["renaper_tokens"].get(BLOQUE_USUARIO, "")
        return privada(
            JsonResponse(
                {
                    "centro": _centro(context["centro"]),
                    "usuarios_restantes": context["usuarios_restantes"],
                    "fields": [campo_web(form, nombre) for nombre in CAMPOS],
                    "non_field_errors": (
                        [str(e) for e in form.non_field_errors()]
                        if form.is_bound
                        else []
                    ),
                    "renaper": bloque_renaper_web(
                        form, BLOQUE_USUARIO, token, permite_cambiar=True
                    ),
                    "urls": {"cancelar": _centro(context["centro"])["url"]},
                    "messages": pending_messages(self.request),
                },
                status=response_kwargs.get("status", 200),
            )
        )
