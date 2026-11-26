"""Web API (G1 v1) of the comedor collaborator screens served by React (CO03.01).

``/api/web/comedores/colaboradores/`` is published by the Comedores backend. After
G1 (``WebGatePermission``) each endpoint keeps the permission code of its native URL
(``comedores.add/change/delete_colaboradorespacio``, superuser bypass included) and
runs the native view's own ``dispatch`` (``comedores.views.colaborador``): the scoped
comedor, the "linea secos" veto of the creation, the citizen search (local first,
then RENAPER), ``ColaboradorEspacioForm`` and ``ColaboradorEspacioService`` (citizen,
M2M, actor and audit snapshot) stay the native ones. A native redirect becomes
``{"ok": true, "redirect": ...}``; a rejected request returns 400 with the bound form
and writes nothing. A collaborator is not an access user: nothing here creates or
grants one.
"""

from django.contrib import messages
from django.template import Context, Template
from django.urls import reverse
from rest_framework.response import Response

from comedores.views.colaborador import (
    ColaboradorEspacioCreateView,
    ColaboradorEspacioDeleteView,
    ColaboradorEspacioUpdateView,
)
from comedores.web_api_montos import _valor_de_campo
from core.web_gate import WebGatePermission
from intervenciones.web_api import NativeWebView, comedor_ref, requires_any

FORMATOS = ("multipart/form-data", "application/x-www-form-urlencoded")
# The template prints ``{{ x|default:"-" }}`` (the birth date through ``date``).
_VALOR = Template('{{ valor|default:"-" }}')
_FECHA = Template('{{ valor|date:"d/m/Y"|default:"-" }}')
_PREVIEW = (
    "apellido",
    "nombre",
    "dni",
    "prefijo_cuil",
    "cuil_cuit",
    "sufijo_cuil",
    "sexo",
    "fecha_nacimiento",
    "edad",
)


def _preview(datos):
    return {
        clave: (_FECHA if clave == "fecha_nacimiento" else _VALOR).render(
            Context({"valor": datos.get(clave)})
        )
        for clave in _PREVIEW
    }


def _formulario(form):
    campos = {}
    for nombre in (
        "genero",
        "codigo_telefono",
        "numero_telefono",
        "fecha_alta",
        "fecha_baja",
    ):
        campo = form[nombre]
        campos[nombre] = {
            "label": str(campo.label),
            "required": campo.field.required,
            # The ``required`` attribute of the native widget (a Select without blank has none).
            "html_required": bool(
                campo.field.required
                and form.use_required_attribute
                and campo.field.widget.use_required_attribute(campo.initial)
            ),
            "value": _valor_de_campo(campo),
            "max_length": getattr(campo.field, "max_length", None),
        }
    campos["genero"]["choices"] = [
        {"value": str(valor), "label": str(etiqueta)}
        for valor, etiqueta in form.fields["genero"].choices
    ]
    actividades = form["actividades"]
    seleccionadas = {str(valor) for valor in (actividades.value() or [])}
    campos["actividades"] = {
        "label": str(actividades.label),
        "required": actividades.field.required,
        "choices": [
            {
                "value": str(valor),
                "label": str(etiqueta),
                "checked": str(valor) in seleccionadas,
            }
            for valor, etiqueta in actividades.field.choices
        ],
    }
    return {
        "fields": campos,
        "errors": form.errors.get_json_data() if form.is_bound else {},
    }


def _mensajes(request):
    """The flash messages of the native alert block (``alert-{{ message.tags }}``)."""
    return [
        {"message": str(mensaje), "tags": mensaje.tags}
        for mensaje in messages.get_messages(request)
    ]


def _pagina(contexto, request):
    comedor = contexto["object"]
    edicion = bool(contexto.get("edit_mode"))
    encontrado = contexto.get("ciudadano_encontrado")
    preview = contexto.get("preview_data")
    existente = bool(contexto.get("colaborador_existente"))
    consulta = contexto.get("query") or ""
    if encontrado:
        oculto = {"name": "ciudadano_id", "value": str(encontrado.id)}
    elif edicion:
        oculto = {
            "name": "ciudadano_id",
            "value": str(contexto["colaborador"].ciudadano_id),
        }
    else:
        oculto = {"name": "dni", "value": consulta}
    if edicion:
        origen = "edicion"
    elif encontrado:
        origen = "sisoc"
    else:
        origen = "renaper"
    return {
        "comedor": comedor_ref(comedor),
        "edit_mode": edicion,
        "query": consulta,
        "preview": _preview(preview) if preview else None,
        "source": origen if preview else None,
        "existing": existente,
        "not_found": bool(not preview and consulta),
        "hidden": oculto,
        "form": _formulario(contexto["form"]) if preview and not existente else None,
        "messages": _mensajes(request),
        "urls": {"comedor": reverse("comedor_detalle", args=[comedor.id])},
    }


class _ColaboradorWebView(NativeWebView):
    http_method_names = ["get", "post", "head"]
    native_class = None

    def get(self, request, **kwargs):
        vista = self.native(self.native_class, request, **kwargs)
        # The native dispatch: scope, creation veto, object lookup (404) and context.
        # pylint: disable-next=protected-access
        respuesta = vista.dispatch(request._request, **kwargs)
        return Response(_pagina(respuesta.context_data, request))

    def post(self, request, **kwargs):
        # ``Request.content_type`` keeps the multipart boundary; Django strips it.
        # pylint: disable-next=protected-access
        if request._request.content_type not in FORMATOS:
            return Response({"detail": "Formato de solicitud no admitido."}, status=415)
        vista = self.native(self.native_class, request, **kwargs)
        # pylint: disable-next=protected-access
        respuesta = vista.dispatch(request._request, **kwargs)
        if respuesta.status_code == 302:
            return Response({"ok": True, "redirect": respuesta["Location"]})
        return Response(_pagina(respuesta.context_data, request), status=400)


class ColaboradorCrearWebView(_ColaboradorWebView):
    """``/api/web/comedores/colaboradores/comedor/<pk>/crear/``."""

    permission_classes = [
        WebGatePermission,
        requires_any(["comedores.add_colaboradorespacio"]),
    ]
    native_class = ColaboradorEspacioCreateView


class ColaboradorEditarWebView(_ColaboradorWebView):
    """``/api/web/comedores/colaboradores/comedor/<pk>/<pk2>/editar/``."""

    permission_classes = [
        WebGatePermission,
        requires_any(["comedores.change_colaboradorespacio"]),
    ]
    native_class = ColaboradorEspacioUpdateView


class ColaboradorBajaWebView(NativeWebView):
    """``POST .../colaboradores/comedor/<pk>/<pk2>/eliminar/``: the native soft delete.

    The native route only accepts POST (the button lives in the comedor card); the
    service stamps ``fecha_baja`` and the audit, and a repeated request only answers
    its "ya se encuentra dado de baja" message.
    """

    permission_classes = [
        WebGatePermission,
        requires_any(["comedores.delete_colaboradorespacio"]),
    ]
    http_method_names = ["post"]

    def post(self, request, pk, pk2):
        vista = self.native(ColaboradorEspacioDeleteView, request, pk=pk, pk2=pk2)
        # pylint: disable-next=protected-access
        respuesta = vista.dispatch(request._request, pk=pk, pk2=pk2)
        return Response({"ok": True, "redirect": respuesta["Location"]})
