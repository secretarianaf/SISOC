"""Web API (G1 v1) of the complementary technical report page (AD02.02).

``GET .../informes/complementario/<tipo>/<pk>/`` runs the native
``InformeTecnicoComplementarioDetailView`` (``setup()``, queryset, ``get_context_data()``)
and projects its context to JSON, so it cannot drift from the HTML page; ``?origen=``
is read by the native view from the request. ``POST`` runs the native ``post()`` with
``{"values": {<field name>: <new value>}}`` as the ``campo_<name>`` form keys of the
template, so empty values, the rejection of an empty change set, the service that stores
the changes, the state transitions and the flash messages are the native ones.

Access is the native URL guard (kept access gaps included) plus the session CSRF check.
Outcomes of the POST: 200 ``{success: true, messages, redirect}``; 400 with the same body
and ``success: false`` when the native view rejected the change (nothing is stored);
404 for an unknown report.
"""

from django.http import Http404, QueryDict
from django.urls import reverse
from django.utils.formats import localize
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.web_gate import WebGatePermission
from admisiones.views.web_views import InformeTecnicoComplementarioDetailView
from admisiones.web_api_informe_acciones import post_request, queue_again
from admisiones.web_api_informes import VerInforme
from admisiones.web_api_templates import _native, pending_messages

ORIGEN = "acompanamiento"


def _campo(campo):
    return {
        "identificador": campo["identificador"],
        "nombre": str(campo["nombre"]),
        "valor": str(localize(campo["valor"])),
    }


def _grupo(grupo):
    base = {"titulo": str(grupo["titulo"]), "tipo": grupo["tipo"]}
    if grupo["tipo"] == "matriz":
        base["identificador"] = grupo["identificador"]
        base["filas"] = [
            {"titulo": fila["titulo"], "campos": [_campo(c) for c in fila["campos"]]}
            for fila in grupo["filas"]
        ]
    else:
        base["campos"] = [_campo(c) for c in grupo["campos"]]
    return base


def _urls(admision, informe, tipo, origen):
    """The links of the page: back, the breadcrumb and the action."""
    if origen:
        volver = (
            reverse("detalle_acompanamiento", args=[admision.comedor_id])
            + f"?admision_id={admision.pk}"
        )
    else:
        volver = reverse("admisiones_tecnicos_editar", args=[admision.pk])
    pagina = reverse(
        "informe_complementario_ver", kwargs={"tipo": tipo, "pk": informe.pk}
    )
    return {
        "volver": volver,
        "pagina": pagina + (f"?origen={ORIGEN}" if origen else ""),
        "accion": pagina,
    }


def _post_data(body):
    """The ``campo_<name>`` form keys of the template for the JSON ``values``."""
    values = body.get("values") if isinstance(body, dict) else None
    if not isinstance(values, dict) or not all(
        isinstance(v, str) for v in values.values()
    ):
        raise ParseError("values debe ser un objeto de textos.")
    datos = QueryDict(mutable=True)
    for nombre, valor in values.items():
        datos[f"campo_{nombre}"] = valor
    return datos


def _vista(request, tipo, pk):
    vista = _native(InformeTecnicoComplementarioDetailView, request, tipo=tipo, pk=pk)
    try:
        vista.object = vista.get_object()
    except Http404 as exc:
        raise NotFound() from exc
    return vista


class InformeComplementarioWebView(APIView):
    """``GET`` and ``POST`` of ``.../informes/complementario/<tipo>/<pk>/``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, VerInforme]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head", "post"]

    def get(self, request, tipo, pk):
        vista = _vista(request, tipo, pk)
        context = vista.get_context_data(object=vista.object)
        admision = vista.object.admision
        origen = bool(context.get("origen_acompanamiento"))
        return Response(
            {
                "id": vista.object.pk,
                "tipo": tipo,
                "comedor": admision.comedor.nombre,
                "origen_acompanamiento": origen,
                "observaciones_legales": context.get("observaciones_legales") or "",
                "grupos": [_grupo(g) for g in context["campos_agrupados"]],
                "campos_modificados": {
                    str(nombre): str(localize(valor))
                    for nombre, valor in (
                        context.get("campos_modificados_existentes") or {}
                    ).items()
                },
                "urls": _urls(admision, vista.object, tipo, origen),
                "messages": pending_messages(request),
            }
        )

    def post(self, request, tipo, pk):
        datos = _post_data(request.data)
        nativa = post_request(request, datos)
        vista = _vista(request, tipo, pk)
        vista.request = nativa
        respuesta = vista.post(nativa)
        mensajes = pending_messages(request)
        niveles = {m["level"] for m in mensajes}
        exito = "success" in niveles and "error" not in niveles
        queue_again(request, mensajes)
        pagina = _urls(
            vista.object.admision,
            vista.object,
            tipo,
            request.GET.get("origen") == ORIGEN,
        )["pagina"]
        return Response(
            {
                "success": exito,
                "messages": mensajes,
                "redirect": respuesta["Location"] if exito else pagina,
            },
            status=200 if exito else 400,
        )
