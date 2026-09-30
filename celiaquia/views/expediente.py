import json
import logging
import re
import traceback

from django.views import View
from django.views.generic import ListView, CreateView, DetailView, UpdateView
from django.urls import reverse, reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.http import (
    FileResponse,
    JsonResponse,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotAllowed,
)
from django.utils.html import escape
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, ValidationError, PermissionDenied
from django.conf import settings
from django.utils.decorators import method_decorator
from django.contrib.auth.models import User
from django.db.models import Q, Count, OuterRef, Subquery, F, CharField
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from iam.services import user_has_permission_code

from celiaquia.forms import ExpedienteForm, ConfirmarEnvioForm
from celiaquia.models import (
    AsignacionTecnico,
    EstadoLegajo,
    Expediente,
    ExpedienteCiudadano,
    RevisionTecnico,
    HistorialValidacionTecnica,
    Subsanacion,
    SubsanacionEstado,
    SubsanacionObservacion,
    TipoSubsanacion,
)
from ciudadanos.models import Ciudadano
from celiaquia.services.ciudadano_service import CiudadanoService
from celiaquia.services.expediente_service import (
    ExpedienteService,
    _set_estado,
)
from celiaquia.services.importacion_service import (
    ImportacionService,
    IMPORTACION_EDITABLE_FIELDS,
    IMPORTACION_RESPONSABLE_FIELDS,
    _beneficiario_tiene_conflicto_importacion,
    _beneficiario_requiere_responsable_importacion,
    _cargar_nacionalidades_cache,
    _cargar_paises_a_nacionalidad_importacion,
    _obtener_provincias_permitidas_ids,
    _precargar_conflictos_y_existentes_importacion,
    _resolver_nacionalidad_payload_importacion,
    validar_y_normalizar_payloads_importacion,
)
from celiaquia.comentarios_tecnicos import (
    TipoDocumentoComentario,
    catalogo_serializable as catalogo_comentarios_tecnicos,
)
from celiaquia.permissions import can_delete_legajo
from celiaquia.services.comentarios_tecnicos_service import ComentariosTecnicosService
from celiaquia.services.cruce_service import CruceService
from celiaquia.services.cupo_service import CupoService, CupoNoConfigurado
from celiaquia.services.expediente_filter_config import (  # pylint: disable=no-name-in-module
    CHOICE_OPS,
    DATE_OPS,
    FIELD_MAP as EXPEDIENTE_FILTER_MAP,
    FIELD_TYPES as EXPEDIENTE_FILTER_TYPES,
    NUM_OPS,
    TEXT_OPS,
    get_filters_ui_config,
)
from celiaquia.services.padron_final_service import (  # pylint: disable=no-name-in-module
    PadronFinalService,
)
from celiaquia.services.revision_service import (  # pylint: disable=no-name-in-module
    MAPA_TIPO_DOCUMENTO_A_SUBSANACION,
    RevisionService,
)
from celiaquia.services.validacion_edad_service import ValidacionEdadService
from django.utils import timezone
from django.db import transaction
from core.models import Nacionalidad, Provincia, Localidad
from core.services.advanced_filters import AdvancedFilterEngine
from core.soft_delete.preview import build_delete_preview
from core.soft_delete.view_helpers import is_soft_deletable_instance
from celiaquia.scope import apply_provincial_expediente_scope
from users.territorial_scope import (
    apply_territorial_scope,
    build_territorial_scope_q,
    get_effective_scopes,
    get_single_full_province_scope_id,
    is_territorial_user,
)

logger = logging.getLogger("django")

# Estas reglas viven ahora en `celiaquia/services/registros_erroneos_service/`,
# para que la API REST y estas pantallas apliquen exactamente lo mismo. Se
# reexportan con sus nombres viejos porque el resto del modulo (y sus tests)
# las usa asi.
from celiaquia.services import registros_erroneos_service  # noqa: E402
from celiaquia.services.registros_erroneos_service import (  # noqa: E402
    _actualizar_alerta_importacion_persistente,
    _aplicar_defaults_registro_erroneo,
    _build_excluidos_importacion_alerta,
    _build_resumen_importacion_alerta,
    _campos_invalidos_desde_mensaje_error,
    _can_manage_registros_erroneos,
    _consolidar_datos_registro_erroneo,
    _deduplicar_excluidos_alerta,
    _limpiar_datos_registro_erroneo,
    _normalizar_datos_registro_erroneo,
    _normalizar_mensaje_error_invalid_fields,
    _registro_erroneo_responsable_requerido,
    _resolver_localidad_registro_erroneo,
    _resolver_municipio_id_desde_localidad,
    _resolver_nacionalidad_id_registro_erroneo,
    _resolver_nacionalidad_registro_erroneo,
    _resolver_provincia_id_registro_erroneo,
    _user_provincia,
    _validar_datos_registro_erroneo,
)

ROLE_COORDINADOR_CELIAQUIA_PERMISSION = "auth.role_coordinadorceliaquia"
ROLE_TECNICO_CELIAQUIA_PERMISSION = "auth.role_tecnicoceliaquia"
ROLE_PROVINCIA_CELIAQUIA_PERMISSION = "auth.role_provinciaceliaquia"

EXPEDIENTE_ADVANCED_FILTER = AdvancedFilterEngine(
    field_map=EXPEDIENTE_FILTER_MAP,
    field_types=EXPEDIENTE_FILTER_TYPES,
    allowed_ops={
        "text": TEXT_OPS,
        "number": NUM_OPS,
        "date": DATE_OPS,
        "choice": CHOICE_OPS,
    },
)
EXPEDIENTE_ADVANCED_FILTER_SIN_TECNICO = AdvancedFilterEngine(
    field_map={
        field: lookup
        for field, lookup in EXPEDIENTE_FILTER_MAP.items()
        if field != "tecnico"
    },
    field_types={
        field: field_type
        for field, field_type in EXPEDIENTE_FILTER_TYPES.items()
        if field != "tecnico"
    },
    allowed_ops={
        "text": TEXT_OPS,
        "number": NUM_OPS,
        "date": DATE_OPS,
        "choice": CHOICE_OPS,
    },
)


def _user_has_permission(user, permission_code: str) -> bool:
    return user_has_permission_code(user, permission_code)


def _is_admin(user) -> bool:
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "is_superuser", False)
    )


def _can_view_tecnico_column(user) -> bool:
    return bool(
        _is_admin(user)
        or _user_has_permission(user, ROLE_COORDINADOR_CELIAQUIA_PERMISSION)
        or _user_has_permission(user, ROLE_TECNICO_CELIAQUIA_PERMISSION)
    )


def _user_in_group(user, group_name) -> bool:
    """Indica si el usuario pertenece al grupo solicitado."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    groups = getattr(user, "groups", None)
    if not groups:
        return False
    filter_fn = getattr(groups, "filter", None)
    if not callable(filter_fn) or not group_name:
        return False

    try:
        exists_fn = getattr(filter_fn(name=group_name), "exists", None)
        return bool(exists_fn() if callable(exists_fn) else False)
    except Exception:
        return False


def _is_ajax(request) -> bool:
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _is_provincial(user) -> bool:
    try:
        if is_territorial_user(user):
            return True
        return _user_has_permission(user, ROLE_PROVINCIA_CELIAQUIA_PERMISSION)
    except ObjectDoesNotExist:
        return False


def _can_manage_excel_masivo_audit(user) -> bool:
    return bool(
        _is_admin(user)
        or _user_has_permission(user, ROLE_COORDINADOR_CELIAQUIA_PERMISSION)
    )


def _get_nacionalidad_argentina():
    return Nacionalidad.objects.filter(nacionalidad__iexact="Argentina").first()


def _get_nacionalidad_argentina_id():
    argentina = _get_nacionalidad_argentina()
    return getattr(argentina, "pk", "") or ""


def _formatear_observaciones_historial(observaciones):
    if not observaciones:
        return ""

    try:
        payload = json.loads(observaciones)
    except (TypeError, ValueError):
        return observaciones

    if not isinstance(payload, dict):
        return observaciones

    partes = [
        str(payload.get(clave)).strip()
        for clave in ("resumen", "excluidos")
        if payload.get(clave)
    ]
    return "\n".join(partes) or observaciones


def _user_scope_provincias(user):
    provincia_ids = sorted({scope.provincia_id for scope in get_effective_scopes(user)})
    if not provincia_ids:
        return Provincia.objects.none()
    return Provincia.objects.filter(pk__in=provincia_ids).order_by("nombre")


def _apply_provincial_expediente_scope(queryset, user):
    # Las reglas viven en celiaquia/scope.py: las comparte con la API REST.
    return apply_provincial_expediente_scope(queryset, user)


def _get_provincial_expediente_or_404(user, pk):
    return get_object_or_404(
        _apply_provincial_expediente_scope(Expediente.objects.all(), user),
        pk=pk,
    )


def _tecnicos_queryset():
    qs = User.objects.filter(
        Q(
            user_permissions__content_type__app_label="auth",
            user_permissions__codename="role_tecnicoceliaquia",
        )
        | Q(
            groups__permissions__content_type__app_label="auth",
            groups__permissions__codename="role_tecnicoceliaquia",
        )
    )
    distinct = getattr(qs, "distinct", None)
    if callable(distinct):
        return distinct()
    return qs


def _parse_limit(value, default=None, max_cap=5000):
    if value is None:
        return default
    txt = str(value).strip().lower()
    if txt in ("all", "todos", "0", "none"):
        return None
    try:
        n = int(txt)
        if n <= 0:
            return None
        return min(n, max_cap) if max_cap is not None else n
    except Exception:
        return default


class LocalidadesLookupView(View):
    """Provide a JSON list of localidades filtered by provincia and municipio."""

    def get(self, request):
        user = request.user
        provincia_id = request.GET.get("provincia")
        municipio_id = request.GET.get("municipio")

        localidades = Localidad.objects.select_related("municipio__provincia")

        # Restringir por el alcance territorial real del usuario (provincia,
        # municipio y/o localidad). Coordinador y admin no tienen restriccion.
        # Antes se filtraba por la provincia unica del perfil, que queda vacia
        # cuando el usuario tiene varias provincias o un municipio especifico,
        # ocultando las localidades de su municipio.
        is_coord = _user_has_permission(user, ROLE_COORDINADOR_CELIAQUIA_PERMISSION)
        if _is_provincial(user) and not is_coord and not _is_admin(user):
            localidades = apply_territorial_scope(
                localidades,
                user,
                provincia_lookup="municipio__provincia_id",
                municipio_lookup="municipio_id",
                localidad_lookup="id",
            )

        if provincia_id:
            localidades = localidades.filter(municipio__provincia_id=provincia_id)
        if municipio_id:
            localidades = localidades.filter(municipio_id=municipio_id)

        data = [
            {
                "provincia_id": loc.municipio.provincia_id if loc.municipio else None,
                "provincia_nombre": (
                    loc.municipio.provincia.nombre
                    if loc.municipio and loc.municipio.provincia
                    else None
                ),
                "municipio_id": loc.municipio_id,
                "municipio_nombre": loc.municipio.nombre if loc.municipio else None,
                "localidad_id": loc.id,
                "localidad_nombre": loc.nombre,
            }
            for loc in localidades.order_by(
                "municipio__provincia__nombre", "municipio__nombre", "nombre"
            )
        ]
        return JsonResponse(data, safe=False)


class ExpedienteListView(ListView):
    model = Expediente
    template_name = "celiaquia/expediente_list.html"
    context_object_name = "expedientes"
    paginate_by = 20

    def get_paginate_by(self, queryset):
        return None

    def get_queryset(self):
        user = self.request.user
        qs = (
            Expediente.objects.select_related(
                "estado",
                "usuario_provincia__profile__provincia",
                "excel_masivo_cargado_por",
                "excel_masivo_procesado_por",
            )
            .prefetch_related("asignaciones_tecnicos__tecnico")
            .annotate(
                legajos_subsanar_count=Coalesce(
                    Subquery(
                        ExpedienteCiudadano.objects.filter(
                            expediente=OuterRef("pk"),
                            revision_tecnico="SUBSANAR",
                        )
                        .values("expediente")
                        .annotate(c=Count("id"))
                        .values("c")
                    ),
                    0,
                ),
                legajos_subsanado_count=Coalesce(
                    Subquery(
                        ExpedienteCiudadano.objects.filter(
                            expediente=OuterRef("pk"),
                            revision_tecnico="SUBSANADO",
                        )
                        .values("expediente")
                        .annotate(c=Count("id"))
                        .values("c")
                    ),
                    0,
                ),
            )
            .only(
                "id",
                "fecha_creacion",
                "estado__nombre",
                "usuario_provincia_id",
                "usuario_provincia__profile__id",
                "usuario_provincia__profile__provincia_id",
                "usuario_provincia__profile__provincia__id",
                "usuario_provincia__profile__provincia__nombre",
                "numero_expediente",
                "excel_masivo",
                "excel_masivo_cargado_por_id",
                "excel_masivo_cargado_por__first_name",
                "excel_masivo_cargado_por__last_name",
                "excel_masivo_cargado_por__username",
                "excel_masivo_cargado_en",
                "excel_masivo_procesado_por_id",
                "excel_masivo_procesado_por__first_name",
                "excel_masivo_procesado_por__last_name",
                "excel_masivo_procesado_por__username",
                "excel_masivo_procesado_en",
            )
        )

        # Provincia mostrada en la grilla: se deriva del territorio de los
        # ciudadanos del expediente (un usuario puede tener varias provincias y el
        # perfil legacy queda vacio). Se anota con Subquery para evitar N+1 y se
        # cae al valor legacy del perfil para expedientes aun sin legajos.
        provincia_derivada_sq = (
            ExpedienteCiudadano.objects.filter(
                expediente=OuterRef("pk"),
                ciudadano__provincia__isnull=False,
            )
            .order_by("ciudadano_id")
            .values("ciudadano__provincia__nombre")[:1]
        )
        qs = qs.annotate(
            provincia_derivada=Coalesce(
                Subquery(provincia_derivada_sq),
                F("usuario_provincia__profile__provincia__nombre"),
                output_field=CharField(),
            )
        )

        if _is_admin(user):
            qs = qs.order_by("-fecha_creacion")
        elif _is_provincial(user):
            qs = _apply_provincial_expediente_scope(qs, user).order_by(
                "-fecha_creacion"
            )
        elif _user_has_permission(user, ROLE_COORDINADOR_CELIAQUIA_PERMISSION):
            qs = qs.order_by("-fecha_creacion")
        elif _user_has_permission(user, ROLE_TECNICO_CELIAQUIA_PERMISSION):
            qs = (
                qs.filter(asignaciones_tecnicos__tecnico=user)
                .distinct()
                .order_by("-fecha_creacion")
            )
        else:
            qs = qs.filter(usuario_provincia=user).order_by("-fecha_creacion")

        search_query = self.request.GET.get("q", "").strip()
        if search_query:
            qs = qs.filter(
                Q(id__icontains=search_query)
                | Q(numero_expediente__icontains=search_query)
                | Q(estado__nombre__icontains=search_query)
                | Q(
                    usuario_provincia__profile__provincia__nombre__icontains=search_query
                )
                | Q(
                    expediente_ciudadanos__ciudadano__provincia__nombre__icontains=search_query
                )
                | Q(asignaciones_tecnicos__tecnico__first_name__icontains=search_query)
                | Q(asignaciones_tecnicos__tecnico__last_name__icontains=search_query)
                | Q(asignaciones_tecnicos__tecnico__username__icontains=search_query)
            ).distinct()

        # Filtros combinables (?filters=...). Se aplican sobre el queryset ya
        # acotado por rol/territorio, así ningún filtro puede ampliar el alcance.
        # El distinct() cubre el filtro por técnico, que atraviesa una relación
        # multivalor y de otro modo repetiría el expediente por cada asignación.
        advanced_filter = (
            EXPEDIENTE_ADVANCED_FILTER
            if _can_view_tecnico_column(user)
            else EXPEDIENTE_ADVANCED_FILTER_SIN_TECNICO
        )
        filtros_q = advanced_filter.build_q(self.request)
        if filtros_q is not None:
            qs = qs.filter(filtros_q).distinct()

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        is_admin = _is_admin(user)
        is_coord = _user_has_permission(user, ROLE_COORDINADOR_CELIAQUIA_PERMISSION)
        is_tecnico = _user_has_permission(user, ROLE_TECNICO_CELIAQUIA_PERMISSION)

        ctx["tecnicos"] = []
        ctx["is_admin_celiaquia"] = is_admin
        ctx["is_coord_celiaquia"] = is_coord
        ctx["is_tecnico_celiaquia"] = is_tecnico
        ctx["is_provincial_celiaquia"] = _is_provincial(user)
        ctx["can_manage_tecnicos_celiaquia"] = is_admin or is_coord
        ctx["can_manage_excel_masivo_audit"] = is_admin or is_coord
        ctx["show_tecnico_column_celiaquia"] = _can_view_tecnico_column(user)

        # El titulo depende del rol y lo consume el componente de busqueda, que
        # lo recibe como parametro; armarlo aca evita repetir el include.
        if ctx["can_manage_tecnicos_celiaquia"]:
            ctx["titulo_listado"] = "Bandeja de Subsecretaría"
        elif is_tecnico:
            ctx["titulo_listado"] = "Mis Expedientes Asignados"
        else:
            ctx["titulo_listado"] = "Mis Expedientes"

        # Filtros combinables. El campo "Técnico asignado" solo se ofrece a quien
        # ve la columna de técnico; para el resto get_filters_ui_config lo omite
        # al no recibir técnicos seleccionables.
        tecnicos_filtrables = (
            _tecnicos_queryset().order_by("last_name", "first_name")
            if ctx["show_tecnico_column_celiaquia"]
            else None
        )
        if is_admin or is_coord:
            ctx["tecnicos"] = tecnicos_filtrables

        ctx["filters_mode"] = True
        ctx["filters_config"] = get_filters_ui_config(tecnicos=tecnicos_filtrables)
        ctx["filters_action"] = reverse("expediente_list")
        return ctx


@method_decorator(csrf_protect, name="dispatch")
class ProcesarExpedienteView(View):
    def post(self, request, pk):
        user = self.request.user
        if _is_admin(user):
            expediente = get_object_or_404(Expediente, pk=pk)
        elif _is_provincial(user):
            expediente = _get_provincial_expediente_or_404(user, pk)
        else:
            expediente = get_object_or_404(Expediente, pk=pk, usuario_provincia=user)

        try:
            result = ExpedienteService.procesar_expediente(expediente, user)

            if _is_ajax(request):
                return JsonResponse(
                    {
                        "success": True,
                        "creados": result.get("creados", 0),
                        "errores": result.get("errores", 0),
                        "excluidos": result.get("excluidos", 0),
                        "excluidos_detalle": result.get("excluidos_detalle", []),
                        "alerta_resumen": _build_resumen_importacion_alerta(
                            creados_total=result.get("creados", 0),
                            errores_actuales=result.get("errores", 0),
                        ),
                    }
                )

            messages.success(
                request,
                f"Importación completada. Creados: {result.get('creados', 0)} — Errores: {result.get('errores', 0)}.",
            )

            excluidos_count = result.get("excluidos", 0)
            if excluidos_count:
                det = result.get("excluidos_detalle", [])
                preview = []
                for d in det[:10]:
                    doc = d.get("documento", "")
                    ape = d.get("apellido", "")
                    nom = d.get("nombre", "")
                    estado = (
                        d.get("estado_programa")
                        or d.get("estado_legajo_origen")
                        or d.get("motivo")
                        or "-"
                    )
                    expid = d.get("expediente_origen_id", "-")
                    preview.append(
                        f"• {doc} — {ape}, {nom} (Estado legajo: {estado}) — Exp #{expid}"
                    )

                extra = ""
                if len(det) > 10:
                    extra = f"<br>… y {len(det) - 10} más."

                # Escapar contenido para prevenir XSS
                preview_escaped = [escape(p) for p in preview]
                extra_escaped = escape(extra) if extra else ""
                encabezado = (
                    "Se excluyó 1 registro porque pertenece a otro expediente:"
                    if excluidos_count == 1
                    else f"Se excluyeron {excluidos_count} registros porque pertenecen a otro expediente:"
                )
                html = f"{encabezado}<br>{'<br>'.join(preview_escaped)}{extra_escaped}"
                messages.warning(request, html)

            return redirect("expediente_detail", pk=pk)

        except ValidationError as ve:
            if _is_ajax(request):
                return JsonResponse(
                    {"success": False, "error": escape(str(ve))}, status=400
                )
            messages.error(request, f"Error de validación: {escape(str(ve))}")
            return redirect("expediente_detail", pk=pk)
        except Exception as e:
            tb = traceback.format_exc()
            logging.error("Error al procesar expediente %s:\n%s", pk, tb)
            if _is_ajax(request):
                return JsonResponse(
                    {"success": False, "error": escape(str(e))}, status=500
                )
            messages.error(request, "Error inesperado al procesar el expediente.")
            return redirect("expediente_detail", pk=pk)


class CrearLegajosView(View):
    def post(self, request, pk):
        user = self.request.user
        if _is_admin(user):
            expediente = get_object_or_404(Expediente, pk=pk)
        elif _is_provincial(user):
            expediente = _get_provincial_expediente_or_404(user, pk)
        else:
            expediente = get_object_or_404(Expediente, pk=pk, usuario_provincia=user)

        try:
            payload = json.loads(request.body)
            rows = payload.get("rows", [])
        except json.JSONDecodeError:
            return HttpResponseBadRequest("JSON inválido.")

        return JsonResponse(
            ExpedienteService.crear_legajos_desde_filas(expediente, rows, user)
        )


class ExpedientePlantillaExcelView(View):
    """Genera un archivo de Excel vacío con los campos requeridos para un expediente."""

    def get(self, request, *args, **kwargs):
        content = ImportacionService.generar_plantilla_excel()
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            'attachment; filename="plantilla_expediente.xlsx"'
        )
        return response


class ExpedienteExcelMasivoDownloadView(View):
    """Descarga la copia del Excel masivo vigente del expediente."""

    def get(self, request, pk):
        if not _can_manage_excel_masivo_audit(request.user):
            raise PermissionDenied("No tiene permisos para descargar el Excel masivo.")

        expediente = get_object_or_404(Expediente, pk=pk)
        if not expediente.excel_masivo:
            messages.error(request, "El expediente no tiene Excel masivo cargado.")
            return redirect("expediente_detail", pk=expediente.pk)

        filename = expediente.excel_masivo.name.rsplit("/", 1)[-1]
        return FileResponse(
            expediente.excel_masivo.open("rb"),
            as_attachment=True,
            filename=filename,
        )


@method_decorator(csrf_protect, name="dispatch")
class ExpedientePreviewExcelView(View):
    def post(self, request, *args, **kwargs):
        logger.debug("PREVIEW: %s %s", request.method, request.get_full_path())
        archivo = request.FILES.get("excel_masivo")
        if not archivo:
            return JsonResponse({"error": "No se recibió ningún archivo."}, status=400)

        raw_limit = request.POST.get("limit") or request.GET.get("limit")
        max_rows = _parse_limit(raw_limit, default=None, max_cap=5000)

        try:
            preview = ImportacionService.preview_excel(archivo, max_rows=max_rows)
            return JsonResponse(preview)
        except ValidationError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except Exception:
            tb = traceback.format_exc()
            logger.error("PREVIEW error:\n%s", tb)
            return JsonResponse({"error": "Error inesperado al procesar."}, status=500)


class ExpedienteCreateView(CreateView):
    """Formulario para la creación de expedientes provinciales."""

    model = Expediente
    form_class = ExpedienteForm
    template_name = "celiaquia/expediente_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        # Filtrar provincias según el usuario
        if _is_provincial(user) and not _is_admin(user) and is_territorial_user(user):
            ctx["provincias"] = _user_scope_provincias(user)
        else:
            # Admin/Coordinador/provincial sin scope configurado: todas las provincias
            ctx["provincias"] = Provincia.objects.order_by("nombre")
        return ctx

    def form_valid(self, form):
        expediente = ExpedienteService.create_expediente(
            usuario_provincia=self.request.user,
            datos_metadatos=form.cleaned_data,
            excel_masivo=form.cleaned_data["excel_masivo"],
        )
        messages.success(self.request, "Expediente creado correctamente.")
        return redirect("expediente_detail", pk=expediente.pk)


class ExpedienteDetailView(DetailView):
    """Detalle del expediente con información relacionada."""

    model = Expediente
    template_name = "celiaquia/expediente_detail.html"
    context_object_name = "expediente"

    def get_queryset(self):
        user = self.request.user
        base = Expediente.objects.select_related(
            "estado",
            "usuario_modificador",
            "usuario_provincia",
            "excel_masivo_cargado_por",
            "excel_masivo_procesado_por",
        ).prefetch_related(
            "expediente_ciudadanos__ciudadano",
            "expediente_ciudadanos__estado",
            "asignaciones_tecnicos__tecnico",
        )
        if _is_admin(user):
            return base
        if _is_provincial(user):
            return _apply_provincial_expediente_scope(base, user)
        if _user_has_permission(user, ROLE_COORDINADOR_CELIAQUIA_PERMISSION):
            return base
        if _user_has_permission(user, ROLE_TECNICO_CELIAQUIA_PERMISSION):
            return base.filter(asignaciones_tecnicos__tecnico=user)
        return base.filter(usuario_provincia=user)

    def get_context_data(self, **kwargs):
        """Arma el contexto con métricas y paginación del historial."""

        ctx = super().get_context_data(**kwargs)
        expediente = self.object
        user = self.request.user
        is_admin = _is_admin(user)
        is_coord = _user_has_permission(user, ROLE_COORDINADOR_CELIAQUIA_PERMISSION)
        is_tecnico = _user_has_permission(user, ROLE_TECNICO_CELIAQUIA_PERMISSION)
        can_manage_registros_erroneos = _can_manage_registros_erroneos(user)
        ctx["is_tecnico_celiaquia"] = is_tecnico
        ctx["is_admin_celiaquia"] = is_admin
        ctx["is_coord_celiaquia"] = is_coord
        ctx["is_provincial_celiaquia"] = _is_provincial(user)
        ctx["can_manage_tecnicos_celiaquia"] = is_admin or is_coord
        ctx["can_manage_registros_erroneos"] = can_manage_registros_erroneos
        ctx["can_manage_excel_masivo_audit"] = is_admin or is_coord
        ctx["can_download_nomina_aprobados"] = bool(
            (is_admin or is_coord or is_tecnico)
            and expediente.estado.nombre == "CRUCE_FINALIZADO"
            and PadronFinalService.hay_aprobados(expediente)
        )

        preview = preview_error = None
        preview_limit_actual = None

        q = expediente.expediente_ciudadanos.select_related("ciudadano", "estado")
        counts = q.aggregate(
            c_aceptados=Count(
                "id",
                filter=Q(revision_tecnico="APROBADO", resultado_sintys="MATCH"),
            ),
            c_rech_tecnico=Count("id", filter=Q(revision_tecnico="RECHAZADO")),
            c_rech_sintys=Count(
                "id",
                filter=Q(revision_tecnico="APROBADO", resultado_sintys="NO_MATCH"),
            ),
            c_subsanar=Count("id", filter=Q(revision_tecnico=RevisionTecnico.SUBSANAR)),
            c_total=Count("id"),
        )
        ctx["hay_subsanar"] = counts["c_subsanar"] > 0
        # Total de legajos del expediente. Sale del mismo aggregate que los
        # conteos por estado, así que no agrega consultas.
        ctx["legajos_total"] = counts["c_total"]
        ctx["legajos_aceptados"] = q.filter(
            revision_tecnico="APROBADO", resultado_sintys="MATCH"
        )
        ctx["legajos_rech_tecnico"] = q.filter(revision_tecnico="RECHAZADO")
        ctx["legajos_rech_sintys"] = q.filter(
            revision_tecnico="APROBADO", resultado_sintys="NO_MATCH"
        )
        ctx["legajos_subsanar"] = q.filter(revision_tecnico=RevisionTecnico.SUBSANAR)

        # Enriquecer legajos con informacion de tipo (hijo/responsable)
        from celiaquia.services.legajo_service import LegajoService
        from celiaquia.services.familia_service import FamiliaService
        from celiaquia.services.subsanacion_service import SubsanacionService

        legajos_enriquecidos = []
        # Prefetch de subsanaciones solo para la lista que se enriquece y muestra
        # (evita disparar estas consultas en las querysets de conteo/listas).
        legajos_list = list(
            q.prefetch_related(
                "subsanaciones__observaciones",
                "subsanaciones__archivos__usuario",
                "subsanaciones__archivos__observacion",
                "subsanaciones__solicitada_por",
                "subsanaciones__respondida_por",
            ).all()
        )
        ultimo_historial_tecnico_con_motivo = (
            HistorialValidacionTecnica.objects.filter(legajo_id=OuterRef("legajo_id"))
            .exclude(Q(motivo__isnull=True) | Q(motivo=""))
            .order_by("-creado_en", "-pk")
            .values("pk")[:1]
        )
        historial_tecnico = HistorialValidacionTecnica.objects.filter(
            legajo_id__in=[legajo.pk for legajo in legajos_list],
            pk=Subquery(ultimo_historial_tecnico_con_motivo),
        )
        observaciones_tecnicas_por_legajo = {}
        for historial_item in historial_tecnico:
            observaciones_tecnicas_por_legajo.setdefault(
                historial_item.legajo_id, historial_item
            )
        legajos_por_ciudadano = {}
        ciudadanos_ids = [leg.ciudadano_id for leg in legajos_list]
        ciudadanos_ids_set = set(ciudadanos_ids)
        roles_responsables = {
            ExpedienteCiudadano.ROLE_RESPONSABLE,
            ExpedienteCiudadano.ROLE_BENEFICIARIO_Y_RESPONSABLE,
        }
        responsables_por_rol_ids = {
            leg.ciudadano_id
            for leg in legajos_list
            if (getattr(leg, "rol", "") or "").strip().lower() in roles_responsables
        }
        responsables_ids = set()
        if responsables_por_rol_ids:
            try:
                responsables_ids = FamiliaService.obtener_ids_responsables(
                    responsables_por_rol_ids, hijos_ids=ciudadanos_ids_set
                )
                responsables_ids.update(responsables_por_rol_ids)
            except Exception as exc:
                logger.warning(
                    "No se pudo resolver responsables para expediente %s: %s",
                    expediente.id,
                    exc,
                )

        # Enriquecer legajos con información de responsable/hijo
        responsables_legajos = []
        hijos_por_responsable = {}
        hijos_sin_responsable = []

        for legajo in legajos_list:
            rol_normalizado = (getattr(legajo, "rol", "") or "").strip().lower()
            legajo.es_responsable = rol_normalizado in roles_responsables
            legajo.responsable_id = FamiliaService.obtener_responsable_de_hijo(
                legajo.ciudadano.id, responsables_ids=responsables_ids
            )
            hijos_list = []
            # Buscar hijos si es responsable O si el rol es beneficiario_y_responsable
            if (
                legajo.es_responsable
                or legajo.rol == ExpedienteCiudadano.ROLE_BENEFICIARIO_Y_RESPONSABLE
            ):
                hijos_list = FamiliaService.obtener_hijos_a_cargo(
                    legajo.ciudadano.id, expediente
                )

            legajo.es_doble_rol = (
                rol_normalizado == ExpedienteCiudadano.ROLE_BENEFICIARIO_Y_RESPONSABLE
            ) or (legajo.es_responsable and legajo.responsable_id is not None)

            # Determinar tipo de legajo segun roles efectivos.
            if legajo.es_doble_rol:
                legajo.tipo_legajo = "Responsable y Beneficiario"
            elif legajo.es_responsable:
                legajo.tipo_legajo = "Responsable"
            else:
                legajo.tipo_legajo = "Beneficiario"

            legajo.archivos_requeridos = (
                LegajoService.get_archivos_requeridos_por_legajo(
                    legajo, responsables_ids
                )
            )
            # Indicadores de documentos: uno por cada archivo obligatorio del
            # legajo. Los legajos estandar requieren 2 (archivo2/archivo3) y los
            # de doble rol (beneficiario y responsable) requieren 3
            # (archivo1/archivo2/archivo3). Cada indicador refleja si el archivo
            # correspondiente esta cargado o pendiente.
            legajo.doc_indicadores = [
                {
                    "label": f"Doc{idx}",
                    "nombre": nombre,
                    "cargado": bool(getattr(legajo, campo, None)),
                }
                for idx, (campo, nombre) in enumerate(
                    legajo.archivos_requeridos.items(), start=1
                )
            ]
            # La provincia ve el panel de comentarios en los estados en que
            # puede haber observaciones publicadas: mientras subsana, después
            # de responder (para releer qué le pidieron) y si se la rechazó.
            legajo.comentarios_visibles_provincia = (
                legajo.revision_tecnico in ESTADOS_CON_COMENTARIOS_PUBLICADOS
            )
            # Subsanación activa (pendiente de respuesta) para que la provincia
            # adjunte archivos correctivos y se listen las evidencias cargadas.
            # Historial completo de subsanaciones (usa el prefetch del queryset).
            historial_subsanaciones = list(legajo.subsanaciones.all())
            legajo.subsanaciones_historial = historial_subsanaciones
            legajo.subsanacion_activa = None
            legajo.subsanacion_tiene_evidencia = False
            legajo.subsanacion_obs_dom_id = f"subs-obs-{legajo.pk}"
            legajo.subsanacion_obs_data = []
            if (
                legajo.revision_tecnico == RevisionTecnico.SUBSANAR
                and historial_subsanaciones
            ):
                legajo.subsanacion_activa = historial_subsanaciones[0]
                legajo.subsanacion_tiene_evidencia = SubsanacionService.tiene_evidencia(
                    legajo
                )
                legajo.subsanacion_obs_data = [
                    {
                        "id": obs.pk,
                        "label": obs.get_tipo_display()
                        + (f" — {obs.detalle}" if obs.detalle else ""),
                    }
                    for obs in legajo.subsanacion_activa.observaciones.all()
                ]

            legajo.observacion_tecnica_titulo = None
            legajo.observacion_tecnica_texto = None

            observacion_tecnica = observaciones_tecnicas_por_legajo.get(legajo.pk)
            if observacion_tecnica:
                if observacion_tecnica.estado_nuevo == RevisionTecnico.RECHAZADO:
                    legajo.observacion_tecnica_titulo = "Motivo del Rechazo"
                else:
                    legajo.observacion_tecnica_titulo = "Observación (subsanación)"
                legajo.observacion_tecnica_texto = observacion_tecnica.motivo
            elif legajo.subsanacion_motivo:
                legajo.observacion_tecnica_titulo = "Observación (subsanación)"
                legajo.observacion_tecnica_texto = legajo.subsanacion_motivo

            if (
                legajo.es_responsable
                or legajo.rol == ExpedienteCiudadano.ROLE_BENEFICIARIO_Y_RESPONSABLE
            ):
                legajo.hijos_a_cargo = hijos_list
                responsables_legajos.append(legajo)
                # Si tiene responsable, agregarlo también a hijos_por_responsable
                if legajo.responsable_id:
                    if legajo.responsable_id not in hijos_por_responsable:
                        hijos_por_responsable[legajo.responsable_id] = []
                    hijos_por_responsable[legajo.responsable_id].append(legajo)
            else:
                legajo.hijos_a_cargo = []
                if legajo.responsable_id:
                    if legajo.responsable_id not in hijos_por_responsable:
                        hijos_por_responsable[legajo.responsable_id] = []
                    hijos_por_responsable[legajo.responsable_id].append(legajo)
                else:
                    hijos_sin_responsable.append(legajo)

            legajos_por_ciudadano[legajo.ciudadano_id] = legajo

        # Ordenar: construir árbol jerárquico completo
        agregados = set()

        def agregar_con_descendientes(legajo):
            """Agrega un legajo y todos sus descendientes recursivamente"""
            if legajo.ciudadano_id in agregados:
                return
            agregados.add(legajo.ciudadano_id)
            legajos_enriquecidos.append(legajo)
            # Agregar hijos de este legajo
            hijos = hijos_por_responsable.get(legajo.ciudadano_id, [])
            for hijo in hijos:
                agregar_con_descendientes(hijo)

        # Encontrar raíces (responsables que no son hijos de nadie)
        raices = []
        for responsable in responsables_legajos:
            if responsable.responsable_id is None:
                raices.append(responsable)

        # Agregar cada raíz con sus descendientes
        for raiz in raices:
            agregar_con_descendientes(raiz)

        # Agregar responsables que no fueron agregados (tienen responsable pero también son responsables)
        for responsable in responsables_legajos:
            if responsable.ciudadano_id not in agregados:
                agregar_con_descendientes(responsable)

        # Agregar hijos sin responsable al final evitando duplicados.
        for legajo in hijos_sin_responsable:
            if legajo.ciudadano_id not in agregados:
                legajos_enriquecidos.append(legajo)
                agregados.add(legajo.ciudadano_id)

        # Agregar legajos huérfanos: tienen responsable_id pero ese responsable
        # no está en el expediente (fue eliminado o nunca se importó).
        # Sin este paso quedan invisibles en la vista pero siguen existiendo en BD,
        # lo que provoca errores en la validación de confirm_envío.
        for legajo in legajos_list:
            if legajo.ciudadano_id not in agregados:
                legajos_enriquecidos.append(legajo)
                agregados.add(legajo.ciudadano_id)

        faltantes_list = LegajoService.faltantes_archivos(expediente)
        # Obtener estructura familiar completa
        estructura_familiar = FamiliaService.obtener_estructura_familiar_expediente(
            expediente
        )

        # Enriquecer estructura familiar con referencia a legajos
        for info in estructura_familiar.get("responsables", {}).values():
            for hijo in info.get("hijos", []):
                hijo.legajo_relacionado = legajos_por_ciudadano.get(hijo.id)

        # Menores sin adulto responsable vivo en el expediente: se marcan en la
        # fila para que la provincia los ubique antes de intentar el envio, que
        # es donde la validacion bloquea.
        menores_sin_responsable_ids = {
            leg.pk for leg in ValidacionEdadService.menores_sin_responsable(expediente)
        }
        for legajo in legajos_enriquecidos:
            legajo.sin_responsable_alerta = legajo.pk in menores_sin_responsable_ids

        ctx["legajos_enriquecidos"] = legajos_enriquecidos
        ctx["estructura_familiar"] = estructura_familiar

        ctx["c_aceptados"] = counts["c_aceptados"]
        ctx["c_rech_tecnico"] = counts["c_rech_tecnico"]
        ctx["c_rech_sintys"] = counts["c_rech_sintys"]
        ctx["c_subsanar"] = counts["c_subsanar"]

        if expediente.estado.nombre == "CREADO" and expediente.excel_masivo:
            raw_limit = self.request.GET.get("preview_limit")
            max_rows = _parse_limit(raw_limit, default=None, max_cap=5000)
            preview_limit_actual = (
                raw_limit if raw_limit is not None else str(max_rows or "all")
            )
            try:
                preview = ImportacionService.preview_excel(
                    expediente.excel_masivo, max_rows=max_rows
                )
            except Exception as e:
                preview_error = str(e)

        preview_limit_opciones = ["5", "10", "20", "50", "100", "all"]

        tecnicos = []
        if _is_admin(user) or _user_has_permission(
            user, ROLE_COORDINADOR_CELIAQUIA_PERMISSION
        ):
            tecnicos = _tecnicos_queryset().order_by("last_name", "first_name")

        faltan_archivos = bool(faltantes_list)

        # Cupo: usar propiedad expediente.provincia (puede ser None)
        cupo = None
        cupo_metrics = None
        cupo_error = None
        prov = getattr(expediente, "provincia", None)
        if prov:
            try:
                cupo_metrics = CupoService.metrics_por_provincia(prov)
                cupo = cupo_metrics
            except CupoNoConfigurado:
                cupo_error = "La provincia no tiene cupo configurado."
        else:
            # Sin provincia determinable aun (p. ej. expediente sin legajos
            # importados). No corresponde a ninguna accion del usuario, por lo que
            # no se muestra un error al abrir el expediente.
            cupo_error = None

        fuera_count = expediente.expediente_ciudadanos.filter(
            estado_cupo="FUERA"
        ).count()
        ctx["fuera_de_cupo"] = q.filter(estado_cupo="FUERA")

        historial = expediente.historial.select_related(
            "estado_anterior", "estado_nuevo", "usuario"
        )
        historial_estado_actual = (
            historial.filter(
                estado_nuevo=expediente.estado,
                observaciones__isnull=False,
            )
            .exclude(observaciones="")
            .order_by("-fecha")
        )
        alerta_importacion_persistente = historial_estado_actual.values_list(
            "observaciones", flat=True
        ).first()
        ctx["alerta_importacion_persistente"] = alerta_importacion_persistente
        ctx["alerta_importacion_resumen"] = ""
        ctx["alerta_importacion_resumen_style"] = ""
        ctx["alerta_importacion_excluidos"] = ""
        ctx["alerta_importacion_excluidos_style"] = ""
        ctx["alerta_importacion_warning"] = ""
        ctx["alerta_importacion_warning_secundario"] = ""
        ctx["alerta_importacion_success"] = ""
        if alerta_importacion_persistente:
            try:
                alerta_payload = json.loads(alerta_importacion_persistente)
            except (TypeError, ValueError):
                alerta_payload = None

            if isinstance(alerta_payload, dict):
                resumen_alerta = alerta_payload.get("resumen", "")
                excluidos_alerta = alerta_payload.get("excluidos", "")
                creados_total = int(alerta_payload.get("creados_total") or 0)
                tiene_errores = bool(alerta_payload.get("tiene_errores"))
                resumen_bloque = ""
                resumen_bloque_style = ""
                excluidos_bloque = ""
                excluidos_bloque_style = ""

                # Al volver a entrar al expediente solo se recuperan advertencias
                # persistentes del estado EN_ESPERA; los mensajes success se
                # muestran en el flujo inmediato post-importacion / post-subsanacion.
                if tiene_errores:
                    resumen_bloque = resumen_alerta
                    resumen_bloque_style = "warning"
                    excluidos_bloque = excluidos_alerta
                    excluidos_bloque_style = "warning" if excluidos_alerta else ""
                elif creados_total == 0 and excluidos_alerta:
                    resumen_bloque = "\n".join(
                        part for part in [resumen_alerta, excluidos_alerta] if part
                    )
                    resumen_bloque_style = "warning"
                elif excluidos_alerta:
                    excluidos_bloque = excluidos_alerta
                    excluidos_bloque_style = "warning"

                ctx["alerta_importacion_resumen"] = resumen_bloque
                ctx["alerta_importacion_resumen_style"] = resumen_bloque_style
                ctx["alerta_importacion_excluidos"] = excluidos_bloque
                ctx["alerta_importacion_excluidos_style"] = excluidos_bloque_style
                ctx["alerta_importacion_warning"] = (
                    resumen_bloque if resumen_bloque_style == "warning" else ""
                )
                ctx["alerta_importacion_warning_secundario"] = (
                    excluidos_bloque if excluidos_bloque_style == "warning" else ""
                )
                ctx["alerta_importacion_success"] = (
                    resumen_bloque if resumen_bloque_style == "success" else ""
                )
        historial_page_obj = Paginator(historial, 5).get_page(
            self.request.GET.get("historial_page")
        )
        for item in historial_page_obj.object_list:
            item.observaciones_visibles = _formatear_observaciones_historial(
                item.observaciones
            )
        ctx["historial_page_obj"] = historial_page_obj

        # Obtener registros erróneos
        registros_erroneos = list(
            expediente.registros_erroneos.filter(procesado=False).order_by("fila_excel")
        )

        # Datos para desplegables en registros erróneos
        from core.models import Sexo, Municipio, Localidad

        sexos = Sexo.objects.all()
        nacionalidades = Nacionalidad.objects.all().order_by("nacionalidad")
        nacionalidad_argentina_id = str(_get_nacionalidad_argentina_id() or "")
        municipios = []
        localidades = []

        if prov:
            municipios = Municipio.objects.filter(provincia=prov).order_by("nombre")
            localidades = (
                Localidad.objects.filter(municipio__provincia=prov)
                .select_related("municipio")
                .order_by("municipio__nombre", "nombre")
            )
        elif can_manage_registros_erroneos:
            municipios = Municipio.objects.all().order_by("nombre")
            localidades = Localidad.objects.select_related("municipio").order_by(
                "municipio__nombre", "nombre"
            )

        for registro in registros_erroneos:
            datos_render = _aplicar_defaults_registro_erroneo(
                _normalizar_datos_registro_erroneo(registro.datos_raw or {})
            )
            registro.datos_render = datos_render
            registro.invalid_fields = _campos_invalidos_desde_mensaje_error(
                registro.mensaje_error
            )
            registro.responsable_requerido = _registro_erroneo_responsable_requerido(
                datos_render
            )
            registro.nacionalidad_autocomplete_id = (
                _resolver_nacionalidad_id_registro_erroneo(
                    datos_render.get("nacionalidad")
                )
            )
            registro.municipio_autocomplete_id = datos_render.get("municipio", "")

        ctx.update(
            {
                "legajos": legajos_enriquecidos,
                "registros_erroneos": registros_erroneos,
                "sexos": sexos,
                "nacionalidades": nacionalidades,
                "nacionalidad_argentina_id": nacionalidad_argentina_id,
                "municipios": municipios,
                "localidades": localidades,
                "confirm_form": ConfirmarEnvioForm(),
                "preview": preview,
                "preview_error": preview_error,
                "preview_limit_actual": str(preview_limit_actual or "5").lower(),
                "preview_limit_opciones": preview_limit_opciones,
                "tecnicos": tecnicos,
                "faltan_archivos": faltan_archivos,
                "faltantes_archivos_detalle": faltantes_list,
                "cupo": cupo,  # para el template actual
                "cupo_metrics": cupo_metrics,  # compat si lo usas en JS/otros templates
                "cupo_error": cupo_error,
                "provincia_expediente": prov,
                "fuera_count": fuera_count,
                "total_responsables": len(estructura_familiar.get("responsables", {})),
                "total_hijos_sin_responsable": len(
                    estructura_familiar.get("hijos_sin_responsable", [])
                ),
                # Catálogo de observaciones del formulario de comentarios
                # técnicos: el desplegable se filtra por tipo de documento en
                # el cliente, sin ida y vuelta al servidor.
                "catalogo_comentarios_tecnicos": catalogo_comentarios_tecnicos(),
                "tipos_documento_comentario": TipoDocumentoComentario.choices,
            }
        )
        return ctx


class ExpedienteImportView(View):
    def post(self, request, pk):
        user = self.request.user
        if _is_admin(user):
            expediente = get_object_or_404(Expediente, pk=pk)
        elif _is_provincial(user):
            expediente = _get_provincial_expediente_or_404(user, pk)
        else:
            expediente = get_object_or_404(Expediente, pk=pk, usuario_provincia=user)

        try:
            result = ImportacionService.importar_legajos_desde_excel(
                expediente, expediente.excel_masivo, user
            )
            detalles = result.get("detalles_errores") or []
            resumen = ""
            if detalles:
                resumen = "; ".join(
                    f"Fila {d.get('fila')}: {d.get('error')}" for d in detalles[:5]
                )
                if len(detalles) > 5:
                    resumen += " (ver logs para más detalles)"

            mensaje_principal = f"Importación: {result['validos']} válidos, {result['errores']} errores."
            if resumen:
                mensaje_principal += f" Detalles: {resumen}"
            messages.success(request, mensaje_principal)

            if detalles:
                messages.error(request, f"Errores detectados: {resumen}")

            advertencias = result.get("warnings") or []
            if advertencias:
                resumen_warn = "; ".join(
                    f"Fila {w.get('fila')}: {w.get('detalle')}"
                    for w in advertencias[:5]
                )
                if len(advertencias) > 5:
                    resumen_warn += " (se muestran las primeras 5)"
                messages.warning(request, f"Advertencias: {resumen_warn}")
        except ValidationError as ve:
            messages.error(request, f"Error de validación: {ve.message}")
        except Exception as e:
            messages.error(request, f"Error inesperado: {e}")
        return redirect("expediente_detail", pk=pk)


class ExpedienteConfirmView(View):
    def post(self, request, pk):
        user = self.request.user
        if _is_admin(user):
            expediente = get_object_or_404(Expediente, pk=pk)
        elif _is_provincial(user):
            expediente = _get_provincial_expediente_or_404(user, pk)
        else:
            expediente = get_object_or_404(Expediente, pk=pk, usuario_provincia=user)

        from celiaquia.models import RegistroErroneo

        registros_erroneos = RegistroErroneo.objects.filter(
            expediente=expediente, procesado=False
        )
        if registros_erroneos.exists():
            msg = f"No se puede enviar: hay {registros_erroneos.count()} registros con errores pendientes de corrección."
            if _is_ajax(request):
                return JsonResponse({"success": False, "error": msg}, status=400)
            messages.error(request, msg)
            return redirect("expediente_detail", pk=pk)

        try:
            result = ExpedienteService.confirmar_envio(expediente, user)
            if _is_ajax(request):
                return JsonResponse(
                    {
                        "success": True,
                        "message": "Expediente enviado a Subsecretaría.",
                        "validos": result["validos"],
                        "errores": result["errores"],
                    }
                )
            messages.success(
                request,
                f"Expediente enviado a Subsecretaría. Legajos: {result['validos']} (sin errores).",
            )
        except ValidationError as ve:
            error_msg = str(ve.message) if hasattr(ve, "message") else str(ve)
            if _is_ajax(request):
                return JsonResponse(
                    {"success": False, "error": escape(error_msg)}, status=400
                )
            messages.error(request, f"Error al confirmar: {escape(error_msg)}")
        except Exception as e:
            logger.error("Error inesperado al confirmar envío: %s", e, exc_info=True)
            if _is_ajax(request):
                return JsonResponse(
                    {"success": False, "error": escape(str(e))}, status=500
                )
            messages.error(request, f"Error inesperado: {escape(str(e))}")
        return redirect("expediente_detail", pk=pk)


class ExpedienteUpdateView(UpdateView):
    model = Expediente
    form_class = ExpedienteForm
    template_name = "celiaquia/expediente_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.FILES.get("excel_masivo"):
            self.object.excel_masivo_cargado_por = self.request.user
            self.object.excel_masivo_cargado_en = timezone.now()
            self.object.excel_masivo_procesado_por = None
            self.object.excel_masivo_procesado_en = None
            self.object.save(
                update_fields=[
                    "excel_masivo_cargado_por",
                    "excel_masivo_cargado_en",
                    "excel_masivo_procesado_por",
                    "excel_masivo_procesado_en",
                ]
            )
        return response

    def get_success_url(self):
        return reverse_lazy("expediente_detail", args=[self.object.pk])


class RecepcionarExpedienteView(View):
    def post(self, request, pk):
        user = self.request.user
        if not (
            _is_admin(user)
            or _user_has_permission(user, ROLE_COORDINADOR_CELIAQUIA_PERMISSION)
        ):
            if _is_ajax(request):
                return JsonResponse(
                    {"success": False, "error": "Permiso denegado."}, status=403
                )
            raise PermissionDenied(
                "No tiene permisos para recepcionar este expediente."
            )

        expediente = get_object_or_404(Expediente, pk=pk)
        try:
            ExpedienteService.recepcionar(expediente, user)
        except ValidationError as exc:
            msg = "; ".join(exc.messages)
            if _is_ajax(request):
                return JsonResponse({"success": False, "error": msg}, status=400)
            messages.warning(request, msg)
            return redirect("expediente_detail", pk=pk)

        if _is_ajax(request):
            return JsonResponse(
                {"success": True, "message": "Recepcionado correctamente."}
            )
        messages.success(
            request,
            "Expediente recepcionado correctamente. Ahora puede asignar un técnico.",
        )
        return redirect("expediente_detail", pk=pk)

    def get(self, *_a, **_k):
        return HttpResponseNotAllowed(["POST"])


class AsignarTecnicoView(View):
    def post(self, request, pk):
        user = self.request.user
        if not (
            _is_admin(user)
            or _user_has_permission(user, ROLE_COORDINADOR_CELIAQUIA_PERMISSION)
        ):
            if _is_ajax(request):
                return JsonResponse(
                    {"success": False, "error": "Permiso denegado."}, status=403
                )
            raise PermissionDenied("No tiene permisos para asignar técnico.")

        expediente = get_object_or_404(Expediente, pk=pk)

        tecnico_id = request.POST.get("tecnico_id")
        if not tecnico_id:
            msg = "No se seleccionó ningún técnico."
            if _is_ajax(request):
                return JsonResponse({"success": False, "error": msg}, status=400)
            messages.error(request, msg)
            return redirect("expediente_detail", pk=pk)

        tecnico_qs = _tecnicos_queryset()
        tecnico = get_object_or_404(tecnico_qs, pk=tecnico_id)

        estado_actual = expediente.estado.nombre
        if estado_actual not in ("RECEPCIONADO", "ASIGNADO"):
            msg = "Primero debe recepcionar el expediente."
            if _is_ajax(request):
                return JsonResponse({"success": False, "error": msg}, status=400)
            messages.error(request, msg)
            return redirect("expediente_detail", pk=pk)

        AsignacionTecnico.objects.get_or_create(
            expediente=expediente,
            tecnico=tecnico,
        )

        _set_estado(expediente, "ASIGNADO", user)

        if _is_ajax(request):
            return JsonResponse(
                {
                    "success": True,
                    "message": "Técnico asignado correctamente. Estado: ASIGNADO.",
                }
            )
        messages.success(
            request,
            f"Técnico {tecnico.get_full_name() or tecnico.username} asignado correctamente. Estado: ASIGNADO.",
        )
        return redirect("expediente_detail", pk=pk)

    def delete(self, request, pk):
        user = self.request.user
        if not (
            _is_admin(user)
            or _user_has_permission(user, ROLE_COORDINADOR_CELIAQUIA_PERMISSION)
        ):
            return JsonResponse(
                {"success": False, "error": "Permiso denegado."}, status=403
            )

        expediente = get_object_or_404(Expediente, pk=pk)
        tecnico_id = request.GET.get("tecnico_id")

        if not tecnico_id:
            return JsonResponse(
                {"success": False, "error": "ID de técnico requerido."}, status=400
            )

        try:
            asignacion = AsignacionTecnico.objects.get(
                expediente=expediente, tecnico_id=tecnico_id
            )
            get_data = getattr(request, "GET", {})
            post_data = getattr(request, "POST", {})
            preview_enabled = str(
                get_data.get("preview") or post_data.get("preview") or ""
            )
            if preview_enabled in {"1", "true", "True"} and is_soft_deletable_instance(
                asignacion
            ):
                return JsonResponse(
                    {
                        "success": True,
                        "preview": build_delete_preview(asignacion),
                    }
                )

            if is_soft_deletable_instance(asignacion):
                asignacion.delete(user=user, cascade=True)
            else:
                asignacion.delete()
            return JsonResponse(
                {"success": True, "message": "Técnico removido correctamente."}
            )
        except AsignacionTecnico.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Asignación no encontrada."}, status=404
            )


class ExpedienteNominaSintysExportView(View):
    """Descarga la nómina del expediente en formato compatible con Sintys."""

    def get(self, request, pk):
        expediente = get_object_or_404(Expediente, pk=pk)
        content = CruceService.generar_nomina_sintys_excel(expediente)
        filename = f"nomina_sintys_{expediente.pk}.xlsx"
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class SubirCruceExcelView(View):
    def post(self, request, pk):
        user = self.request.user

        if not (
            _is_admin(user)
            or _user_has_permission(user, ROLE_TECNICO_CELIAQUIA_PERMISSION)
        ):
            return JsonResponse(
                {"success": False, "error": "Permiso denegado."}, status=403
            )

        expediente = get_object_or_404(Expediente, pk=pk)

        if not _is_admin(user):
            # Usar prefetch para evitar query adicional
            tecnicos_ids = [
                t.tecnico_id for t in expediente.asignaciones_tecnicos.all()
            ]
            if user.id not in tecnicos_ids:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "No sos un técnico asignado a este expediente.",
                    },
                    status=403,
                )

        archivo = request.FILES.get("archivo")
        if not archivo:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Debe adjuntar un Excel con columna 'documento'.",
                },
                status=400,
            )

        try:
            resumen = CruceService.procesar_cruce_por_cuit(expediente, archivo, user)
            return JsonResponse(
                {
                    "success": True,
                    "message": "Cruce finalizado. Se generó el PRD del expediente.",
                    "resumen": resumen,
                }
            )
        except ValidationError as ve:
            return JsonResponse(
                {"success": False, "error": escape(str(ve))}, status=400
            )
        except Exception as e:
            logger.error("Error en cruce por CUIT: %s", e, exc_info=True)
            return JsonResponse({"success": False, "error": escape(str(e))}, status=500)

    def get(self, *_a, **_k):
        return HttpResponseNotAllowed(["POST"])


#: Estados del legajo en los que la provincia puede tener observaciones
#: técnicas publicadas y por lo tanto ve el panel de comentarios. Queda afuera
#: PENDIENTE, donde todavía no se publicó nada. Se enumeran los estados que
#: habilitan el panel, y no los que lo niegan, para que un estado nuevo no pase
#: a mostrar comentarios internos por descuido.
ESTADOS_CON_COMENTARIOS_PUBLICADOS = {
    RevisionTecnico.SUBSANAR,
    RevisionTecnico.SUBSANADO,
    RevisionTecnico.RECHAZADO,
    RevisionTecnico.APROBADO,
}


def _observaciones_desde_comentarios_tecnicos(legajo):
    """Observaciones (tipo, detalle) derivadas de los comentarios técnicos.

    Alias del service, que es donde vive la traducción. Se conserva el nombre
    porque lo usan los tests y el resto del módulo."""
    return RevisionService.observaciones_desde_comentarios_tecnicos(legajo)


def _parse_observaciones_subsanacion(request, motivo_general):
    """Construye la lista de (tipo, detalle) de una solicitud de subsanación.

    Soporta el formato nuevo (múltiples observaciones tipo+detalle y/o múltiples
    motivos seleccionados) y cae al formato legacy (un único tipo_subsanacion).
    Siempre devuelve al menos una observación."""
    tipos_validos = {value for value, _ in TipoSubsanacion.choices}

    # Observaciones específicas (tipo + detalle) del formato nuevo.
    obs_tipos = request.POST.getlist("observacion_tipo")
    obs_detalles = request.POST.getlist("observacion_detalle")
    observaciones = []
    for tipo, detalle in zip(obs_tipos, obs_detalles):
        tipo = (tipo or "").strip().upper()
        detalle = (detalle or "").strip()
        if tipo in tipos_validos:
            observaciones.append((tipo, detalle[:500]))

    # Motivos seleccionados (checkboxes) que aún no tengan una observación propia:
    # se registran con el detalle general para no perder la categoría elegida.
    tipos_en_observaciones = {tipo for tipo, _ in observaciones}
    motivos_sel = [
        m.strip().upper() for m in request.POST.getlist("motivos") if m.strip()
    ]
    for tipo in motivos_sel:
        if tipo in tipos_validos and tipo not in tipos_en_observaciones:
            observaciones.append((tipo, motivo_general[:500]))
            tipos_en_observaciones.add(tipo)

    # Fallback legacy: un único tipo_subsanacion.
    if not observaciones:
        tipo_legacy = (request.POST.get("tipo_subsanacion") or "OTROS").strip().upper()
        if tipo_legacy not in tipos_validos:
            tipo_legacy = TipoSubsanacion.OTROS
        observaciones.append((tipo_legacy, motivo_general[:500]))

    return observaciones


@method_decorator(csrf_protect, name="dispatch")
class RevisarLegajoView(View):
    def _componer_motivo(self, request, leg):
        """Motivo de Subsanar/Rechazar armado en backend.

        Concatena las observaciones técnicas del legajo (las que tienen
        observaciones = Sí) y le suma el texto libre complementario. Lo que
        llega del cliente es solo ese texto libre: la previsualización que
        muestra el modal no es la fuente de verdad. Devuelve
        ``(motivo, None)`` o ``("", JsonResponse)`` cuando no hay nada que
        comunicar."""
        texto_libre = request.POST.get("texto_libre")
        if texto_libre is None:
            # La UI previa al issue #2318 manda el motivo en `motivo`.
            texto_libre = request.POST.get("motivo") or ""
        try:
            return ComentariosTecnicosService.componer_motivo(leg, texto_libre), None
        except ValidationError as exc:
            return "", JsonResponse(
                {"success": False, "error": "; ".join(exc.messages)}, status=400
            )

    def _rechazar(self, user, leg, motivo):
        """Rechaza el legajo. La regla vive en `RevisionService.rechazar`."""
        return JsonResponse(RevisionService.rechazar(leg, user, motivo))

    def _subsanar(self, request, user, leg, motivo):
        """Solicita la subsanación. La vista solo parsea el POST.

        El fallback por request cubre los legajos previos al issue #2318, que
        todavía no tienen comentarios técnicos: el service lo usa solo si no
        encuentra observaciones publicables."""
        tipo_subsanacion = (request.POST.get("tipo_subsanacion") or "").strip()
        return JsonResponse(
            RevisionService.subsanar(
                leg,
                user,
                motivo,
                tipo_subsanacion=tipo_subsanacion,
                observaciones_fallback=_parse_observaciones_subsanacion(
                    request, motivo
                ),
            )
        )

    def _eliminar_legajo(self, request, user, leg, *, revalidar_baja_provincial=False):
        """Elimina un legajo delegando en `RevisionService.eliminar`.

        La vista conserva el modo `preview` (que es de la UI) y la traducción de
        los errores a JsonResponse. Devuelve siempre una JsonResponse."""
        try:
            get_data = getattr(request, "GET", {})
            post_data = getattr(request, "POST", {})
            preview_enabled = str(
                post_data.get("preview") or get_data.get("preview") or ""
            )
            if preview_enabled in {"1", "true", "True"}:
                payload = RevisionService.preview_eliminacion(leg)
                if payload is not None:
                    return JsonResponse(payload)

            return JsonResponse(
                RevisionService.eliminar(
                    leg,
                    user,
                    revalidar_baja_provincial=revalidar_baja_provincial,
                )
            )
        except PermissionDenied as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=403)
        except Exception as e:
            logger.error("Error al eliminar legajo %s: %s", leg.pk, e, exc_info=True)
            return JsonResponse(
                {
                    "success": False,
                    "message": "Ocurrió un error al eliminar el legajo. Inténtelo nuevamente más tarde.",
                },
                status=500,
            )

    def post(self, request, pk, legajo_id):
        """Punto de entrada de la pantalla. Las reglas viven en RevisionService."""
        user = request.user
        expediente = get_object_or_404(Expediente, pk=pk)

        accion = (request.POST.get("accion") or "").upper()

        es_admin = _is_admin(user)
        es_tecnico = _user_has_permission(user, ROLE_TECNICO_CELIAQUIA_PERMISSION)
        es_coord = _user_has_permission(user, ROLE_COORDINADOR_CELIAQUIA_PERMISSION)
        es_prov = _is_provincial(user)
        solo_provincia = es_prov and not (es_admin or es_tecnico or es_coord)

        try:
            RevisionService.verificar_permiso(user, expediente, accion)
        except PermissionDenied as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=403)

        leg = get_object_or_404(
            ExpedienteCiudadano, pk=legajo_id, expediente=expediente
        )

        # La provincia solo elimina, y con la validación extra de `can_delete_legajo`
        # tanto acá como al confirmar, con el expediente bloqueado.
        if solo_provincia:
            try:
                can_delete_legajo(user, expediente, leg)
            except PermissionDenied as exc:
                return JsonResponse({"success": False, "error": str(exc)}, status=403)
            return self._eliminar_legajo(
                request, user, leg, revalidar_baja_provincial=True
            )

        try:
            accion = RevisionService.validar_accion(accion)
            RevisionService.validar_transicion(leg, accion)
        except ValidationError as exc:
            return JsonResponse(
                {"success": False, "error": "; ".join(exc.messages)}, status=400
            )

        # El motivo se compone antes de tocar el cupo y el estado: si no hay
        # nada que comunicar, el legajo tiene que quedar intacto.
        motivo = ""
        if accion in ("RECHAZAR", "SUBSANAR"):
            motivo, error = self._componer_motivo(request, leg)
            if error:
                return error

        RevisionService.liberar_cupo_si_corresponde(leg, user, accion)

        if accion == "APROBAR":
            return JsonResponse(RevisionService.aprobar(leg, user))

        if accion == "RECHAZAR":
            return self._rechazar(user, leg, motivo)

        if accion == "ELIMINAR":
            return self._eliminar_legajo(request, user, leg)

        return self._subsanar(request, user, leg, motivo)


ESTADOS_EVALUACION_FINAL = {"APROBADO", "RECHAZADO", "SUBSANADO"}


@method_decorator(csrf_protect, name="dispatch")
class CorregirEvaluacionView(View):
    """Corrección de la evaluación final de un legajo por Nación autorizada.

    Permite cambiar el estado entre APROBADO, RECHAZADO y SUBSANADO ante errores
    posteriores a la evaluación. Reservado a administradores y coordinadores; no
    disponible para usuarios provinciales ni técnicos. Cada cambio queda
    registrado en HistorialValidacionTecnica (usuario, fecha/hora, estado
    anterior y nuevo)."""

    def get(self, *_a, **_k):
        return HttpResponseNotAllowed(["POST"])

    def post(self, request, pk, legajo_id):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse(
                {"success": False, "error": "Autenticación requerida."}, status=403
            )

        es_admin = _is_admin(user)
        es_coord = _user_has_permission(user, ROLE_COORDINADOR_CELIAQUIA_PERMISSION)
        if not (es_admin or es_coord):
            return JsonResponse(
                {
                    "success": False,
                    "error": "No tenés permiso para corregir evaluaciones finales.",
                },
                status=403,
            )

        expediente = get_object_or_404(Expediente, pk=pk)
        leg = get_object_or_404(
            ExpedienteCiudadano, pk=legajo_id, expediente=expediente
        )

        nuevo_estado = (request.POST.get("nuevo_estado") or "").strip().upper()
        if nuevo_estado not in ESTADOS_EVALUACION_FINAL:
            return JsonResponse(
                {"success": False, "error": "Estado de evaluación inválido."},
                status=400,
            )

        estado_anterior = leg.revision_tecnico
        if estado_anterior not in ESTADOS_EVALUACION_FINAL:
            return JsonResponse(
                {
                    "success": False,
                    "error": "El legajo no tiene una evaluación final para corregir.",
                },
                status=400,
            )
        if nuevo_estado == estado_anterior:
            return JsonResponse(
                {"success": False, "error": "El legajo ya está en ese estado."},
                status=400,
            )

        motivo = (request.POST.get("motivo") or "").strip()
        cupo_liberado = False

        with transaction.atomic():
            # Regla de negocio de cupo: si la corrección saca al legajo de
            # APROBADO (a RECHAZADO/SUBSANADO) y ocupaba cupo, se libera.
            if (
                nuevo_estado in ("RECHAZADO", "SUBSANADO")
                and leg.estado_cupo == "DENTRO"
            ):
                try:
                    CupoService.liberar_slot(
                        legajo=leg,
                        usuario=user,
                        motivo=f"Corrección de evaluación final a {nuevo_estado}",
                    )
                    leg.estado_cupo = "NO_EVAL"
                    leg.es_titular_activo = False
                    cupo_liberado = True
                except CupoNoConfigurado as exc:
                    logger.warning(
                        "Corrección legajo %s sin cupo configurado: %s", leg.pk, exc
                    )
                except Exception as exc:  # pragma: no cover - log y continuar
                    logger.error(
                        "Error al liberar cupo en corrección de legajo %s: %s",
                        leg.pk,
                        exc,
                        exc_info=True,
                    )

            leg.revision_tecnico = nuevo_estado
            leg.save(
                update_fields=[
                    "revision_tecnico",
                    "modificado_en",
                    "estado_cupo",
                    "es_titular_activo",
                ]
            )

            motivo_historial = "Corrección de evaluación final."
            if motivo:
                motivo_historial = f"{motivo_historial} {motivo}"
            HistorialValidacionTecnica.objects.create(
                legajo=leg,
                estado_anterior=estado_anterior,
                estado_nuevo=nuevo_estado,
                usuario=user,
                motivo=motivo_historial[:500],
            )

        logger.info(
            "Evaluación corregida: legajo=%s %s -> %s por user=%s",
            leg.pk,
            estado_anterior,
            nuevo_estado,
            user.id,
        )
        return JsonResponse(
            {
                "success": True,
                "estado": nuevo_estado,
                "estado_anterior": estado_anterior,
                "cupo_liberado": cupo_liberado,
            }
        )


class ActualizarRegistroErroneoView(View):
    def post(self, request, pk, registro_id):
        user = request.user

        if not _can_manage_registros_erroneos(user):
            return JsonResponse(
                {"success": False, "error": "Permiso denegado."}, status=403
            )

        # Coordinador/admin gestionan cualquier expediente; el usuario provincial
        # solo los de su alcance territorial (evita operar registros de otra
        # provincia accediendo por pk directo).
        if _is_admin(user) or _user_has_permission(
            user, ROLE_COORDINADOR_CELIAQUIA_PERMISSION
        ):
            expediente = get_object_or_404(Expediente, pk=pk)
        else:
            expediente = _get_provincial_expediente_or_404(user, pk)

        from celiaquia.models import RegistroErroneo

        registro = get_object_or_404(
            RegistroErroneo, pk=registro_id, expediente=expediente
        )

        try:
            registros_erroneos_service.actualizar(
                expediente, registro, json.loads(request.body), user
            )
            return JsonResponse(
                {"success": True, "message": "Registro actualizado correctamente."}
            )
        except ValidationError as exc:
            return JsonResponse(
                {
                    "success": False,
                    "saved_partial": True,
                    "error": str(exc),
                    "invalid_fields": registros_erroneos_service.campos_invalidos(exc),
                },
                status=400,
            )
        except Exception as e:
            logger.error("Error actualizando registro erróneo: %s", e, exc_info=True)
            return JsonResponse(
                {
                    "success": False,
                    "error": "Ocurrió un error interno al actualizar el registro.",
                },
                status=500,
            )


class ReprocesarRegistrosErroneosView(View):
    # La transaccion la abre el service, que es el dueño de la operacion.
    def post(self, request, pk):
        user = request.user

        if not _can_manage_registros_erroneos(user):
            return JsonResponse(
                {"success": False, "error": "Permiso denegado."}, status=403
            )

        # Coordinador/admin reprocesan cualquier expediente; el usuario provincial
        # solo los de su alcance territorial.
        if _is_admin(user) or _user_has_permission(
            user, ROLE_COORDINADOR_CELIAQUIA_PERMISSION
        ):
            expediente = get_object_or_404(Expediente, pk=pk)
        else:
            expediente = _get_provincial_expediente_or_404(user, pk)

        try:
            resumen = registros_erroneos_service.reprocesar(expediente, user)
        except ValidationError as exc:
            return JsonResponse(
                {"success": False, "error": exc.messages[0]}, status=400
            )
        return JsonResponse({"success": True, **resumen})


class EliminarRegistroErroneoView(View):
    def post(self, request, pk, registro_id):
        user = request.user
        expediente = get_object_or_404(Expediente, pk=pk)

        if not _can_manage_registros_erroneos(user):
            return JsonResponse(
                {"success": False, "error": "Permiso denegado."}, status=403
            )

        from celiaquia.models import RegistroErroneo

        registro = get_object_or_404(
            RegistroErroneo, pk=registro_id, expediente=expediente
        )

        get_data = getattr(request, "GET", {})
        post_data = getattr(request, "POST", {})
        preview_enabled = str(post_data.get("preview") or get_data.get("preview") or "")
        if preview_enabled in {"1", "true", "True"} and is_soft_deletable_instance(
            registro
        ):
            return JsonResponse(
                {
                    "success": True,
                    "preview": build_delete_preview(registro),
                }
            )

        if is_soft_deletable_instance(registro):
            registro.delete(user=user, cascade=True)
        else:
            registro.delete()
        return JsonResponse(
            {"success": True, "message": "Registro eliminado correctamente."}
        )


class ExpedienteDeleteView(View):
    def delete(self, request, pk):
        user = request.user
        if not (_is_admin(user) or _user_in_group(user, "CoordinadorCeliaquia")):
            return JsonResponse(
                {"success": False, "error": "Permiso denegado."}, status=403
            )
        queryset = getattr(Expediente, "all_objects", Expediente.objects)
        expediente = queryset.filter(pk=pk).first()
        if expediente is None:
            return JsonResponse(
                {
                    "success": True,
                    "message": "El expediente ya estaba eliminado.",
                    "already_deleted": True,
                }
            )

        get_data = getattr(request, "GET", {})
        post_data = getattr(request, "POST", {})
        preview_enabled = str(post_data.get("preview") or get_data.get("preview") or "")
        if preview_enabled in {"1", "true", "True"} and is_soft_deletable_instance(
            expediente
        ):
            return JsonResponse(
                {
                    "success": True,
                    "preview": build_delete_preview(expediente),
                }
            )

        try:
            if is_soft_deletable_instance(expediente):
                expediente.delete(user=user, cascade=True)
            else:
                expediente.delete()
            return JsonResponse(
                {"success": True, "message": "Expediente eliminado correctamente."}
            )
        except Exception as e:
            logger.error("Error al eliminar expediente %s: %s", pk, e, exc_info=True)
            return JsonResponse(
                {"success": False, "error": "Error al eliminar el expediente."},
                status=500,
            )
