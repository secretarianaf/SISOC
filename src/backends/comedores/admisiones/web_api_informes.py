"""Web API (G1 v1) of the technical-report detail page (AD02.01).

``GET /api/web/comedores/admisiones/informes/<tipo>/<pk>/`` runs the native
``InformeTecnicoDetailView`` (``setup()``, queryset, ``get_context_data()``) and
projects its context to JSON, so it cannot drift from the HTML page. The access
is exactly the native one: the URL guard ``permissions_any_required`` with
``comedores.view_comedor``, ``admisiones.view_admision`` or
``acompanamientos.view_informacionrelevante`` (superuser bypass included) and no
per-object scope. Every action of the page (upload the edited DOCX, review the
report) keeps posting to the native URL, whose own rules are unchanged; the DOCX
and PDF files are generated and stored by the backend as today.
"""

from django.http import Http404
from django.urls import reverse
from django.utils.formats import localize
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

# The exact predicate of ``permissions_any_required``, the native URL guard.
from core.decorators import _has_any_permissions
from core.web_gate import WebGatePermission
from admisiones.views.web_views import InformeTecnicoDetailView
from admisiones.web_api_templates import _native, pending_messages

INFORME_VIEW_PERMISSIONS = [
    "comedores.view_comedor",
    "admisiones.view_admision",
    "acompanamientos.view_informacionrelevante",
]


class VerInforme(BasePermission):
    """The native ``permissions_any_required`` of ``informe_tecnico_ver``."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, INFORME_VIEW_PERMISSIONS)


def _file_url(field):
    return field.url if field else None


def _archivos(context, estado, revisor):
    """The download links of the page, resolved with the template's conditions."""
    pdf = context.get("pdf")
    borrador = context.get("pdf_borrador")
    docx = _file_url(borrador.archivo_docx) if borrador else None
    editado = _file_url(borrador.archivo_docx_editado) if borrador else None
    ver_editado = revisor and estado == "Docx editado"
    # The ``elif pdf_borrador`` branch, shown only when there is no final PDF.
    if pdf or not borrador:
        enlace = None
    elif editado and not ver_editado:
        enlace = {"kind": "docx_editado", "url": editado}
    elif not editado and docx:
        enlace = {"kind": "docx_final", "url": docx}
    else:
        enlace = None
    return {
        "docx_descargar": docx if revisor and estado == "Docx generado" else None,
        "docx_editado_ver": editado if ver_editado else None,
        "pdf_final": _file_url(pdf.archivo) if pdf else None,
        "borrador": enlace,
    }


class InformeDetailWebView(APIView):
    """``GET /api/web/comedores/admisiones/informes/<tipo>/<pk>/``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, VerInforme]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request, tipo, pk):
        vista = _native(InformeTecnicoDetailView, request, tipo=tipo, pk=pk)
        try:
            informe = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        vista.object = informe
        context = vista.get_context_data(object=informe)
        admision = informe.admision
        estado = informe.estado
        # ``has_any_perm ... or is_superuser`` of the template, behind the URL guard.
        revisor = _has_any_permissions(request.user, INFORME_VIEW_PERMISSIONS)
        return Response(
            {
                "id": informe.pk,
                "tipo": tipo,
                "estado": estado,
                "comedor": admision.comedor.nombre,
                "observaciones_subsanacion": informe.observaciones_subsanacion or "",
                "campos": [
                    {"nombre": str(nombre), "valor": str(localize(valor))}
                    for nombre, valor in context.get("campos", [])
                ],
                "archivos": _archivos(context, estado, revisor),
                "puede_cambiar_estado": revisor
                and estado not in ("Validado", "Docx generado"),
                "puede_subsanar": revisor and estado != "Validado",
                "urls": {
                    "admision": reverse(
                        "admisiones_tecnicos_editar", args=[admision.pk]
                    ),
                    "accion": reverse(
                        "informe_tecnico_ver", kwargs={"tipo": tipo, "pk": informe.pk}
                    ),
                },
                "messages": pending_messages(request),
            }
        )
