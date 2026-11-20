"""Web API (G1 v1) of the admision detail page (AD03.01).

``GET /api/web/comedores/admisiones/<comedor_pk>/<pk>/detalle/`` runs the native
``AdmisionDetailView`` (``setup()``, ``get_object()`` and ``get_context_data()``)
and projects its context to JSON, so it cannot drift from the HTML page. The
access is exactly the native one: the URL guard ``permissions_any_required``
(``comedores.view_comedor``, ``admisiones.view_admision`` or
``acompanamientos.view_informacionrelevante``, superuser bypass included) and no
per-object scope; the admision is resolved by its global primary key and only the
``comedor_pk`` must match, otherwise 404. The «Forzar cierre» POST, the inline
edits and the additional-file upload keep posting to their native endpoints in
this unit; this module is read-only.

Dates and numbers go through the same Django filters as the template.
"""

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.template.defaultfilters import date as date_filter
from django.urls import reverse
from django.utils.http import urlencode
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

# The exact predicate of ``permissions_any_required``, the native URL guard.
from core.decorators import _has_any_permissions
from core.pagination import build_compact_page_range
from core.web_gate import WebGatePermission
from admisiones.views.web_views import AdmisionDetailView
from admisiones.web_api_listas import TECNICOS_PERMISSIONS
from admisiones.web_api_templates import _native, pending_messages

COORDINADOR = "Coordinador Equipo Tecnico"


class VerAdmision(BasePermission):
    """The native ``permissions_any_required`` of ``admision_detalle``."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, TECNICOS_PERMISSIONS)


def _text(value):
    """``{{ value|default:"-" }}``."""
    return str(value) if value else "-"


def _fecha(value, formato="d/m/Y"):
    """``{{ value|date:"d/m/Y"|default:"-" }}``."""
    return date_filter(value, formato) or "-"


def _usuario(usuario):
    """``usuario.get_full_name|default:usuario.username|default:"-"``."""
    if not usuario:
        return "-"
    return usuario.get_full_name() or usuario.username or "-"


def _enlace(archivo):
    return archivo.url if archivo else None


def _documento(doc, obligatorio):
    return {
        "nombre": str(doc.get("nombre") or ""),
        "obligatorio": obligatorio,
        "estado": _text(doc.get("estado")),
        "numero_gde": _text(doc.get("numero_gde")),
        "archivo_url": doc.get("archivo_url") or None,
    }


def _informe(informe):
    if not informe:
        return None
    return {
        "expediente": _text(informe.expediente_nro),
        "nota_gde_if": _text(informe.nota_gde_if),
        "if_relevamiento": _text(informe.if_relevamiento),
        "vencimiento_mandatos": _fecha(informe.fecha_vencimiento_mandatos),
        "estado_formulario": _text(informe.estado_formulario),
        "tipo": _text(informe.get_tipo_display()),
        "responsable_nombre": _text(informe.responsable_tarjeta_nombre),
        "responsable_cuit": _text(informe.responsable_tarjeta_cuit),
    }


def _informe_enlaces(informe, pdf):
    """The download buttons of the report, with the template's conditions.

    ``me_2`` is the template's ``me-2`` class: it marks the first button of a
    pair, but the Word button of the non-validated branch never carries it.
    """
    if not informe or not pdf:
        return None
    docx = _enlace(pdf.archivo_docx)
    if informe.estado == "Validado":
        if pdf.archivo_docx_editado:
            return [
                {
                    "label": "Descargar Informe SISOC Final",
                    "tone": "success",
                    "me_2": True,
                    "url": pdf.archivo_docx_editado.url,
                }
            ]
        if docx:
            return [
                {
                    "label": "Descargar Word",
                    "tone": "outline-primary",
                    "me_2": True,
                    "url": docx,
                }
            ]
        return []
    enlaces = []
    if pdf.archivo:
        enlaces.append(
            {
                "label": "Descargar PDF",
                "tone": "outline-primary",
                "me_2": True,
                "url": pdf.archivo.url,
            }
        )
    if docx:
        enlaces.append(
            {
                "label": "Descargar Word",
                "tone": "outline-primary",
                "me_2": False,
                "url": docx,
            }
        )
    return enlaces


def _complementario(item):
    try:
        final = item.pdf_final
    except ObjectDoesNotExist:
        final = None
    return {
        "fecha": _fecha(item.creado),
        "estado": _text(item.get_estado_display()),
        "observaciones": _text(item.observaciones_legales),
        "pdf": _enlace(item.pdf),
        "pdf_final": _enlace(final.archivo) if final else None,
        "word_final": _enlace(final.archivo_docx) if final else None,
    }


def _paginado(request, page, param):
    previous = page.previous_page_number() if page.has_previous() else None
    siguiente = page.next_page_number() if page.has_next() else None
    otros = [(k, v) for k, v in request.GET.items() if k not in (param, "busqueda")]
    return {
        "is_paginated": page.has_other_pages(),
        "number": page.number,
        "count": page.paginator.count,
        "has_rows": len(page.object_list) > 0,
        "previous": previous,
        "next": siguiente,
        "range": [
            "…" if numero in ("...", "…") else numero
            for numero in build_compact_page_range(page)
        ],
        "param": param,
        "query_without_page": urlencode(otros) + "&" if otros else "",
    }


def _rendicion_final(context):
    final = context.get("rendicion_final")
    if not final:
        return None
    return {
        "fisicamente_presentada": bool(final.fisicamente_presentada),
        "documentos": [
            {
                "tipo": _text(getattr(doc.tipo, "nombre", "")),
                "estado": _text(getattr(doc.estado, "nombre", "")),
                "observaciones": _text(doc.observaciones),
                "actualizacion": _fecha(doc.fecha_modificacion, "d/m/Y H:i"),
                "archivo": _enlace(doc.documento),
            }
            for doc in context["rendicion_final_documentos"]
        ],
        "historial": [
            {
                "fecha": date_filter(item.fecha, "d/m/Y H:i"),
                "usuario": _usuario(item.usuario),
                "accion": str(item.accion),
            }
            for item in context["rendicion_final_historial"]
        ],
    }


def _acompanamiento(context, comedor):
    info = context.get("acompanamiento_info")
    return {
        "expediente": _text(info.expediente_nro) if info else "-",
        "disposicion": _text(context.get("acompanamiento_numero_disposicion")),
        "if_relevamiento": _text(info.if_relevamiento) if info else "-",
        "vencimiento": _fecha(info.fecha_vencimiento_mandatos) if info else "-",
        "codigo_proyecto": _text(comedor.codigo_de_proyecto),
        "if_asociados": _text(context.get("acompanamiento_numero_if")),
        "dias": [str(dia) for dia in context.get("dias_semana", [])],
        "prestaciones_por_dia": [
            {
                "tipo": str(fila.get("tipo", "")),
                "valores": [
                    _text(fila.get(str(dia).lower())) for dia in context["dias_semana"]
                ],
            }
            for fila in context.get("prestaciones_por_dia", [])
        ],
        "totales": (
            [
                {"tipo": str(t.get("tipo", "")), "cantidad": _text(t.get("cantidad"))}
                for t in context.get("prestaciones_dias", [])
            ]
            if context.get("prestaciones_por_dia")
            else []
        ),
    }


class AdmisionDetailWebView(APIView):
    """``GET /api/web/comedores/admisiones/<comedor_pk>/<pk>/detalle/``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, VerAdmision]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request, comedor_pk, pk):
        vista = _native(AdmisionDetailView, request, comedor_pk=comedor_pk, pk=pk)
        try:
            vista.object = vista.get_object()
            context = vista.get_context_data(object=vista.object)
        except Http404 as exc:
            raise NotFound() from exc
        admision = vista.object
        comedor = admision.comedor
        user = request.user
        dupla = context.get("dupla")
        coordinador = user.is_superuser or user.groups.filter(name=COORDINADOR).exists()
        informe = context.get("informe_tecnico")
        pdf = context.get("informe_tecnico_pdf")
        cierre = admision.motivo_descarte_expediente or admision.motivo_forzar_cierre
        return Response(
            {
                "id": admision.pk,
                "activa": bool(admision.activa),
                "comedor": {"id": comedor.pk, "nombre": comedor.nombre},
                "urls": {
                    "comedores": reverse("comedores"),
                    "comedor": reverse("comedor_detalle", args=[comedor.pk]),
                    "pagina": reverse(
                        "admision_detalle", kwargs={"comedor_pk": comedor.pk, "pk": pk}
                    ),
                },
                "puede_forzar_cierre": bool(admision.activa and coordinador),
                "admision": {
                    "creado": _fecha(admision.creado),
                    "tipo": _text(admision.get_tipo_display()),
                    "tipo_convenio": _text(
                        admision.tipo_convenio.nombre if admision.tipo_convenio else ""
                    ),
                    "convenio_numero": admision.convenio_numero,
                    "vigente_pwa": bool(admision.vigente_pwa),
                    "estado_actual": _text(admision.estado_mostrar),
                    "fecha_estado": _fecha(admision.fecha_estado_mostrar),
                    "estado_legales": _text(admision.get_estado_legales_display()),
                    "enviado_legales": bool(admision.enviado_legales),
                    "enviado_acompaniamiento": bool(admision.enviado_acompaniamiento),
                    "num_expediente": admision.num_expediente or None,
                    "fecha_cierre": (
                        _fecha(admision.modificado, "d/m/Y")
                        if not admision.activa
                        else None
                    ),
                    "motivo_cierre": _text(cierre),
                },
                "puede_editar_convenio_numero": bool(
                    context["puede_editar_convenio_numero"]
                ),
                "puede_editar_num_expediente": bool(
                    context["puede_editar_num_expediente"]
                ),
                "num_expediente_bloqueo": context["num_expediente_edit_locked_reason"],
                "dupla": (
                    {
                        "nombre": str(dupla.nombre),
                        "estado": str(dupla.estado),
                        "abogado": _usuario(context.get("dupla_abogado")),
                        "tecnicos": context["dupla_tecnicos"],
                    }
                    if dupla
                    else None
                ),
                "documentos": [
                    _documento(doc, bool(doc.get("obligatorio")))
                    for doc in context["documentos"]
                ],
                "documentos_personalizados": [
                    _documento(doc, False)
                    for doc in context["documentos_personalizados"]
                ],
                "informe_tecnico": _informe(informe),
                "informe_enlaces": _informe_enlaces(informe, pdf),
                "informe_gde": (
                    {
                        "numero": _text(admision.numero_if_tecnico),
                        "archivo": _enlace(admision.archivo_informe_tecnico_GDE),
                    }
                    if admision.numero_if_tecnico
                    or admision.archivo_informe_tecnico_GDE
                    else None
                ),
                "complementarios": [
                    _complementario(item)
                    for item in context["informes_complementarios"]
                ],
                "historial_estados": {
                    "headers": [
                        str(h["title"]) for h in context["historial_estados_headers"]
                    ],
                    "rows": [
                        [str(c["content"]) for c in item["cells"]]
                        for item in context["historial_estados_items"]
                    ],
                    "page": _paginado(
                        request,
                        context["historial_estados_page_obj"],
                        context["historial_estados_page_param"],
                    ),
                },
                "acompanamiento": _acompanamiento(context, comedor),
                "expedientes_pagos": [
                    {
                        "expediente": _text(e.expediente_pago),
                        "convenio": _text(e.expediente_convenio),
                        "if_prestaciones": _text(e.if_cantidad_de_prestaciones),
                        "monto": _text(e.monto),
                        "orden_pago": _text(e.numero_orden_pago),
                        "fecha_banco": _fecha(e.fecha_pago_al_banco),
                        "fecha_acreditacion": _fecha(e.fecha_acreditacion),
                        "url": reverse("expedientespagos_detail", args=[e.pk]),
                    }
                    for e in context["expedientes_pagos"]
                ],
                "rendiciones_mensuales": [
                    {
                        "mes": _text(r.get_mes_display()),
                        "anio": _text(r.anio),
                        "documento_adjunto": bool(r.documento_adjunto),
                        "observaciones": _text(r.observaciones),
                        "url": reverse("rendicioncuentasmensual_detail", args=[r.pk]),
                    }
                    for r in context["rendiciones_mensuales"]
                ],
                "rendicion_final": _rendicion_final(context),
                "messages": pending_messages(request),
            }
        )
