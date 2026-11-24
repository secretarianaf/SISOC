"""Web API (G1 v1) of the organization rendiciones (O04).

``GET .../organizaciones/<id>/rendiciones/<pk>/`` runs the native
``OrganizacionRendicionDetailView`` (non-deleted rendición of a project or of a
non-deleted comedor of the organization, organization visible by dupla: 404
otherwise). Access is today's: any of ``ORGANIZACION_DOCUMENTACION_PERMS``.
The PDF download (O04.02) has no API of its own: React calls the job endpoints
of ``rendicioncuentasmensual``, which owns it, exactly as the native script
does; this API only says whether the button is shown and where those
endpoints are. The legajo rendiciones table and its project filter
(``legajo/rendiciones_tabla.html``, ``legajo/filtro_proyecto.html``) are
delivered as sections (``web_api_secciones``).
"""

from django.template.defaultfilters import date as formato_fecha
from django.urls import reverse
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.web_gate import WebGatePermission
from gestion_organizaciones.views import OrganizacionRendicionDetailView
from gestion_organizaciones.web_api import OrganizacionListAccess
from gestion_organizaciones.web_api_secciones import seccion

VER_RENDICION = "rendicioncuentasmensual.view_rendicioncuentamensual"


def _periodo(rendicion):
    """The period cell of the legajo table and the detail page."""
    if rendicion.periodo_inicio and rendicion.periodo_fin:
        return (
            f"{formato_fecha(rendicion.periodo_inicio, 'd/m/Y')} al "
            f"{formato_fecha(rendicion.periodo_fin, 'd/m/Y')}"
        )
    return f"{rendicion.get_mes_display()} {rendicion.anio}"


def _fecha_hora(valor):
    """``|date:"d/m/Y H:i"|default:"-"`` (aware values are shown in local time)."""
    if not valor:
        return "-"
    if timezone.is_aware(valor):
        valor = timezone.localtime(valor)
    return formato_fecha(valor, "d/m/Y H:i")


def _si_no(valor):
    return "Sí" if valor else "No"


def _codigo_proyecto(rendicion):
    if rendicion.proyecto:
        return rendicion.proyecto.codigo
    comedor = rendicion.comedor
    return (comedor.codigo_de_proyecto if comedor else None) or "-"


@seccion("organizaciones/partials/legajo/rendiciones_tabla.html")
def seccion_rendiciones(contexto):
    """``legajo/rendiciones_tabla.html``: the presented rendiciones of a selection."""
    organizacion = contexto["organizacion"]
    return {
        "kind": "rendiciones",
        "show_line": bool(contexto.get("mostrar_linea")),
        "rows": [
            {
                "id": rendicion.pk,
                "line": rendicion.linea_programatica or None,
                "line_label": (
                    rendicion.get_linea_programatica_display()
                    if rendicion.linea_programatica
                    else None
                ),
                "project": _codigo_proyecto(rendicion),
                "convenio": rendicion.convenio or "-",
                "number": str(rendicion.numero_rendicion or "-"),
                "period": _periodo(rendicion),
                "territorial": bool(rendicion.validacion_territorial_finalizada),
                "audit": bool(rendicion.validacion_auditoria_finalizada),
                "validated": bool(rendicion.validada),
                "audited": bool(rendicion.auditada),
                "url": reverse(
                    "organizacion_rendicion_detalle",
                    args=[organizacion.pk, rendicion.pk],
                ),
            }
            for rendicion in contexto.get("rendiciones") or []
        ],
    }


@seccion("organizaciones/partials/legajo/filtro_proyecto.html")
def seccion_filtro_proyecto(contexto):
    """``legajo/filtro_proyecto.html``: the project-code filter of the rendiciones."""
    programa = contexto.get("programa")
    return {
        "kind": "rendiciones_filtro",
        "codes": list(contexto.get("codigos_rendiciones") or []),
        "selected": contexto.get("proyecto_rendiciones") or "",
        "program_id": programa.pk if programa else None,
    }


class RendicionDetalleWebView(APIView):
    """``GET .../<id>/rendiciones/<pk>/``: ``organizacion_rendicion_detail.html``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, OrganizacionListAccess]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request, pk, rendicion_id):
        vista = OrganizacionRendicionDetailView()
        vista.setup(
            request._request,  # pylint: disable=protected-access
            organizacion_id=pk,
            pk=rendicion_id,
        )
        vista.object = vista.get_object()
        contexto = vista.get_context_data()
        rendicion, organizacion = vista.object, contexto["organizacion"]
        puede_ver = request.user.has_perm(VER_RENDICION)
        validada = bool(rendicion.validada)
        return Response(
            {
                "id": rendicion.pk,
                "number": rendicion.numero_rendicion or rendicion.pk,
                "organization": {"id": organizacion.pk, "name": organizacion.nombre},
                "project_code": contexto["codigo_proyecto"] or "-",
                "convenio": rendicion.convenio or "-",
                "number_text": str(rendicion.numero_rendicion or "-"),
                "period": _periodo(rendicion),
                "process": (
                    f"{rendicion.get_etapa_proceso_display()} — "
                    f"{rendicion.get_subestado_proceso_display()}"
                ),
                "territorial": _si_no(rendicion.validacion_territorial_finalizada),
                "territorial_date": _fecha_hora(rendicion.fecha_validacion_territorial),
                "audit": _si_no(rendicion.validacion_auditoria_finalizada),
                "audit_date": _fecha_hora(rendicion.fecha_validacion_auditoria),
                "validated": _si_no(validada),
                "validated_date": (
                    _fecha_hora(
                        rendicion.fecha_gestion_auditoria
                        or rendicion.fecha_carga_auditoria
                    )
                    if validada
                    else "-"
                ),
                "audited": _si_no(rendicion.auditada),
                "audited_date": _fecha_hora(rendicion.fecha_auditada),
                "audit_record_url": (
                    rendicion.acta_auditoria.url if rendicion.acta_auditoria else None
                ),
                "regularized": _si_no(rendicion.regularizada),
                "regularized_date": _fecha_hora(rendicion.fecha_regularizacion),
                "complementary_record_url": (
                    rendicion.documento_regularizacion.url
                    if rendicion.documento_regularizacion
                    else None
                ),
                "can_view_rendicion": puede_ver,
                "can_download_pdf": bool(
                    puede_ver and rendicion.validacion_auditoria_finalizada
                ),
                "urls": {
                    "rendicion": reverse(
                        "rendicioncuentasmensual_detail", args=[rendicion.pk]
                    ),
                    "pdf_request": reverse(
                        "rendicioncuentasmensual_download_pdf_solicitar",
                        args=[rendicion.pk],
                    ),
                    "pdf_status": reverse(
                        "rendicioncuentasmensual_download_pdf_estado",
                        args=[rendicion.pk],
                    ),
                },
            }
        )
