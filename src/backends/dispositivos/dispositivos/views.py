import json
import os

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ProtectedError, Q
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from core.services.advanced_filters import AdvancedFilterEngine
from core.services.favorite_filters import SeccionesFiltrosFavoritos

from .dispositivos_filter_config import (
    CHOICE_OPS as DISPOSITIVOS_CHOICE_OPS,
    FIELD_MAP as DISPOSITIVOS_FIELD_MAP,
    FIELD_TYPES as DISPOSITIVOS_FIELD_TYPES,
    NUM_OPS as DISPOSITIVOS_NUM_OPS,
    TEXT_OPS as DISPOSITIVOS_TEXT_OPS,
    get_filters_ui_config,
)
from .forms import DispositivoForm
from .models import Dispositivo
from .services import (
    apply_dispositivos_scope,
    delete_dispositivo,
    get_dispositivos_queryset,
    get_saved_dispositivo_location,
    geolocate_dispositivo,
    save_dispositivo_from_form,
)


def _format_value(value):
    if value in (None, ""):
        return "-"
    return value


def _format_display_list(values, choices):
    labels = dict(choices)
    if not values:
        return []
    return [labels.get(v, v) for v in values]


def _format_file(file_field):
    if not file_field:
        return None
    return {
        "name": os.path.basename(file_field.name),
        "url": file_field.url,
    }


DISPOSITIVOS_ADVANCED_FILTER = AdvancedFilterEngine(
    field_map=DISPOSITIVOS_FIELD_MAP,
    field_types=DISPOSITIVOS_FIELD_TYPES,
    allowed_ops={
        "text": DISPOSITIVOS_TEXT_OPS,
        "number": DISPOSITIVOS_NUM_OPS,
        "choice": DISPOSITIVOS_CHOICE_OPS,
    },
)


class DispositivoListView(LoginRequiredMixin, ListView):
    model = Dispositivo
    template_name = "dispositivos_list.html"
    context_object_name = "dispositivos"
    paginate_by = 15

    def get_queryset(self):
        queryset = get_dispositivos_queryset()
        queryset = apply_dispositivos_scope(queryset, self.request.user)
        queryset = DISPOSITIVOS_ADVANCED_FILTER.filter_queryset(queryset, self.request)

        query = (self.request.GET.get("busqueda") or "").strip()
        if query:
            queryset = queryset.filter(
                Q(nombre_institucion__icontains=query)
                | Q(tipo_dispositivo__icontains=query)
                | Q(provincia__nombre__icontains=query)
                | Q(municipio__nombre__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reset_url"] = reverse("dispositivos_listar")
        context["add_url"] = (
            reverse("dispositivos_crear")
            if self.request.user.has_perm("dispositivos.add_dispositivo")
            else None
        )
        context["filters_mode"] = True
        context["filters_config"] = get_filters_ui_config()
        context["filters_action"] = reverse("dispositivos_listar")
        context["seccion_filtros_favoritos"] = SeccionesFiltrosFavoritos.DISPOSITIVOS
        query = self.request.GET.copy()
        query.pop("page", None)
        context["map_url"] = reverse("dispositivos_mapa")
        if query:
            context["map_url"] += "?" + query.urlencode()
        context["titulo"] = "Buscar Dispositivos"
        return context


class DispositivoDetailView(LoginRequiredMixin, DetailView):
    model = Dispositivo
    template_name = "dispositivos_detail.html"
    context_object_name = "dispositivo"

    def get_queryset(self):
        return apply_dispositivos_scope(get_dispositivos_queryset(), self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dispositivo = self.object
        context["breadcrumb_items"] = [
            {"text": "Dispositivos", "url": reverse("dispositivos_listar")},
            {"text": dispositivo.nombre_institucion},
        ]
        context["detalle_secciones"] = [
            {
                "titulo": "Identificación del dispositivo",
                "icono": "fas fa-building",
                "items": [
                    {
                        "label": "Nombre de la institución",
                        "value": _format_value(dispositivo.nombre_institucion),
                    },
                    {
                        "label": "Tipo de gestión",
                        "value": dispositivo.get_tipo_gestion_display(),
                    },
                    {
                        "label": "Tipo de gestión - detalle",
                        "value": _format_value(dispositivo.tipo_gestion_otra),
                    },
                    {
                        "label": "Razón social",
                        "value": _format_value(dispositivo.razon_social),
                    },
                    {
                        "label": "CUIT",
                        "value": _format_value(dispositivo.cuit_institucion),
                    },
                    {
                        "label": "Provincia",
                        "value": _format_value(str(dispositivo.provincia)),
                    },
                    {
                        "label": "Municipio",
                        "value": _format_value(str(dispositivo.municipio)),
                    },
                    {
                        "label": "Calle",
                        "value": _format_value(dispositivo.calle),
                    },
                    {
                        "label": "Altura",
                        "value": _format_value(dispositivo.altura),
                    },
                    {
                        "label": "Teléfono",
                        "value": _format_value(
                            f"{dispositivo.telefono_prefijo} {dispositivo.telefono_numero}".strip()
                            or None
                        ),
                    },
                    {
                        "label": "Correo electrónico",
                        "value": _format_value(dispositivo.correo_electronico),
                    },
                    {
                        "label": "Responsable",
                        "value": _format_value(dispositivo.responsable_nombre_completo),
                    },
                    {
                        "label": "DNI del responsable",
                        "value": _format_value(dispositivo.responsable_dni),
                    },
                ],
            },
            {
                "titulo": "Características del dispositivo",
                "icono": "fas fa-cogs",
                "items": [
                    {
                        "label": "Tipo de dispositivo",
                        "value": dispositivo.get_tipo_dispositivo_display(),
                    },
                    {
                        "label": "Tipo de dispositivo - detalle",
                        "value": _format_value(dispositivo.tipo_dispositivo_otro),
                    },
                    {
                        "label": "Modalidad de funcionamiento",
                        "value": dispositivo.get_modalidad_funcionamiento_display(),
                    },
                    {
                        "label": "Capacidad total de plazas",
                        "value": dispositivo.get_capacidad_total_plazas_display(),
                    },
                    {
                        "label": "Días de atención",
                        "value": _format_display_list(
                            dispositivo.dias_atencion,
                            DispositivoForm.DIAS_ATENCION_CHOICES,
                        ),
                        "kind": "list",
                    },
                    {
                        "label": "Horarios de funcionamiento",
                        "value": _format_display_list(
                            dispositivo.horarios_funcionamiento,
                            DispositivoForm.HORARIOS_FUNCIONAMIENTO_CHOICES,
                        ),
                        "kind": "list",
                    },
                ],
            },
            {
                "titulo": "Población destinataria",
                "icono": "fas fa-users",
                "items": [
                    {
                        "label": "Población destinataria",
                        "value": _format_display_list(
                            dispositivo.poblacion_destinataria,
                            DispositivoForm.POBLACION_DESTINATARIA_CHOICES,
                        ),
                        "kind": "list",
                    },
                    {
                        "label": "Detalle población",
                        "value": _format_value(dispositivo.poblacion_destinataria_otro),
                    },
                    {
                        "label": "Franja etaria",
                        "value": _format_display_list(
                            dispositivo.franja_etaria_destinataria,
                            DispositivoForm.FRANJA_ETARIA_CHOICES,
                        ),
                        "kind": "list",
                    },
                    {
                        "label": "Tiempo promedio de permanencia",
                        "value": (
                            dispositivo.get_tiempo_permanencia_promedio_display()
                            if dispositivo.tiempo_permanencia_promedio
                            else "-"
                        ),
                    },
                    {
                        "label": "Detalle permanencia",
                        "value": _format_value(dispositivo.tiempo_permanencia_otro),
                    },
                ],
            },
            {
                "titulo": "Modalidad de ingreso",
                "icono": "fas fa-sign-in-alt",
                "items": [
                    {
                        "label": "Modalidad de ingreso",
                        "value": _format_display_list(
                            dispositivo.modalidad_ingreso,
                            DispositivoForm.MODALIDAD_INGRESO_CHOICES,
                        ),
                        "kind": "list",
                    },
                    {
                        "label": "Detalle modalidad",
                        "value": _format_value(dispositivo.modalidad_ingreso_otro),
                    },
                    {
                        "label": "Documentación para el ingreso",
                        "value": _format_display_list(
                            dispositivo.documentacion_ingreso,
                            DispositivoForm.DOCUMENTACION_INGRESO_CHOICES,
                        ),
                        "kind": "list",
                    },
                    {
                        "label": "Detalle documentación",
                        "value": _format_value(dispositivo.documentacion_ingreso_otro),
                    },
                    {
                        "label": "Requisitos para el ingreso",
                        "value": _format_display_list(
                            dispositivo.requisitos_ingreso,
                            DispositivoForm.REQUISITOS_INGRESO_CHOICES,
                        ),
                        "kind": "list",
                    },
                    {
                        "label": "Detalle requisitos",
                        "value": _format_value(dispositivo.requisitos_ingreso_otro),
                    },
                ],
            },
            {
                "titulo": "Servicios brindados",
                "icono": "fas fa-hands-helping",
                "items": [
                    {
                        "label": "Servicios brindados",
                        "value": _format_display_list(
                            dispositivo.servicios_brindados,
                            DispositivoForm.SERVICIOS_BRINDADOS_CHOICES,
                        ),
                        "kind": "list",
                    },
                    {
                        "label": "Detalle servicios",
                        "value": _format_value(dispositivo.servicios_brindados_otro),
                    },
                    {
                        "label": "Ofrece actividades formativas",
                        "value": (
                            dispositivo.get_ofrece_actividades_formativas_display()
                            if dispositivo.ofrece_actividades_formativas
                            else "-"
                        ),
                    },
                    {
                        "label": "Tipos de actividades formativas",
                        "value": _format_display_list(
                            dispositivo.tipos_actividades_formativas,
                            DispositivoForm.TIPO_ACTIVIDADES_FORMATIVAS_CHOICES,
                        ),
                        "kind": "list",
                    },
                    {
                        "label": "Detalle actividades",
                        "value": _format_value(
                            dispositivo.tipos_actividades_formativas_otro
                        ),
                    },
                    {
                        "label": "Certificación oficial de actividades",
                        "value": (
                            dispositivo.get_actividades_certificacion_oficial_display()
                            if dispositivo.actividades_certificacion_oficial
                            else "-"
                        ),
                    },
                ],
            },
            {
                "titulo": "Sistema de registro de personas usuarias",
                "icono": "fas fa-clipboard-list",
                "items": [
                    {
                        "label": "Registra información de personas",
                        "value": (
                            dispositivo.get_registra_informacion_personas_display()
                            if dispositivo.registra_informacion_personas
                            else "-"
                        ),
                    },
                    {
                        "label": "Modo de registro",
                        "value": (
                            dispositivo.get_modo_registro_display()
                            if dispositivo.modo_registro
                            else "-"
                        ),
                    },
                    {
                        "label": "Detalle modo de registro",
                        "value": _format_value(dispositivo.modo_registro_otro),
                    },
                    {
                        "label": "Tipo de información registrada",
                        "value": _format_display_list(
                            dispositivo.tipo_informacion_registrada,
                            DispositivoForm.TIPO_INFO_REGISTRADA_CHOICES,
                        ),
                        "kind": "list",
                    },
                    {
                        "label": "Detalle información",
                        "value": _format_value(
                            dispositivo.tipo_informacion_registrada_otro
                        ),
                    },
                ],
            },
            {
                "titulo": "Infraestructura y necesidades",
                "icono": "fas fa-tools",
                "items": [
                    {
                        "label": "Infraestructura disponible",
                        "value": _format_display_list(
                            dispositivo.infraestructura_disponible,
                            DispositivoForm.INFRAESTRUCTURA_DISPONIBLE_CHOICES,
                        ),
                        "kind": "list",
                    },
                    {
                        "label": "Detalle infraestructura",
                        "value": _format_value(
                            dispositivo.infraestructura_disponible_otro
                        ),
                    },
                    {
                        "label": "Infraestructura de accesibilidad",
                        "value": _format_display_list(
                            dispositivo.infraestructura_accesibilidad,
                            DispositivoForm.INFRAESTRUCTURA_ACCESIBILIDAD_CHOICES,
                        ),
                        "kind": "list",
                    },
                    {
                        "label": "Detalle accesibilidad",
                        "value": _format_value(
                            dispositivo.infraestructura_accesibilidad_otro
                        ),
                    },
                    {
                        "label": "Principales limitaciones",
                        "value": _format_value(dispositivo.principales_limitaciones),
                        "wide": True,
                    },
                    {
                        "label": "Necesidades prioritarias",
                        "value": _format_value(dispositivo.necesidades_prioritarias),
                        "wide": True,
                    },
                ],
            },
            {
                "titulo": "Articulaciones institucionales",
                "icono": "fas fa-network-wired",
                "items": [
                    {
                        "label": "Articulaciones institucionales",
                        "value": _format_display_list(
                            dispositivo.articulaciones_institucionales,
                            DispositivoForm.ARTICULACIONES_CHOICES,
                        ),
                        "kind": "list",
                    },
                    {
                        "label": "Detalle articulaciones",
                        "value": _format_value(
                            dispositivo.articulaciones_institucionales_otro
                        ),
                    },
                ],
            },
            {
                "titulo": "Observaciones y documentación",
                "icono": "fas fa-file-alt",
                "items": [
                    {
                        "label": "Observaciones adicionales",
                        "value": _format_value(dispositivo.observaciones_adicionales),
                        "wide": True,
                    },
                    {
                        "label": "Documentación del dispositivo",
                        "value": _format_file(dispositivo.documentacion_dispositivo),
                        "kind": "file",
                    },
                    {
                        "label": "Documentación adicional 1",
                        "value": _format_file(
                            dispositivo.documentacion_dispositivo_adicional_1
                        ),
                        "kind": "file",
                    },
                    {
                        "label": "Documentación adicional 2",
                        "value": _format_file(
                            dispositivo.documentacion_dispositivo_adicional_2
                        ),
                        "kind": "file",
                    },
                    {
                        "label": "Documentación adicional 3",
                        "value": _format_file(
                            dispositivo.documentacion_dispositivo_adicional_3
                        ),
                        "kind": "file",
                    },
                    {
                        "label": "Documentación adicional 4",
                        "value": _format_file(
                            dispositivo.documentacion_dispositivo_adicional_4
                        ),
                        "kind": "file",
                    },
                ],
            },
        ]
        return context


class DispositivoCreateView(LoginRequiredMixin, CreateView):
    model = Dispositivo
    form_class = DispositivoForm
    template_name = "dispositivos_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumb_items"] = [
            {"text": "Dispositivos", "url": reverse("dispositivos_listar")},
            {"text": "Nuevo dispositivo"},
        ]
        return context

    def form_valid(self, form):
        self.object = save_dispositivo_from_form(form)
        messages.success(self.request, "Dispositivo creado correctamente.")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("dispositivos_detalle", kwargs={"pk": self.object.pk})


class DispositivoUpdateView(LoginRequiredMixin, UpdateView):
    model = Dispositivo
    form_class = DispositivoForm
    template_name = "dispositivos_form.html"

    def get_queryset(self):
        return apply_dispositivos_scope(get_dispositivos_queryset(), self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumb_items"] = [
            {"text": "Dispositivos", "url": reverse("dispositivos_listar")},
            {
                "text": self.object.nombre_institucion,
                "url": reverse("dispositivos_detalle", kwargs={"pk": self.object.pk}),
            },
            {"text": "Editar"},
        ]
        return context

    def form_valid(self, form):
        self.object = save_dispositivo_from_form(form, instance=self.get_object())
        messages.success(self.request, "Dispositivo actualizado correctamente.")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("dispositivos_detalle", kwargs={"pk": self.object.pk})


class DispositivoDeleteView(LoginRequiredMixin, DeleteView):
    model = Dispositivo
    template_name = "dispositivos_confirm_delete.html"
    context_object_name = "dispositivo"

    def get_queryset(self):
        return apply_dispositivos_scope(get_dispositivos_queryset(), self.request.user)

    def form_valid(self, form):
        self.object = self.get_object()
        try:
            delete_dispositivo(self.object)
        except ProtectedError as exc:
            asociados = sorted(
                {str(obj._meta.verbose_name_plural) for obj in exc.protected_objects}
            )
            messages.error(
                self.request,
                "No se puede eliminar el dispositivo porque tiene registros "
                f"asociados: {', '.join(asociados)}.",
            )
            return HttpResponseRedirect(
                reverse("dispositivos_detalle", kwargs={"pk": self.object.pk})
            )
        messages.success(self.request, "Dispositivo eliminado correctamente.")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("dispositivos_listar")


class DispositivoMapView(DispositivoListView):
    """Mapa con los mismos filtros y alcance territorial que el listado."""

    template_name = "dispositivos_map.html"
    paginate_by = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["map_url"] = None
        context["reset_url"] = reverse("dispositivos_mapa")
        context["filters_action"] = reverse("dispositivos_mapa")
        context["map_devices"] = [
            {
                "id": device.pk,
                "name": device.nombre_institucion,
                "type": device.get_tipo_dispositivo_display(),
                "province_id": device.provincia_id,
                "province": str(device.provincia),
                "representative": device.responsable_nombre_completo,
                "phone": " ".join(
                    part
                    for part in (device.telefono_prefijo, device.telefono_numero)
                    if part
                ),
                "address": f"{device.calle} {device.altura}, {device.municipio}, {device.provincia}",
                "detail_url": reverse("dispositivos_detalle", args=[device.pk]),
                "location_url": reverse("dispositivos_ubicacion", args=[device.pk]),
                "location": get_saved_dispositivo_location(device),
            }
            for device in context["dispositivos"]
        ]
        # Las opciones salen del alcance del usuario y no del resultado filtrado,
        # para poder cambiar de provincia sin limpiar los filtros.
        context["map_provinces"] = list(
            apply_dispositivos_scope(Dispositivo.objects.all(), self.request.user)
            .order_by("provincia__nombre")
            .values_list("provincia_id", "provincia__nombre")
            .distinct()
        )
        for field in context["filters_config"]["fields"]:
            if field["name"] == "provincia":
                field["type"] = "choice"
                field["choices"] = [
                    {"value": name, "label": name}
                    for _, name in context["map_provinces"]
                ]
        context["filters_config"]["fields"].append(
            {
                "name": "estado_ubicacion",
                "label": "Estado de ubicación",
                "type": "choice",
                "choices": [
                    {"value": value, "label": label}
                    for value, label in (
                        ("located", "Ubicado"),
                        ("pending", "Pendiente"),
                        ("ambiguous", "Dirección ambigua"),
                        ("not_found", "Sin coincidencia"),
                        ("unavailable", "Servicio no disponible"),
                    )
                ],
            }
        )
        try:
            payload = json.loads(self.request.GET.get("filters") or "{}")
        except (ValueError, TypeError):
            payload = {}
        items = payload.get("items", []) if isinstance(payload, dict) else []
        context["map_location_filters"] = (
            [
                item
                for item in items
                if isinstance(item, dict)
                and item.get("field") == "estado_ubicacion"
                and item.get("op") in ("eq", "ne")
            ]
            if isinstance(items, list)
            else []
        )
        selected_id = self.request.GET.get("dispositivo", "")
        context["map_initial_device"] = next(
            (
                device["id"]
                for device in context["map_devices"]
                if str(device["id"]) == selected_id
            ),
            "",
        )
        context["breadcrumb_items"] = [
            {"text": "Dispositivos", "url": reverse("dispositivos_listar")},
            {"text": "Mapa"},
        ]
        return context


class DispositivoLocationView(LoginRequiredMixin, View):
    """Resuelve únicamente direcciones de dispositivos visibles para el usuario."""

    def get(self, request, pk):
        device = get_object_or_404(
            apply_dispositivos_scope(get_dispositivos_queryset(), request.user), pk=pk
        )
        result = geolocate_dispositivo(device)
        response = JsonResponse(
            result, status=503 if result["status"] == "unavailable" else 200
        )
        response["Cache-Control"] = "private, no-store"
        return response
