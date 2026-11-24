"""Alta de un familiar (grupo familiar) para React (C05.02, G1 v1).

``/api/web/ciudadanos/<pk>/familiares/nuevo/`` lo sirve el core y corre
``GrupoFamiliarCreateView`` con su orden nativo: el ciudadano primero (404) y
después el permiso ``ciudadanos.change_ciudadano`` (403). El ``GET`` proyecta lo que
imprime ``grupofamiliar_form.html``; el ``POST`` arma el formulario con
``get_form_kwargs`` (el campo ``ciudadano_2`` toma ``ciudadano_2_id``, como allá) y,
si es válido, corre ``form_valid`` (relación, mensaje y redirección a la ficha). Un
formulario inválido responde 400 con el formulario ligado y no escribe nada.
"""

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.cache import patch_cache_control, patch_vary_headers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from ciudadanos.models import Ciudadano
from ciudadanos.views import GrupoFamiliarCreateView
from ciudadanos.web_ficha import pending_messages
from core.web_gate import WebGatePermission

SELECTS = ("vinculo", "estado_relacion")
BOOLEANOS = ("conviven", "cuidador_principal")


def _vista(request, pk):
    try:
        ciudadano = get_object_or_404(Ciudadano, pk=pk)
    except Http404 as exc:
        raise NotFound() from exc
    if not request.user.has_perm("ciudadanos.change_ciudadano"):
        raise PermissionDenied()
    vista = GrupoFamiliarCreateView()
    # pylint: disable-next=protected-access
    vista.setup(request._request, pk=pk)
    vista.ciudadano = ciudadano
    return vista


def _valor(form, nombre):
    valor = form[nombre].value()
    if nombre in BOOLEANOS:
        return bool(valor)
    return "" if valor is None else str(valor)


def _proyectar(form, ciudadano, request):
    """Lo que imprime el template: etiquetas, opciones, valores y errores del form."""
    campos = {}
    for nombre in ("ciudadano_2", *SELECTS, *BOOLEANOS, "observaciones"):
        campo = {"label": str(form[nombre].label)}
        if nombre in SELECTS:
            campo["options"] = [
                {"value": str(valor), "label": str(texto)}
                for valor, texto in form.fields[nombre].choices
            ]
        if nombre == "ciudadano_2":
            campo["placeholder"] = form.fields[nombre].widget.attrs["placeholder"]
        campos[nombre] = campo
    return {
        "ciudadano": {
            "id": ciudadano.pk,
            "texto": str(ciudadano),
            "volver_url": ciudadano.get_absolute_url(),
        },
        "campos": campos,
        "values": {nombre: _valor(form, nombre) for nombre in campos},
        "errors": {
            nombre: [str(e) for e in errores] for nombre, errores in form.errors.items()
        },
        "messages": pending_messages(request),
    }


class CiudadanoFamiliarNuevoWebView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "post"]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response

    def get(self, request, pk):
        vista = _vista(request, pk)
        form = vista.get_form()
        return Response(_proyectar(form, vista.ciudadano, request))

    def post(self, request, pk):
        vista = _vista(request, pk)
        # El cuerpo es urlencoded como el del formulario nativo; DRF lo lee una sola
        # vez y deja ``request.POST`` de Django listo para ``get_form_kwargs``.
        form = vista.get_form()
        if not form.is_valid():
            return Response(_proyectar(form, vista.ciudadano, request), status=400)
        respuesta = vista.form_valid(form)
        return Response({"ok": True, "redirect": respuesta["Location"]})
