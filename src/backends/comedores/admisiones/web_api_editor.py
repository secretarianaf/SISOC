"""Web API (G1 v1) of the technical admision editor (AD03.02).

``GET /api/web/comedores/admisiones/<pk>/`` runs the native
``AdmisionesTecnicosUpdateView`` (``setup()``, ``get_object()`` and
``get_context_data()``) and projects its context to JSON, so it cannot drift from the
HTML page. ``POST /api/web/comedores/admisiones/<pk>/acciones/<accion>/`` runs the
native view's ``post()`` itself with the JSON or multipart body as its POST (the key of
the action is added, as the template's button does), so the dispatch, the services and
the flash messages are the native ones; nothing is validated or decided here. The access
is exactly the native one: the URL guard ``permissions_any_required`` and no per-object
scope (the admision is resolved by its global primary key). The gaps of the actions that
do not repeat the role or the origin state are kept (see the AD03 contract).

Outcomes of an action: 200 ``{success: true, message, level, messages, redirect}``;
400 with the same body and ``success: false`` when the native view answered with an
error message, plus ``fields`` and ``non_field_errors`` when it re-rendered an invalid
form; 403 when the native view answered 403; 404 for an unknown admision or action.
"""

import copy
from datetime import datetime

from django.http import Http404, HttpResponseRedirect, QueryDict
from django.template.defaultfilters import date as date_filter
from django.urls import reverse
from django.utils import timezone
from django.utils.datastructures import MultiValueDict
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.templatetags.custom_filters import has_any_group, has_any_perm, has_perm_code
from core.web_gate import WebGatePermission
from admisiones.forms.admisiones_forms import (
    CaratularForm,
    IFInformeTecnicoForm,
)
from admisiones.services.admisiones_service.impl import AdmisionService
from admisiones.templatetags.admisiones_tags import (
    puede_gestionar_documentacion_admision,
    render_boton_tecnicos,
)
from admisiones.views.web_views import AdmisionesTecnicosUpdateView
from admisiones.web_api_detalle import VerAdmision
from admisiones.web_api_informe_formulario import fields_payload
from admisiones.web_api_listas import TECNICOS_PERMISSIONS
from admisiones.web_api_templates import _native, pending_messages

ACCIONES = {
    "derivar-legales": "mandarLegales",
    "if-informe-tecnico": "btnIFInformeTecnico",
    "comenzar-acompanamiento": "btnDisponibilizarAcomp",
    "rectificar-documentacion": "btnRectificarDocumentacion",
    "finalizar-carga-documentacion": "btnFinalizarCargaDocumentacion",
    "caratular": "btnCaratulacion",
    "confirmar-tipo-convenio": "confirmar_tipo_convenio",
    "validaciones-template": "guardar_validaciones_template",
    "subir-docx-final": "subir_docx_final",
}
SIN_INFO = "Sin información"
# States of the admision in which the template hides the delete button of a file.
ESTADOS_SIN_ELIMINAR = {
    "descartado",
    "informe_tecnico_finalizado",
    "informe_tecnico_docx_editado",
    "informe_tecnico_en_revision",
    "informe_tecnico_en_subsanacion",
    "informe_tecnico_aprobado",
    "if_informe_tecnico_cargado",
    "enviado_a_legales",
    "enviado_a_acompaniamiento",
}
PERMISOS_LECTURA = ",".join(TECNICOS_PERMISSIONS)


def _fecha(value, formato="d/m/Y"):
    """``{{ value|date:"d/m/Y" }}`` (the template localizes aware datetimes)."""
    if not value:
        return ""
    if isinstance(value, datetime) and timezone.is_aware(value):
        value = timezone.localtime(value)
    return date_filter(value, formato)


def _sin_info(value):
    """``{{ value|default_if_none:"Sin información" }}``."""
    return SIN_INFO if value is None else str(value)


def usa_formulario_embebido(user, admision, informe):
    """True when the native page draws the embedded report and cover form."""
    tipo = getattr(admision, "tipo_informe", None)
    return bool(
        tipo and AdmisionService.puede_editar_informe_tecnico(user, admision, informe)
    )


def _rol(user):
    """The role checks of ``documento_row.html`` and ``gde_cell.html``."""
    tecnico = has_perm_code(user, "auth.role_tecnico_comedor") or has_any_group(
        user, "Tecnico Comedor"
    )
    lectura = has_any_perm(user, PERMISOS_LECTURA)
    return {
        "abogado": has_perm_code(user, "auth.role_abogado_dupla"),
        "ve_a_validar": lectura or tecnico,
        "gestiona": bool(puede_gestionar_documentacion_admision(user)),
        "edita_gde": bool(user.is_superuser or lectura or tecnico),
    }


def _badge(estado):
    if estado == "Rectificar":
        return "bg-danger"
    if estado == "Aceptado":
        return "bg-success"
    if estado in ("Pendiente", "Documento adjunto"):
        return "bg-secondary"
    return "bg-primary"


def _opcion(valor, seleccionada=False, deshabilitada=False):
    return {
        "value": valor,
        "label": valor,
        "selected": seleccionada,
        "disabled": deshabilitada,
    }


def _select_abogado():
    return {
        "kind": "select",
        "requires_observacion": True,
        "border": "border border-2 border-primary",
        "options": [
            _opcion("A Validar Abogado", True),
            _opcion("Aceptado"),
            _opcion("Rectificar"),
        ],
    }


def _select_tecnico(estado, valor):
    opciones = []
    if estado == "Rectificar":
        opciones.append(_opcion("Rectificar", True, True))
    opciones.append(
        _opcion(
            "Documento adjunto",
            valor == "Documento adjunto",
            valor == "Documento adjunto",
        )
    )
    opciones.append(_opcion("A Validar Abogado", valor == "A Validar Abogado"))
    return {
        "kind": "select",
        "requires_observacion": False,
        "border": "border border-danger border-2" if estado == "Rectificar" else "",
        "options": opciones,
    }


def _estado_ui(doc, rol):
    """The state cell of ``documento_row.html``."""
    estado, archivo_id = doc["estado"], doc.get("archivo_id")
    if estado == "Aceptado":
        ui = {"kind": "badge", "badge": "bg-success"}
    elif estado == "Pendiente":
        ui = {"kind": "badge", "badge": "bg-secondary"}
    elif estado == "A Validar Abogado":
        if rol["abogado"] and archivo_id:
            ui = _select_abogado()
        elif rol["ve_a_validar"]:
            ui = {"kind": "badge", "badge": "bg-primary"}
        else:
            ui = {"kind": "text"}
    elif archivo_id and rol["gestiona"]:
        ui = _select_tecnico(estado, doc.get("estado_valor"))
    else:
        ui = {"kind": "badge", "badge": _badge(estado)}
    return ui


def _gde_ui(doc, rol):
    """The GDE cell (``includes/gde_cell.html``)."""
    numero = doc.get("numero_gde")
    if doc["estado"] != "Aceptado":
        return {"kind": "plain"}
    if doc.get("es_origen_organizacion"):
        return {"kind": "organizacion"}
    if doc.get("archivo_id") and rol["edita_gde"]:
        return {"kind": "editable", "value": numero}
    return {"kind": "plain"}


def _documento(doc, admision, rol, adjuntable):
    organizacion = doc.get("origen") == "organizacion"
    archivo_url = doc.get("archivo_url")
    puede_eliminar = (
        bool(archivo_url)
        and not organizacion
        and not admision.enviada_a_archivo
        and admision.estado_admision not in ESTADOS_SIN_ELIMINAR
        and rol["gestiona"]
    )
    puede_adjuntar = (
        not archivo_url
        and not organizacion
        and not doc.get("es_personalizado")
        and not admision.enviada_a_archivo
        and admision.estado_admision != "descartado"
        and rol["gestiona"]
        and adjuntable
    )
    vencimiento = doc.get("fecha_vencimiento")
    return {
        "id": str(doc["id"]),
        "row_id": str(doc["row_id"]),
        "documentacion_id": doc.get("documentacion_id"),
        "archivo_id": doc.get("archivo_id"),
        "nombre": str(doc["nombre"]),
        "obligatorio": bool(doc.get("obligatorio")),
        "organizacion": organizacion,
        "vencimiento": _fecha(vencimiento) if organizacion and vencimiento else None,
        "estado": str(doc["estado"]),
        "estado_valor": doc.get("estado_valor") or "",
        "estado_ui": _estado_ui(doc, rol),
        "archivo_url": archivo_url or None,
        "puede_eliminar": puede_eliminar,
        "puede_adjuntar": puede_adjuntar,
        "gde": _gde_ui(doc, rol),
        "numero_gde": doc.get("numero_gde") or "",
        "personalizado": bool(doc.get("es_personalizado")),
        "observaciones": doc.get("observaciones") or None,
    }


def _boton(clave, admision, informe):
    config = render_boton_tecnicos(clave, admision, informe)
    url = None
    if config["url"]:
        tipo = getattr(informe, "tipo", None)
        if clave == "crear_informe_tecnico":
            url = reverse(
                "informe_tecnico_crear",
                kwargs={"tipo": admision.tipo_informe, "admision_id": admision.pk},
            )
        else:
            nombres = {
                "editar_informe_tecnico": "informe_tecnico_editar",
                "ver_informe_tecnico": "informe_tecnico_ver",
                "descargar_informe_tecnico_gde": "informe_tecnico_descargar_para_gde",
                "informe_tecnico_complementario": "informe_complementario_ver",
            }
            if clave in nombres and informe is not None:
                url = reverse(nombres[clave], kwargs={"tipo": tipo, "pk": informe.pk})
    return {
        "clave": clave,
        "texto": config["texto"],
        "clase": config["clase"],
        "modal": config["modal"].lstrip("#") or None,
        "url": url,
    }


def _resync(context):
    if not context.get("mostrar_modal_resync_org"):
        return None
    desincronizada = bool(context.get("admision_desincronizada"))
    desactualizada = bool(context.get("documentacion_desactualizada"))
    return {
        "desincronizada": desincronizada,
        "documentacion_desactualizada": desactualizada,
        "solo_datos_organizacion": not (desincronizada or desactualizada),
        "tipo_entidad_actual": str(
            context.get("tipo_entidad_actual_organizacion") or ""
        )
        or SIN_INFO,
        "tipo_entidad_snapshot": str(context.get("tipo_entidad_origen_snapshot") or "")
        or SIN_INFO,
        "documentos_modificados": [
            str(e) for e in context.get("documentos_org_modificados") or []
        ],
        "datos_modificados": [
            str(e) for e in context.get("datos_organizacion_modificados") or []
        ],
    }


def _seleccion_convenio(admision, context):
    if admision.tipo_convenio_id or admision.enviada_a_archivo:
        return None
    comedor = context.get("comedor")
    organizacion = getattr(comedor, "organizacion", None)
    precargado = context.get("tipo_convenio_precargado")
    return {
        "tipo_entidad": str(getattr(organizacion, "tipo_entidad", None) or SIN_INFO),
        "tipo_convenio": str(getattr(precargado, "nombre", None) or SIN_INFO),
        "precargado": bool(precargado),
        "tipo": admision.tipo,
    }


def _validaciones(admision, context):
    if not admision.tipo_convenio_id:
        return None
    editable = bool(context.get("puede_editar_validaciones_template"))
    nombres = (
        ["es_ex_pnud", "estado_convenio_pnud"]
        if admision.tipo == "incorporacion"
        else (
            [
                "tipo_renovacion",
                "estado_financiamiento",
                "informe_complementario_modifica_prestaciones",
            ]
            if admision.tipo == "renovacion"
            else []
        )
    )
    if editable:
        todos = {
            f["name"]: f for f in fields_payload(context["validaciones_template_form"])
        }
        return {"editable": True, "fields": [todos[n] for n in nombres]}
    valores = []
    if admision.tipo == "incorporacion":
        valores = [
            ["¿Es Ex PNUD?", admision.get_es_ex_pnud_display() or "-"],
            [
                "Estado del convenio PNUD",
                admision.get_estado_convenio_pnud_display() or "No aplica",
            ],
        ]
    elif admision.tipo == "renovacion":
        valores = [
            ["Renovación que tramita", admision.get_tipo_renovacion_display() or "-"],
            [
                "Estado del financiamiento",
                admision.get_estado_financiamiento_display() or "-",
            ],
            [
                "Informe Complementario - Modificación de Prestaciones",
                admision.get_informe_complementario_modifica_prestaciones_display()
                or "-",
            ],
        ]
    return {"editable": False, "valores": valores}


def _comedor(comedor):
    def campo(nombre):
        return _sin_info(getattr(comedor, nombre, None))

    return {
        "id": comedor.pk if comedor else None,
        "nombre": comedor.nombre if comedor else "",
        "tipocomedor": campo("tipocomedor"),
        "programa": campo("programa"),
        "organizacion": campo("organizacion"),
        "provincia": campo("provincia"),
        "municipio": campo("municipio"),
        "localidad": campo("localidad"),
        "calle": campo("calle"),
        "numero": campo("numero"),
        "piso": campo("piso"),
        "departamento": (
            ""
            if getattr(comedor, "departamento", None) is None
            else str(comedor.departamento)
        ),
    }


def _pdf(pdf):
    if not pdf:
        return None
    return {
        "archivo": pdf.archivo.url if pdf.archivo else None,
        "docx": pdf.archivo_docx.url if pdf.archivo_docx else None,
        "docx_editado": (
            pdf.archivo_docx_editado.url if pdf.archivo_docx_editado else None
        ),
    }


def _banner(admision):
    if not admision.enviada_a_archivo:
        return None
    if admision.estado and admision.estado.nombre == "Descartado":
        return f"DESCARTADO: {admision.motivo_descarte_expediente}"
    return f"RECHAZADO: {admision.get_rechazo_juridicos_motivo_display()}"


def _modales(admision, context, informe):
    """Forms of the modals: the IF report and the cover."""
    form_if = context.get("form_if_informe_tecnico") or IFInformeTecnicoForm(
        instance=admision
    )
    caratular = context.get("caratular_form") or CaratularForm(instance=admision)
    return {
        "if_informe": [
            f for f in fields_payload(form_if) if f["name"] == "numero_if_tecnico"
        ],
        "if_informe_archivo": {
            "id": form_if["archivo_informe_tecnico_GDE"].id_for_label,
            "label": str(form_if["archivo_informe_tecnico_GDE"].label),
        },
        "caratular": fields_payload(caratular),
        "informe_id": informe.pk if informe else None,
    }


def projection(request, context, admision, pk):
    """The JSON of the editor, from the native context."""
    user = request.user
    comedor = context.get("comedor")
    informe = context.get("informe_tecnico")
    rol = _rol(user)
    adjuntable = (
        not admision.enviada_a_archivo and admision.estado_admision != "descartado"
    )
    stats = context.get("stats") or {}
    lectura = has_any_perm(user, PERMISOS_LECTURA)
    return {
        "id": admision.pk,
        "vacio": not context.get("comedor"),
        "comedor": _comedor(comedor),
        "banner": _banner(admision),
        "urls": {
            "listar": reverse("admisiones_tecnicos_listar"),
            "comedor": (
                reverse("comedor_detalle", args=[comedor.pk]) if comedor else None
            ),
            "pagina": reverse("admisiones_tecnicos_editar", args=[pk]),
            "localidades": reverse("ajax_load_localidades"),
            "agregar_documento": reverse("documento_personalizado_crear", args=[pk]),
            "resync": reverse("admision_resync_convenio", args=[pk]),
        },
        "botones": [
            _boton(c, admision, informe)
            for c in context.get("botones_disponibles") or []
        ],
        "resync": _resync(context),
        "complementario_requerido": (
            {
                "observaciones": context.get(
                    "observaciones_informe_tecnico_complementario"
                )
                or ""
            }
            if context.get("informe_complementario_requerido")
            else None
        ),
        "informe_a_subsanar": (
            informe.observaciones_subsanacion
            if informe and informe.observaciones_subsanacion and lectura
            else None
        ),
        "seleccion_convenio": _seleccion_convenio(admision, context),
        "admision": {
            "tipo": admision.tipo,
            # ``admision.tipo_convenio.nombre|default_if_none`` renders empty without a type.
            "tipo_convenio": (
                admision.tipo_convenio.nombre if admision.tipo_convenio else ""
            ),
            "convenio_numero": admision.convenio_numero,
            "vigente_pwa": bool(admision.vigente_pwa),
            "personas_conveniadas_nomina": admision.personas_conveniadas_nomina,
            "tipo_display": _sin_info(admision.get_tipo_display()),
            "estado_proceso": admision.get_estado_admision_display(),
            "fecha": _fecha(admision.creado),
            "vencimiento_mandatos": (
                _fecha(informe.fecha_vencimiento_mandatos)
                if informe and informe.fecha_vencimiento_mandatos
                else "-"
            ),
            "num_expediente": admision.num_expediente or None,
            "enviado_legales": bool(admision.enviado_legales),
            "informe_estado": informe.estado if informe else None,
            "numero_if_tecnico": admision.numero_if_tecnico or None,
            "informe_gde": (
                admision.archivo_informe_tecnico_GDE.url
                if admision.archivo_informe_tecnico_GDE
                else None
            ),
            "estado_legales": admision.estado_legales or "",
            "observaciones": admision.observaciones or "",
        },
        "puede_editar_convenio_numero": bool(
            context.get("puede_editar_convenio_numero")
        ),
        "mostrar_personas_conveniadas_nomina": bool(
            context.get("mostrar_personas_conveniadas_nomina")
        ),
        "puede_editar_personas_conveniadas_nomina": bool(
            context.get("puede_editar_personas_conveniadas_nomina")
        ),
        "puede_editar_num_expediente": bool(context.get("puede_editar_num_expediente")),
        "pdf": _pdf(context.get("pdf")),
        "complementarios": [
            {
                "pdf": i.pdf.url if i.pdf else None,
                "fecha": _fecha(i.creado),
                "estado": i.get_estado_display(),
            }
            for i in context.get("informes_complementarios") or []
        ],
        "validaciones": _validaciones(admision, context),
        "stats": {
            "obligatorios_completos": stats.get("obligatorios_completos"),
            "obligatorios_total": stats.get("obligatorios_total"),
            "aceptados": stats.get("aceptados"),
            "a_validar_abogado": stats.get("a_validar_abogado"),
            "rectificar": stats.get("rectificar"),
            "pendientes": stats.get("pendientes"),
        },
        "documentos": [
            _documento(d, admision, rol, adjuntable)
            for d in context.get("documentos") or []
        ],
        "documentos_personalizados": [
            _documento(d, admision, rol, adjuntable)
            for d in context.get("documentos_personalizados") or []
        ],
        "puede_agregar_documento": bool(adjuntable and rol["gestiona"]),
        "modales": _modales(admision, context, informe),
        "informe_embebido": usa_formulario_embebido(user, admision, informe),
        "messages": pending_messages(request),
    }


class EditorWebView(APIView):
    """``GET /api/web/comedores/admisiones/<pk>/``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, VerAdmision]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request, pk):
        vista = _native(AdmisionesTecnicosUpdateView, request, pk=pk)
        try:
            vista.object = vista.get_object()
            context = vista.get_context_data(object=vista.object)
        except Http404 as exc:
            raise NotFound() from exc
        return Response(projection(request, context, vista.object, pk))


def _post_data(request, clave):
    """Form-encoded view of the body, with the key of the action."""
    data = QueryDict(mutable=True)
    cuerpo = request.data
    if hasattr(cuerpo, "items"):
        for nombre, valor in cuerpo.items():
            if valor is True:
                data[nombre] = "on"
            elif isinstance(valor, (str, int, float)) and valor is not False:
                data[nombre] = str(valor)
    data[clave] = "1"
    return data


def _errores(response):
    contexto = getattr(response, "context_data", None) or {}
    formulario = contexto.get("caratular_form")
    if formulario is None:
        return {}
    return {
        "fields": fields_payload(formulario),
        "non_field_errors": list(formulario.non_field_errors()),
    }


class EditorAccionWebView(APIView):
    """``POST /api/web/comedores/admisiones/<pk>/acciones/<accion>/``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, VerAdmision]
    renderer_classes = [JSONRenderer]
    http_method_names = ["post"]

    def post(self, request, pk, accion):
        clave = ACCIONES.get(accion)
        if clave is None:
            raise NotFound()
        post_request = copy.copy(request._request)  # pylint: disable=protected-access
        post_request.method = "POST"
        post_request.POST = _post_data(request, clave)
        post_request._files = (  # pylint: disable=protected-access
            request.FILES if request.FILES else MultiValueDict()
        )
        vista = AdmisionesTecnicosUpdateView()
        vista.setup(post_request, pk=pk)
        try:
            vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        vista.object = vista.get_object()
        # The dispatcher of the native ``post()`` for the buttons of the page. The generic
        # ``UpdateView.post`` it falls back to (gap 5 of the contract) is not exposed.
        if accion == "subir-docx-final":
            respuesta = (
                vista._handle_docx_final_post(  # pylint: disable=protected-access
                    post_request
                )
            )
        else:
            respuesta = (
                vista._handle_post_update_actions(  # pylint: disable=protected-access
                    post_request, vista.object
                )
            )
        if respuesta is None:
            return Response(
                {
                    "success": False,
                    "message": "Error inesperado.",
                    "level": "error",
                    "messages": pending_messages(request),
                    "redirect": reverse("admisiones_tecnicos_editar", args=[pk]),
                },
                status=400,
            )
        if respuesta.status_code == 403:
            return Response({"success": False, "message": ""}, status=403)
        mensajes = pending_messages(request)
        error = any(m["level"] == "error" for m in mensajes)
        cuerpo = {
            "success": isinstance(respuesta, HttpResponseRedirect) and not error,
            "message": mensajes[-1]["message"] if mensajes else "",
            "level": mensajes[-1]["level"] if mensajes else "info",
            "messages": mensajes,
            "redirect": reverse("admisiones_tecnicos_editar", args=[pk]),
        }
        if cuerpo["success"]:
            return Response(cuerpo)
        cuerpo.update(_errores(respuesta))
        return Response(cuerpo, status=400)
