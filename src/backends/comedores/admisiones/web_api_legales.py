"""Web API (G1 v1) of the legal admision detail and its actions (AD03.03).

``GET /api/web/comedores/admisiones/legales/<pk>/`` runs the native
``AdmisionesLegalesDetailView`` (``setup()``, ``get_object()`` and
``get_context_data()``) and projects its context to JSON, so it cannot drift from the
HTML page: the same forms (with their widgets and initial values), the same buttons from
``LegalesService.get_botones_disponibles`` and the same paginated state history. The access
is exactly the native one: ``permissions_any_required`` with the technical permissions plus
``expedientespagos.view_expedientepago`` (superuser bypass included) and no per-object scope;
the admision is resolved by its global primary key.

``POST .../legales/<pk>/acciones/<accion>/`` runs one action. Each endpoint feeds the native
``LegalesService`` handler with a request whose POST holds only the whitelisted fields of that
action plus its own button key, so the native dispatch order cannot pick another action. The
messages the service queues are drained and returned in ``messages``; its redirect is dropped.
A form the native view would re-render with its modal open answers 400 with the bound form;
the sequence guard of the providence handlers (``_bloquear_fuera_de_secuencia``) answers 409
with the native text. Nothing else changes: the services keep their own transactions.

``GET``/``POST .../legales/<pk>/complementario/revision/`` serve the review page of the
complementary technical report (``InformeTecnicoComplementarioReviewView`` and
``LegalesService.revisar_informe_complementario``).
"""

import copy

from django import forms
from django.http import Http404, QueryDict
from django.template.defaultfilters import date as date_filter
from django.urls import reverse
from django.utils import timezone
from django.utils.datastructures import MultiValueDict
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

# The exact predicate of ``permissions_any_required``, the native URL guard.
from core.decorators import _has_any_permissions
from core.web_gate import WebGatePermission
from admisiones.services.legales_service.impl import LegalesService
from admisiones.views.web_views import (
    AdmisionesLegalesDetailView,
    InformeTecnicoComplementarioReviewView,
)
from admisiones.web_api_detalle import _paginado
from admisiones.web_api_informe_formulario import fields_payload
from admisiones.web_api_listas import LEGALES_PERMISSIONS
from admisiones.web_api_templates import _native, pending_messages

# One endpoint per action: the native POST key and the only fields it reads.
ACCIONES = {
    "rectificar": ("btnObservaciones", ("observaciones",)),
    "numero-expediente": (
        "btnLegalesNumIF",
        (
            "expediente_anio",
            "expediente_numero",
            "expediente_reparticion",
            "expediente_organismo",
        ),
    ),
    "proyecto-convenio": ("btnProyectoConvenio", ()),
    "if-proyecto-convenio": ("btnConvenioNumIF", ("numero_if",)),
    "primera-providencia": (
        "btnPrimeraProvidencia",
        ("cantidad_espacios", "caratula_causa", "juzgado", "memo"),
    ),
    "gde-pv-primera": (
        "btnGDEPVPrimera",
        ("pv_anio", "pv_numero", "pv_reparticion", "pv_organismo"),
    ),
    "segunda-providencia": (
        "btnSegundaProvidencia",
        ("pv_anio", "pv_numero", "pv_reparticion", "pv_organismo"),
    ),
    "gde-pv-segunda": (
        "btnGDEPVSegunda",
        ("pv_anio", "pv_numero", "pv_reparticion", "pv_organismo"),
    ),
    "intervencion-juridicos": (
        "BtnIntervencionJuridicos",
        ("intervencion_juridicos", "rechazo_juridicos_motivo", "dictamen_motivo"),
    ),
    "convenio": ("btnConvenio", ("numero_convenio",)),
    "reinicio-expediente": (
        "btnReinicioExpediente",
        ("observaciones_reinicio_expediente",),
    ),
    "solicitar-complementario": (
        "btnInformeComplementario",
        ("observaciones_informe_tecnico_complementario",),
    ),
    "if-complementario": ("btnIFInformeComplementario", ("numero_if_complementario",)),
    "validar-juridicos": ("ValidacionJuridicos", ()),
}
# The handlers that call ``_bloquear_fuera_de_secuencia``.
EN_SECUENCIA = frozenset(
    {
        "primera-providencia",
        "gde-pv-primera",
        "segunda-providencia",
        "gde-pv-segunda",
    }
)
ARCHIVOS = {"convenio": ("archivo_convenio",)}
# ``render_boton_legales``: label, modal and class of every button.
BOTONES = {
    "rectificar": ("Rectificar", "modalRectificar", "btn-warning"),
    "agregar_expediente": (
        "Agregar Número de expediente",
        "modalLegalesNumIF",
        "btn-primary",
    ),
    "formulario_convenio": (
        "Formulario Proyecto de Convenio",
        "modalFormConvenio",
        "btn-primary",
    ),
    "if_convenio": ("IF Proyecto de Convenio", "modalConvenioNumIF", "btn-primary"),
    "primera_providencia": (
        "Generar Primera Providencia",
        "modalPrimeraProvidencia",
        "btn-primary",
    ),
    "gde_pv_primera": (
        "Cargar número de GDE PV",
        "modalGDEPVPrimera",
        "btn-primary",
    ),
    "segunda_providencia": (
        "Generar Segunda Providencia",
        "modalSegundaProvidencia",
        "btn-primary",
    ),
    "gde_pv_segunda": (
        "Cargar número de GDE Segunda PV",
        "modalGDEPVSegunda",
        "btn-primary",
    ),
    "intervencion_juridicos": (
        "Intervención Jurídicos",
        "modalIntervencionJuridicos",
        "btn-primary",
    ),
    "informe_sga": ("Informe SGA", "modalInformeSGA", "btn-primary"),
    "convenio": ("Convenio", "modalConvenio", "btn-primary"),
    "reinicio_expediente": (
        "Reinicio de Expediente",
        "modalReinicioExpediente",
        "btn-danger",
    ),
    "informe_complementario": (
        "Solicitar Informe Técnico Complementario",
        "modalSolicitarInformeComplementario",
        "btn-primary",
    ),
    "revisar_informe_complementario": (
        "Revisar Informe Complementario",
        None,
        "btn-info",
    ),
    "if_informe_complementario": (
        "IF Informe Técnico Complementario",
        "modalIFInformeComplementario",
        "btn-primary",
    ),
}


class VerLegales(BasePermission):
    """The native ``permissions_any_required`` of ``admisiones_legales_ver``."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, LEGALES_PERMISSIONS)


def _sin_info(value, texto="Sin información"):
    """``{{ value|default_if_none:"Sin información" }}``."""
    return texto if value is None else str(value)


def _fecha(value, formato="d/m/Y"):
    """``{{ value|date:"d/m/Y" }}``."""
    return date_filter(value, formato)


def _url(archivo):
    return archivo.url if archivo else None


def _forms(form):
    """A native form: its effective fields (a file input is its own kind)."""
    campos = fields_payload(form)
    for campo in campos:
        if isinstance(form.fields[campo["name"]].widget, forms.FileInput):
            campo["kind"] = "file"
            campo["value"] = ""
    return {
        "fields": campos,
        "non_field_errors": [str(e) for e in form.non_field_errors()],
    }


def _providencia(providencia):
    if not providencia:
        return None
    return {
        "pdf": _url(providencia.archivo),
        "docx": _url(providencia.archivo_docx),
        "numero_gde_pv": providencia.numero_gde_pv or None,
    }


def _historial(request, context):
    cambios = context["historial_estados_cambios"]
    return {
        "headers": [
            {"title": str(h["title"]), "width": h.get("width")}
            for h in context["historial_estados_headers"]
        ],
        "rows": [[str(c["content"]) for c in item["cells"]] for item in cambios],
        "page": _paginado(
            request,
            context["historial_estados_page_obj"],
            context["historial_estados_page_param"],
        ),
    }


def _complementario(item):
    return {
        "fecha": _fecha(item.creado),
        "estado": str(item.get_estado_display()),
        "pdf": _url(item.pdf),
    }


def _botones(admision):
    botones = []
    for clave in LegalesService.get_botones_disponibles(admision):
        texto, modal, clase = BOTONES.get(clave, ("", "", "btn-primary"))
        botones.append(
            {
                "key": clave,
                "texto": texto,
                "modal": modal,
                "clase": clase,
                "url": (
                    reverse("revisar_informe_complementario", args=[admision.pk])
                    if modal is None
                    else None
                ),
            }
        )
    return botones


def _comedor(comedor):
    return {
        "id": comedor.pk,
        "nombre": comedor.nombre,
        "url": reverse("comedor_detalle", args=[comedor.pk]),
        "tipo": _sin_info(comedor.tipocomedor),
        "programa": _sin_info(comedor.programa),
        "organizacion": _sin_info(comedor.organizacion),
        "ubicacion": " - ".join(
            _sin_info(valor)
            for valor in (comedor.provincia, comedor.municipio, comedor.localidad)
        ),
        "calle": (
            f"{_sin_info(comedor.calle)} {_sin_info(comedor.numero)} - Piso: "
            f"{_sin_info(comedor.piso)} {'' if comedor.departamento is None else comedor.departamento}"
        ),
    }


def _expediente(admision, context):
    proyecto = context.get("formulario_proyecto")
    intervencion = admision.intervencion_juridicos
    dictamen = admision.dictamen_motivo
    return {
        "estado": _sin_info(admision.estado_legales),
        "numero": _sin_info(admision.legales_num_if),
        "proyecto": (
            {
                "pdf": _url(proyecto.archivo),
                "docx": _url(proyecto.archivo_docx),
                "numero_if": proyecto.numero_if or None,
            }
            if context.get("formulario_proyecto_completo")
            else None
        ),
        "primera_providencia": _providencia(context.get("primera_providencia")),
        "segunda_providencia": _providencia(context.get("segunda_providencia")),
        "intervencion": (
            {
                "label": str(admision.get_intervencion_juridicos_display()),
                "rechazo": (
                    str(admision.get_rechazo_juridicos_motivo_display())
                    if intervencion == "rechazado"
                    else None
                ),
            }
            if intervencion
            else None
        ),
        "dictamen": str(admision.get_dictamen_motivo_display()) if dictamen else None,
        "disposicion": (
            {
                "numero": str(admision.numero_disposicion),
                "archivo": _url(admision.archivo_disposicion),
            }
            if not dictamen and admision.numero_disposicion
            else None
        ),
        "convenio": (
            {
                "numero": str(admision.numero_convenio),
                "archivo": _url(admision.archivo_convenio),
            }
            if admision.numero_convenio
            else None
        ),
    }


def _admision_card(admision, context):
    informe = context.get("informe")
    final = context.get("pdf_complementario_final")
    return {
        "tipo": _sin_info(admision.get_tipo_display()),
        "tipo_convenio": (
            _sin_info(admision.tipo_convenio.nombre) if admision.tipo_convenio else ""
        ),
        "estado": _sin_info(admision.estado.nombre) if admision.estado else "",
        "fecha": _fecha(admision.creado),
        "vencimiento_mandatos": (
            _fecha(informe.fecha_vencimiento_mandatos)
            if informe and informe.fecha_vencimiento_mandatos
            else "-"
        ),
        "num_expediente": _sin_info(admision.num_expediente),
        "informe_pdf": context.get("pdf_url"),
        "complementarios": [
            _complementario(item) for item in context["informes_complementarios"]
        ],
        "complementario_final": (
            {
                "pdf": _url(final.archivo),
                "docx": _url(final.archivo_docx),
                "numero_if": final.numero_if or None,
            }
            if final
            else None
        ),
    }


def _titulo(admision):
    return {
        "num_expediente": str(admision.num_expediente),
        "archivada": bool(admision.enviada_a_archivo),
        "rechazo": str(admision.get_rechazo_juridicos_motivo_display()),
        "estado": (
            "Estado a definir"
            if admision.estado_legales is None
            else str(admision.estado_legales)
        ),
    }


class LegalesDetalleWebView(APIView):
    """``GET /api/web/comedores/admisiones/legales/<pk>/``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, VerLegales]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request, pk):
        vista = _native(AdmisionesLegalesDetailView, request, pk=pk)
        try:
            vista.object = vista.get_object()
            context = vista.get_context_data(object=vista.object)
        except Http404 as exc:
            raise NotFound() from exc
        admision = vista.object
        if not context.get("botones_disponibles") and "documentos" not in context:
            # ``get_legales_context`` failed and the native page renders empty.
            context = {
                **context,
                "documentos": [],
                "informes_complementarios": [],
                "historial_estados_cambios": [],
                "historial_estados_headers": [],
            }
        return Response(
            {
                "id": admision.pk,
                "titulo": _titulo(admision),
                "urls": {
                    "lista": reverse("admisiones_legales_listar"),
                    "pagina": reverse("admisiones_legales_ver", args=[admision.pk]),
                },
                "botones": _botones(admision),
                "expediente": _expediente(admision, context),
                "admision": _admision_card(admision, context),
                "comedor": _comedor(admision.comedor),
                "es_judicializado": bool(context.get("es_judicializado")),
                "tipo_admision": _sin_info(
                    admision.get_tipo_display(), "Sin información"
                ),
                "documentos": [
                    {
                        "id": doc["id"],
                        "nombre": str(doc["nombre"]),
                        "archivo_url": doc["archivo_url"],
                    }
                    for doc in context["documentos"]
                ],
                "historial_estados": _historial(request, context),
                "forms": {
                    "rectificar": _forms(context["form"]),
                    "numero_expediente": _forms(context["form_legales_num_if"]),
                    "primera_providencia": _forms(context["primera_providencia_form"]),
                    "segunda_providencia": _forms(context["segunda_providencia_form"]),
                    "gde_pv_primera": _forms(context["gde_pv_primera_form"]),
                    "gde_pv_segunda": _forms(context["gde_pv_segunda_form"]),
                    "intervencion_juridicos": _forms(
                        context["form_intervencion_juridicos"]
                    ),
                    "if_proyecto_convenio": _forms(context["convenio_num_if"]),
                    "convenio": _forms(context["form_convenio"]),
                    "reinicio_expediente": _forms(context["form_reinicio_expediente"]),
                    "solicitar_complementario": _forms(
                        context["form_solicitar_informe_complementario"]
                    ),
                },
                "messages": pending_messages(request),
            }
        )


def _post_request(request, campos, clave, archivos=()):
    """The native request of a POST holding only ``campos`` plus the action key."""
    base = request._request  # pylint: disable=protected-access
    datos = QueryDict(mutable=True)
    for campo in campos:
        valores = base.POST.getlist(campo)
        if valores:
            datos.setlist(campo, valores)
    datos[clave] = ""
    subidos = MultiValueDict()
    for campo in archivos:
        if campo in base.FILES:
            subidos[campo] = base.FILES[campo]
    clon = copy.copy(base)
    clon.method = "POST"
    clon.POST = datos
    clon._files = subidos  # pylint: disable=protected-access
    return clon


def _admision(request, pk):
    vista = _native(AdmisionesLegalesDetailView, request, pk=pk)
    try:
        return vista.get_object()
    except Http404 as exc:
        raise NotFound() from exc


def _resultado(request, admision, estado=200):
    admision.refresh_from_db()
    return Response(
        {
            "messages": pending_messages(request),
            "estado_legales": admision.estado_legales,
            "botones": _botones(admision),
        },
        status=estado,
    )


def _formulario_invalido(clon, admision, accion):
    """The forms the native ``post()`` re-renders with their modal open."""
    if accion == "numero-expediente":
        from admisiones.forms.admisiones_forms import LegalesNumIFForm

        form = LegalesNumIFForm(clon.POST, instance=admision)
        if not form.is_valid():
            return "numero_expediente", "modalLegalesNumIF", form
        return None
    modal = LegalesService.form_modal_invalido(clon, admision)
    if modal is None:
        return None
    clave, id_modal, form = modal
    return clave.replace("_form", ""), id_modal, form


class LegalesAccionWebView(APIView):
    """``POST /api/web/comedores/admisiones/legales/<pk>/acciones/<accion>/``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, VerLegales]
    renderer_classes = [JSONRenderer]
    http_method_names = ["post"]

    def post(self, request, pk, accion):
        if accion not in ACCIONES:
            raise NotFound()
        admision = _admision(request, pk)
        clave, campos = ACCIONES[accion]
        clon = _post_request(request, campos, clave, ARCHIVOS.get(accion, ()))
        invalido = _formulario_invalido(clon, admision, accion)
        if invalido is not None:
            nombre, modal, form = invalido
            return Response(
                {"form": nombre, "modal": modal, **_forms(form)}, status=400
            )
        LegalesService.procesar_post_legales(clon, admision)
        resultado = _resultado(request, admision)
        if accion in EN_SECUENCIA and any(
            m["level"] == "error" and m["message"].startswith("No se puede ")
            for m in resultado.data["messages"]
        ):
            resultado.status_code = 409
        return resultado


def _revision(context):
    informe = context.get("informe_complementario")
    if not informe:
        return None
    return {
        "estado": str(informe.get_estado_display()),
        "creado_por": informe.creado_por.username if informe.creado_por else "",
        "fecha": date_filter(timezone.localtime(informe.modificado), "d/m/Y H:i"),
        "campos": [
            {"campo": str(campo.campo), "value": str(campo.value)}
            for campo in context["campos_modificados"]
        ],
    }


class RevisionComplementarioWebView(APIView):
    """``GET``/``POST .../legales/<pk>/complementario/revision/``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, VerLegales]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head", "post"]

    def get(self, request, pk):
        vista = _native(InformeTecnicoComplementarioReviewView, request, pk=pk)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        admision = vista.object
        context = vista.get_context_data(object=admision)
        return Response(
            {
                "id": admision.pk,
                "comedor": admision.comedor.nombre,
                "urls": {
                    "legal": reverse("admisiones_legales_ver", args=[admision.pk])
                },
                "informe": _revision(context),
                "messages": pending_messages(request),
            }
        )

    def post(self, request, pk):
        admision = _admision(request, pk)
        clon = _post_request(
            request,
            ("accion_complementario", "observaciones_complementario"),
            "btnRevisarInformeComplementario",
        )
        LegalesService.revisar_informe_complementario(clon, admision)
        admision.refresh_from_db()
        # The native view redirects to the legal detail, which shows the queued flash
        # messages: they stay queued for that page instead of being drained here.
        return Response(
            {
                "redirect": reverse("admisiones_legales_ver", args=[admision.pk]),
                "estado_legales": admision.estado_legales,
            }
        )
