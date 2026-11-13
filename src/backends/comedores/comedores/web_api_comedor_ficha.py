"""Web API (G1 v1) of the comedor ficha (CO07.01): ``/api/web/comedores/comedores/<pk>/``.

The endpoint runs the native ``ComedorDetailView`` itself (``setup()``,
``get_object()`` with the user scope and ``get_context_data()``), so it cannot
drift from ``comedor_detail.html``; this module only projects that context to
JSON, one block of the template per key. After the web gate the native route
guard applies unchanged:
``permissions_any_required(["comedores.view_comedor", "admisiones.view_admision",
"acompanamientos.view_informacionrelevante"])`` and a comedor outside the user's
scope is a 404.

Blocks published so far (the contract grows by adding keys, never by renaming):

- ``header``: the ``app-header`` block (validar, convenio PNUD, actividades,
  acompañamiento territorial, historial, the «Acciones» menu and the convenio
  selector). Each action carries the flag the template checks, so a control the
  user cannot use is absent, not disabled.
- ``tablero``: timeline, summary boxes, age chart, admission / convenio card and
  card-holder card (``web_api_comedor_ficha_tablero``).
- ``acordeon``: the four panels (``web_api_comedor_ficha_datos``).
- ``titulo``: the title card (pending conformity notice, name, validation,
  program and estado badges, CARITAS and the execution dates).
- ``certificaciones`` and the other lower cards (``web_api_comedor_ficha_bloques``).

The ficha has no write here: its POSTs (admisión, descartar expediente) and the
modals stay native until their own units.
"""

from django.http import Http404
from django.template import Context, Template
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.templatetags.custom_filters import replace_query
from core.web_gate import WebGatePermission
from comedores.views.comedor import ComedorDetailView
from comedores.web_api_comedor_ficha_bloques import bloques
from comedores.web_api_comedor_ficha_datos import acordeon
from comedores.web_api_comedor_ficha_tablero import tablero
from comedores.web_api_comedores import VerComedores, pending_messages

PROGRAMAS = {2: "PAC", 3: "PNUD - SECOS", 4: "PNUD - TRADICIONAL"}
_PLAZO = Template('{% load custom_filters %}{{ informe|getattr:"plazo_ejecucion" }}')


class _WebView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, VerComedores]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]


def _native(view_class, request, **kwargs):
    view = view_class()
    view.setup(request._request, **kwargs)  # pylint: disable=protected-access
    return view


def _fecha(valor):
    return valor.strftime("%d/%m/%Y") if valor else None


def _convenio(admision, seleccionada_id, ruta):
    return {
        "id": admision.pk,
        "tipo": admision.get_tipo_display(),
        "creado": _fecha(admision.creado),
        "estado": (
            "-" if admision.estado_mostrar is None else str(admision.estado_mostrar)
        ),
        "vigente_pwa": bool(admision.vigente_pwa),
        "seleccionada": admision.pk == (seleccionada_id or 0),
        "url": replace_query(ruta, "admision_id", admision.pk),
    }


def _header(context, request, comedor):
    user = request.user
    pk = comedor.pk
    es_pnud = context["es_programa_pnud"]
    gestiona = context["puede_gestionar_actividades_espacio"]
    sin_ingreso = comedor.estado == "Sin Ingreso"
    acciones = {
        "editar": reverse("comedor_editar", args=[pk]),
        "responsable_tarjeta": (
            reverse("comedor_responsable_tarjeta_editar", args=[pk])
            if context["puede_gestionar_responsable_tarjeta"]
            else None
        ),
        "eliminar": reverse("comedor_eliminar", args=[pk]),
        "equipo_tecnico": (
            {
                "url": reverse("dupla_asignar", kwargs={"pk": pk}),
                "label": (
                    "Asignar Equipo Técnico"
                    if sin_ingreso
                    else "Modificar Equipo Técnico"
                ),
            }
            if user.has_perm("duplas.change_dupla")
            else None
        ),
        "comenzar_admision": not sin_ingreso,
    }
    ruta = request.get_full_path()
    return {
        "validar": bool(context["puede_validar_comedor"]),
        "convenio_pnud": (
            reverse("comedor_convenio_pnud", args=[pk])
            if context["usa_convenio_pnud"]
            else None
        ),
        "actividades": (
            {
                "url": (
                    reverse("actividad_espacio_pwa_crear", args=[pk])
                    if gestiona
                    else "#legajo-actividades-pnud"
                )
            }
            if es_pnud
            else None
        ),
        "acompanamiento_territorial": (
            reverse("relevamientos", args=[pk])
            if context["mostrar_relevamientos_header"]
            else None
        ),
        "historial": (
            reverse("audittrail:log_instance", args=["comedores", "comedor", pk])
            if user.has_perm("auditlog.view_logentry")
            else None
        ),
        "acciones": acciones,
        "convenios": [
            _convenio(a, context["selected_admision_id"], ruta)
            for a in context["admision"]
        ],
    }


def _titulo(context, comedor):
    pendiente = context["conformidad_prestacion_pendiente"]
    seleccionada = context["selected_admision"] or context.get("admision_activa")
    informe = context["admisiones_informetecnico"]
    return {
        "conformidad_pendiente": (
            {"periodo": pendiente["periodo"].strftime("%m/%Y")}
            if pendiente["pendiente"]
            else None
        ),
        "nombre": comedor.nombre,
        "validacion": comedor.estado_validacion,
        "programa": PROGRAMAS.get(comedor.programa_id, "Sin programa"),
        "etiqueta_estado": comedor.get_etiqueta_estado_display(),
        "es_caritas": bool(comedor.es_caritas),
        "inicio_ejecucion": _fecha(getattr(seleccionada, "creado", None)),
        "plazo_ejecucion": _PLAZO.render(Context({"informe": informe})).strip(),
    }


class ComedorFichaWebView(_WebView):
    """``GET /api/web/comedores/comedores/<pk>/``: the native ficha."""

    def get(self, request, pk):
        vista = _native(ComedorDetailView, request, pk=pk)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        context = vista.get_context_data(object=vista.object)
        comedor = vista.object
        return Response(
            {
                "id": comedor.pk,
                "nombre": comedor.nombre,
                "header": _header(context, request, comedor),
                "titulo": _titulo(context, comedor),
                "acordeon": acordeon(context, comedor),
                "tablero": tablero(context, comedor),
                **bloques(context, comedor, request.user),
                "messages": pending_messages(request),
            }
        )
