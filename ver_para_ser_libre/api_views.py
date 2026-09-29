"""JSON boundary for the VPSL React client.

Authorization and province scoping remain server side. Existing workflows and
ModelForms remain the source of truth for writes.
"""

import json

from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request as DRFRequest
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    inline_serializer,
)

from core.models import Provincia
from iam.services import user_has_permission_code
from ver_para_ser_libre.forms import ItinerarioVPSLForm
from ver_para_ser_libre.models import (
    CasoLaboratorioVPSL,
    CierreDiarioVPSL,
    EstadoEvaluacionVPSL,
    EstadoItinerario,
    ItinerarioVPSL,
    JornadaVPSL,
    SedeVPSL,
)
from ver_para_ser_libre.services import workflow
from ver_para_ser_libre import api_workflow
from ver_para_ser_libre.api_serializers import (
    ActionResultSerializer,
    DeletePreviewSerializer,
    RenaperSerializer,
    RegistroPageSerializer,
    LaboratorioPageSerializer,
    FormSchemaSerializer,
    ItinerarioPageSerializer,
    ItinerarioSerializer,
    JornadaSerializer,
    LocationPreviewSerializer,
    OptionsSerializer,
    SedePageSerializer,
    SedeSerializer,
    SessionSerializer,
)
from ver_para_ser_libre.api_inputs import FORM_INPUT, ItinerarioInput, ActionInput
from ver_para_ser_libre.api_requests import django_request
from ver_para_ser_libre.services.access import (
    CREATE_ANY_PROVINCE_PERMISSION,
    filtrar_itinerarios_por_usuario,
    filtrar_jornadas_por_usuario,
    provincia_usuario_provincial,
)


def _error(message, status):
    return JsonResponse({"detail": message}, status=status)


class VpslPageNumberPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 200


def _paginated(request, queryset, serialize, *, page_size=10, extra=None):
    pagination = VpslPageNumberPagination()
    pagination.page_size = page_size
    rows = pagination.paginate_queryset(queryset, DRFRequest(request))
    payload = {
        "count": pagination.page.paginator.count,
        "next": pagination.get_next_link(),
        "previous": pagination.get_previous_link(),
        "results": [serialize(item) for item in rows],
    }
    if extra:
        payload.update(extra)
    return JsonResponse(payload)


def _authorize(request, permission):
    if not request.user.is_authenticated:
        return _error("Iniciá sesión en SISOC para continuar.", 401)
    if not user_has_permission_code(request.user, permission):
        return _error("No tenés permiso para esta operación.", 403)
    return None


def _authorize_any(request, permissions):
    if not request.user.is_authenticated:
        return _error("Iniciá sesión en SISOC para continuar.", 401)
    if not any(
        user_has_permission_code(request.user, permission) for permission in permissions
    ):
        return _error("No tenés permiso para esta operación.", 403)
    return None


ITINERARIO_VIEW_PERMISSIONS = (
    "ver_para_ser_libre.view_itinerariovpsl",
    "ver_para_ser_libre.view_all_itinerarios_vpsl",
    CREATE_ANY_PROVINCE_PERMISSION,
)
ITINERARIO_CREATE_PERMISSIONS = (
    "ver_para_ser_libre.add_itinerariovpsl",
    CREATE_ANY_PROVINCE_PERMISSION,
)


def _itinerario(item):
    return {
        "id": item.pk,
        "codigo": item.codigo,
        "provincia": item.provincia.nombre,
        "estado": item.estado,
        "estado_label": item.get_estado_display(),
        "fecha_inicio": item.fecha_inicio.isoformat(),
        "fecha_fin": item.fecha_fin.isoformat(),
        "referente_telefono": item.referente_telefono,
        "referente": " ".join(
            filter(None, [item.referente_nombre, item.referente_apellido])
        ),
        "referente_email": item.referente_email,
        "localidades": item.localidades_tentativas,
        "observaciones": item.observaciones,
        "jornadas_total": getattr(item, "jornadas_total", None),
    }


def _jornada(item):
    return {
        "id": item.pk,
        "itinerario_id": item.itinerario_id,
        "fecha": item.fecha.isoformat(),
        "sede": item.sede,
        "localidad": item.localidad_display,
        "ubicacion_url": item.ubicacion_url,
        "mapa_query": item.mapa_query,
        "latitud": str(item.latitud) if item.latitud is not None else "",
        "longitud": str(item.longitud) if item.longitud is not None else "",
        "vehiculos": [vehicle.nombre for vehicle in item.vehiculos.all()],
        "direccion": item.direccion,
        "estado": item.estado,
        "estado_label": item.get_estado_display(),
        "referente_telefono": item.referente_telefono,
        "referente": " ".join(
            filter(None, [item.referente_nombre, item.referente_apellido])
        ),
        "equipo_asignado": item.equipo_asignado,
        "observaciones": item.observaciones,
        "registros_total": getattr(item, "registros_total", None),
    }


def _sede(item):
    return {
        "id": item.pk,
        "nombre": item.nombre,
        "cueanexo": item.cueanexo,
        "jurisdiccion": item.jurisdiccion,
        "localidad": item.localidad,
        "domicilio": item.domicilio,
        "telefono": item.telefono,
        "mail": item.mail,
        "checklist_aprobado": item.checklist_aprobado,
        "mapa_query": item.mapa_query,
    }


@ensure_csrf_cookie
@require_GET
def session(request):
    if not request.user.is_authenticated:
        return _error("Iniciá sesión en SISOC para continuar.", 401)
    return JsonResponse(
        {
            "username": request.user.get_username(),
            "can_view_itinerarios": any(
                user_has_permission_code(request.user, permission)
                for permission in ITINERARIO_VIEW_PERMISSIONS
            ),
            "can_add_itinerarios": any(
                user_has_permission_code(request.user, permission)
                for permission in ITINERARIO_CREATE_PERMISSIONS
            )
            and bool(
                provincia_usuario_provincial(request.user)
                or user_has_permission_code(
                    request.user, CREATE_ANY_PROVINCE_PERMISSION
                )
            ),
            "can_view_sedes": user_has_permission_code(
                request.user, "ver_para_ser_libre.view_sedevpsl"
            ),
            "can_export": user_has_permission_code(
                request.user, "auth.role_exportar_a_csv"
            ),
            "permissions": {
                code: user_has_permission_code(
                    request.user, f"ver_para_ser_libre.{code}"
                )
                for code in (
                    "add_sedevpsl",
                    "change_sedevpsl",
                    "delete_sedevpsl",
                    "change_itinerariovpsl",
                    "delete_itinerariovpsl",
                    "add_jornadavpsl",
                    "view_jornadavpsl",
                    "change_jornadavpsl",
                    "delete_jornadavpsl",
                    "add_checklistjornadavpsl",
                    "add_registronominalvpsl",
                    "change_registronominalvpsl",
                    "delete_registronominalvpsl",
                    "change_casolaboratoriovpsl",
                    "add_cierrediariovpsl",
                )
            },
        }
    )


@require_GET
def options(request):
    denied = _authorize_any(request, ITINERARIO_CREATE_PERMISSIONS)
    if denied:
        return denied
    global_create = user_has_permission_code(
        request.user, CREATE_ANY_PROVINCE_PERMISSION
    )
    assigned = provincia_usuario_provincial(request.user)
    provinces = (
        Provincia.objects.order_by("nombre")
        if global_create
        else (
            Provincia.objects.filter(pk=assigned.pk)
            if assigned
            else Provincia.objects.none()
        )
    )
    return JsonResponse(
        {
            "provincias": [
                {"id": province.pk, "nombre": province.nombre} for province in provinces
            ],
        }
    )


@require_http_methods(["GET", "POST"])
def itinerarios(request):
    denied = _authorize_any(
        request,
        (
            ITINERARIO_CREATE_PERMISSIONS
            if request.method == "POST"
            else ITINERARIO_VIEW_PERMISSIONS
        ),
    )
    if denied:
        return denied
    if request.method == "POST":
        global_create = user_has_permission_code(
            request.user, CREATE_ANY_PROVINCE_PERMISSION
        )
        provincia = provincia_usuario_provincial(request.user)
        if not provincia and not global_create:
            return _error(
                "Necesitás una provincia asignada para crear itinerarios.", 403
            )
        form = ItinerarioVPSLForm(
            request.POST,
            request.FILES,
            **({} if global_create else {"provincia_bloqueada": provincia}),
        )
        if not form.is_valid():
            return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
        item = form.save(commit=False)
        if not global_create:
            item.provincia = provincia
        item.creado_por = request.user
        item.modificado_por = request.user
        item.save()
        form.save_m2m()
        return JsonResponse(_itinerario(item), status=201)

    queryset = filtrar_itinerarios_por_usuario(
        ItinerarioVPSL.objects.select_related("provincia")
        .annotate(jornadas_total=Count("jornadas", distinct=True))
        .order_by("-fecha_inicio", "-pk"),
        request.user,
    )
    search = (request.GET.get("q") or "").strip()[:100]
    if search:
        queryset = queryset.filter(
            Q(codigo__icontains=search)
            | Q(provincia__nombre__icontains=search)
            | Q(referente_nombre__icontains=search)
            | Q(referente_apellido__icontains=search)
        )
    state = (request.GET.get("estado") or "").strip()
    if state:
        queryset = queryset.filter(estado=state)
    return _paginated(
        request,
        queryset,
        _itinerario,
        extra={
            "estados": [
                {"value": value, "label": label}
                for value, label in EstadoItinerario.choices
            ]
        },
    )


@require_GET
def itinerario_detail(request, pk):
    denied = _authorize_any(request, ITINERARIO_VIEW_PERMISSIONS)
    if denied:
        return denied
    item = (
        filtrar_itinerarios_por_usuario(
            ItinerarioVPSL.objects.select_related("provincia"),
            request.user,
        )
        .filter(pk=pk)
        .first()
    )
    if item is None:
        return _error("Itinerario no encontrado.", 404)
    data = _itinerario(item)
    jornadas = (
        item.jornadas.annotate(registros_total=Count("registros", distinct=True))
        .prefetch_related("vehiculos")
        .order_by("fecha", "pk")
    )
    data["jornadas"] = [_jornada(jornada) for jornada in jornadas]
    data["carta_archivo_estado"] = item.carta_archivo_estado
    data["carta_referencia_estado"] = item.carta_referencia_estado
    data["carta_archivo_url"] = item.carta_archivo.url if item.carta_archivo else ""
    data["carta_referencia"] = item.carta_referencia
    data["subsanacion_observaciones"] = item.subsanacion_observaciones
    data["estados_evaluacion"] = [
        {"value": value, "label": label}
        for value, label in EstadoEvaluacionVPSL.choices
    ]
    return JsonResponse(data)


def _registro_data(entry):
    return {
        "id": entry.pk,
        "dni": entry.dni,
        "nombre": entry.nombre,
        "apellido": entry.apellido,
        "numero_acta": entry.numero_acta,
        "resultado": entry.get_resultado_display(),
        "cantidad_lentes": entry.cantidad_lentes,
        "graduacion_izquierda": (
            str(entry.graduacion_izquierda)
            if entry.graduacion_izquierda is not None
            else ""
        ),
        "graduacion_derecha": (
            str(entry.graduacion_derecha)
            if entry.graduacion_derecha is not None
            else ""
        ),
    }


def _laboratorio_data(caso):
    return {
        "id": caso.pk,
        "registro_id": caso.registro_id,
        "persona": f"{caso.registro.apellido}, {caso.registro.nombre}",
        "estado": caso.get_estado_display(),
        "siguiente": workflow.siguiente_estado_laboratorio(caso),
        "historial": [
            {
                "fecha": record.fecha.isoformat(),
                "antes": record.estado_anterior,
                "despues": record.estado_nuevo,
                "responsable": record.responsable,
            }
            for record in caso.historial.all()
        ],
    }


@require_GET
def jornada_detail(request, pk):
    denied = _authorize(request, "ver_para_ser_libre.view_jornadavpsl")
    if denied:
        return denied
    item = (
        filtrar_jornadas_por_usuario(
            JornadaVPSL.objects.select_related("itinerario").prefetch_related(
                "vehiculos"
            ),
            request.user,
        )
        .annotate(registros_total=Count("registros", distinct=True))
        .filter(pk=pk)
        .first()
    )
    if item is None:
        return _error("Jornada no encontrada.", 404)
    data = _jornada(item)
    data["checklist"] = [
        {
            "item": entry.item,
            "descripcion": entry.descripcion,
            "cumple": entry.cumple,
            "observacion": entry.observacion,
            "evidencia_url": entry.evidencia.url if entry.evidencia else "",
            "historial": [
                {
                    "fecha": record.created_at.isoformat(),
                    "antes": record.cumple_anterior,
                    "despues": record.cumple_nuevo,
                    "observacion": record.observacion_nueva,
                    "responsable": str(record.usuario) if record.usuario else "",
                }
                for record in entry.historial.all()
            ],
        }
        for entry in item.checklist.all()
    ]
    try:
        cierre = item.cierre
    except CierreDiarioVPSL.DoesNotExist:
        cierre = None
    data["cierre"] = (
        {
            "id": cierre.pk,
            "consistente": cierre.consistente,
            "responsable": cierre.responsable_cierre,
            "atenciones": cierre.cantidad_atenciones_registradas,
            "lentes": cierre.cantidad_lentes_entregados_dia,
            "casos": cierre.cantidad_casos_laboratorio_reportados,
            "observaciones": cierre.observaciones,
            "acta_adjunta_url": cierre.acta_adjunta.url if cierre.acta_adjunta else "",
            "historial": [
                {
                    "fecha": record.created_at.isoformat(),
                    "responsable": record.responsable,
                    "atenciones": record.cantidad_atenciones_registradas,
                    "lentes": record.cantidad_lentes_entregados_dia,
                    "casos": record.cantidad_casos_laboratorio_reportados,
                    "acta_adjunta_url": (
                        record.acta_adjunta.url if record.acta_adjunta else ""
                    ),
                }
                for record in cierre.historial_subsanaciones.all()
            ],
        }
        if cierre
        else None
    )
    return JsonResponse(data)


@require_GET
def sedes(request):
    denied = _authorize(request, "ver_para_ser_libre.view_sedevpsl")
    if denied:
        return denied
    queryset = SedeVPSL.objects.order_by("jurisdiccion", "localidad", "nombre")
    search = (request.GET.get("q") or "").strip()[:100]
    if search:
        queryset = queryset.filter(
            Q(nombre__icontains=search)
            | Q(cueanexo__icontains=search)
            | Q(localidad__icontains=search)
            | Q(jurisdiccion__icontains=search)
        )
    return _paginated(request, queryset, _sede, page_size=15)


@require_GET
def sede_detail(request, pk):
    denied = _authorize(request, "ver_para_ser_libre.view_sedevpsl")
    if denied:
        return denied
    item = SedeVPSL.objects.filter(pk=pk).first()
    if item is None:
        return _error("Sede no encontrada.", 404)
    return JsonResponse(_sede(item))


def _drf_response(legacy):
    """Keep existing domain writes while exposing the standard DRF error shape."""
    if not legacy.get("Content-Type", "").startswith("application/json"):
        return legacy
    data = json.loads(legacy.content)
    if legacy.status_code >= 400:
        if "errors" in data:
            data = {
                field: [error["message"] for error in errors]
                for field, errors in data["errors"].items()
            }
        else:
            data = {
                "detail": data.get("detail")
                or data.get("error")
                or data.get("message")
                or "Error"
            }
    response = Response(data, status=legacy.status_code)
    for cookie in legacy.cookies.values():
        response.cookies[cookie.key] = cookie.value
        for attribute in cookie.keys():
            response.cookies[cookie.key][attribute] = cookie[attribute]
    if legacy.has_header("Retry-After"):
        response["Retry-After"] = legacy["Retry-After"]
    return response


@extend_schema(tags=["vpsl"], responses=SessionSerializer)
@api_view(["GET"])
def rest_session(request):
    return _drf_response(session(django_request(request)))


@extend_schema(tags=["vpsl"], responses=OptionsSerializer)
@api_view(["GET"])
def rest_options(request):
    return _drf_response(options(django_request(request)))


@extend_schema(
    tags=["vpsl"],
    parameters=[
        OpenApiParameter("page", int),
        OpenApiParameter("page_size", int),
        OpenApiParameter("q", str),
        OpenApiParameter("estado", str),
    ],
)
@extend_schema(
    methods=["GET"],
    operation_id="vpsl_itinerarios_list",
    responses=ItinerarioPageSerializer,
)
@extend_schema(
    methods=["POST"],
    operation_id="vpsl_itinerarios_create",
    request=ItinerarioInput,
    responses={201: ItinerarioSerializer},
)
@api_view(["GET", "POST"])
def rest_itinerarios(request):
    return _drf_response(itinerarios(django_request(request)))


@extend_schema(
    tags=["vpsl"], operation_id="vpsl_itinerario_detail", responses=ItinerarioSerializer
)
@api_view(["GET"])
def rest_itinerario_detail(request, pk):
    return _drf_response(itinerario_detail(django_request(request), pk))


@extend_schema(tags=["vpsl"], responses=JornadaSerializer)
@api_view(["GET"])
def rest_jornada_detail(request, pk):
    return _drf_response(jornada_detail(django_request(request), pk))


@extend_schema(
    tags=["vpsl"],
    operation_id="vpsl_sedes",
    parameters=[
        OpenApiParameter("page", int),
        OpenApiParameter("page_size", int),
        OpenApiParameter("q", str),
    ],
    responses=SedePageSerializer,
)
@api_view(["GET"])
def rest_sedes(request):
    return _drf_response(sedes(django_request(request)))


@extend_schema(tags=["vpsl"], operation_id="vpsl_sede_detail", responses=SedeSerializer)
@api_view(["GET"])
def rest_sede_detail(request, pk):
    return _drf_response(sede_detail(django_request(request), pk))


@extend_schema(tags=["vpsl"], methods=["GET"], responses=FormSchemaSerializer)
@extend_schema(
    tags=["vpsl"],
    methods=["POST"],
    request=FORM_INPUT,
    responses=ActionResultSerializer,
)
@api_view(["GET", "POST"])
def rest_form(request, kind, pk):
    return _drf_response(api_workflow.workflow_form(django_request(request), kind, pk))


@extend_schema(
    tags=["vpsl"],
    methods=["POST"],
    request=ActionInput,
    responses=ActionResultSerializer,
)
@extend_schema(tags=["vpsl"], methods=["GET"], responses=DeletePreviewSerializer)
@api_view(["GET", "POST"])
def rest_action(request, kind, pk):
    return _drf_response(api_workflow.action(django_request(request), kind, pk))


@extend_schema(
    tags=["vpsl"],
    request=inline_serializer(
        name="LocationInput", fields={"ubicacion_url": serializers.CharField()}
    ),
    responses=LocationPreviewSerializer,
)
@api_view(["POST"])
def rest_ubicacion(request):
    return _drf_response(api_workflow.ubicacion(django_request(request)))


@extend_schema(tags=["vpsl"], responses=RenaperSerializer)
@api_view(["GET"])
def rest_renaper(request):
    return _drf_response(api_workflow.renaper(django_request(request)))


@extend_schema(tags=["vpsl"], responses={(200, "text/csv"): bytes})
@api_view(["GET"])
def rest_export(request, kind, pk):
    return _drf_response(api_workflow.export(django_request(request), kind, pk))


@extend_schema(
    tags=["vpsl"],
    parameters=[OpenApiParameter("page", int), OpenApiParameter("page_size", int)],
    responses=RegistroPageSerializer,
)
@api_view(["GET"])
def rest_registros(request, pk):
    raw = django_request(request)
    denied = _authorize(raw, "ver_para_ser_libre.view_jornadavpsl")
    if denied:
        return _drf_response(denied)
    item = api_workflow.get_jornada(pk, request.user)
    return _drf_response(
        _paginated(raw, item.registros.order_by("pk"), _registro_data, page_size=25)
    )


@extend_schema(
    tags=["vpsl"],
    parameters=[OpenApiParameter("page", int), OpenApiParameter("page_size", int)],
    responses=LaboratorioPageSerializer,
)
@api_view(["GET"])
def rest_laboratorio(request, pk):
    raw = django_request(request)
    denied = _authorize(raw, "ver_para_ser_libre.view_jornadavpsl")
    if denied:
        return _drf_response(denied)
    item = api_workflow.get_jornada(pk, request.user)
    queryset = (
        CasoLaboratorioVPSL.objects.filter(registro__jornada=item)
        .select_related("registro")
        .prefetch_related("historial")
        .order_by("pk")
    )
    return _drf_response(_paginated(raw, queryset, _laboratorio_data, page_size=25))
