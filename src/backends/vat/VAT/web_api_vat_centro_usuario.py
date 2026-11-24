"""Web API (G1 v1) de «Generar usuario» de un centro de VAT (V06.02).

``/api/web/vat/centros-usuarios/<pk>/generar/`` corre la vista nativa ``GenerarUsuarioCentroVATView`` con su ``dispatch``
(centro inexistente 404 y, después, ``puede_generar_usuario_centro_vat``: delegación del grupo CFP, edición del centro y
cupo, 403). El GET devuelve el formulario precargado como lo hace la vista; el POST corre su ``form_valid``
(``generar_usuario_delegado`` y el vínculo con el centro). Un POST válido responde 201 con lo que muestra la página nativa
de resultado, la contraseña temporal incluida, una sola vez: la respuesta es ``private, no-store``, la contraseña no
forma parte de ningún GET y no se guarda ni se registra. Un POST inválido responde 400 con el formulario ligado.
Acceso: ``VAT.view_centro``, como la ruta.
"""

from django.urls import reverse
from django.utils.cache import patch_cache_control
from rest_framework.response import Response

from VAT.views.generar_usuario import GenerarUsuarioCentroVATView
from VAT.web_api_common import VatNativeReadView, campo_formulario, mensajes_pendientes

_RESULTADO = "usuario_generado.html"


def _campo(form, nombre):
    """The field as ``as_crispy_field`` renders it: the widget attributes plus the ``maxlength`` of the model-less field."""
    campo = campo_formulario(form[nombre])
    adicionales = form.fields[nombre].widget_attrs(form.fields[nombre].widget)
    campo["attrs"].update(
        {
            clave: str(valor)
            for clave, valor in adicionales.items()
            if clave == "maxlength"
        }
    )
    return campo


def _centro(centro):
    return {
        "id": centro.pk,
        "nombre": centro.nombre,
        "url": reverse("vat_centro_detail", args=[centro.pk]),
    }


class CentroGenerarUsuarioWebView(VatNativeReadView):
    """``GET|POST .../centros-usuarios/<pk>/generar/``: ``generar_usuario.html`` y ``usuario_generado.html``."""

    native_class = GenerarUsuarioCentroVATView
    codigos = ["VAT.view_centro"]
    http_method_names = ["get", "head", "post"]

    def _despachar(self, pk):
        vista = self.native(pk=pk)
        return vista.dispatch(
            self.request._request, pk=pk  # pylint: disable=protected-access
        )

    def _formulario(self, contexto, status=200):
        form = contexto["form"]
        centro = contexto["centro"]
        return Response(
            {
                "centro": _centro(centro),
                "usuarios_restantes": contexto["usuarios_restantes"],
                "fields": [_campo(form, nombre) for nombre in form.fields],
                "non_field_errors": [str(e) for e in form.non_field_errors()],
                "urls": {
                    "cancelar": reverse("vat_centro_detail", args=[centro.pk]),
                    "generar": reverse("vat_centro_generar_usuario", args=[centro.pk]),
                },
                "messages": mensajes_pendientes(
                    self.request._request  # pylint: disable=protected-access
                ),
            },
            status=status,
        )

    def get(self, request, pk):
        return self._formulario(self._despachar(pk).context_data)

    def post(self, request, pk):
        respuesta = self._despachar(pk)
        if _RESULTADO not in str(respuesta.template_name):
            return self._formulario(respuesta.context_data, status=400)
        contexto = respuesta.context_data
        usuario = contexto["usuario"]
        resultado = Response(
            {
                "ok": True,
                "centro": _centro(contexto["centro"]),
                "usuario": {"username": usuario.username, "email": usuario.email},
                "password": contexto["password"],
                "email_enviado": bool(contexto["email_enviado"]),
                "puede_generar_otro": bool(contexto["puede_generar_otro"]),
                "urls": {
                    "generar": reverse(
                        "vat_centro_generar_usuario", args=[contexto["centro"].pk]
                    )
                },
                "messages": mensajes_pendientes(
                    request._request  # pylint: disable=protected-access
                ),
            },
            status=201,
        )
        patch_cache_control(resultado, private=True, no_store=True)
        return resultado
