"""API de sesión del frontend INET; no usa las claves de integración VAT."""

from django import forms
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from drf_spectacular.authentication import SessionScheme
from drf_spectacular.openapi import AutoSchema
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from VAT import models
from VAT.api_inet_serializers import (
    InetAsistenciaSerializer,
    InetEstadoInputSerializer,
    InetFormInputSerializer,
    InetFormSerializer,
    InetHorarioSerializer,
    InetInscripcionInputSerializer,
    InetItemSerializer,
    InetSessionSerializer,
    InetPageSerializer,
    InetCiudadanoPageSerializer,
    InetOptionsPageSerializer,
    InetDeletePreviewSerializer,
)
from VAT.forms import ComisionCursoWizardHorarioForm, InscripcionForm
from VAT.services.access_scope import (
    get_user_provincia_id,
    is_vat_provincial,
    is_vat_sse,
)
from VAT.services.inet_forms import (
    FORM_CLASSES,
    authorize_create,
    build_form,
    choice_options,
    choice_queryset,
    form_data,
    serialize_form,
    validate_form,
    InetCiudadanoForm,
    InetSinDniForm,
)
from VAT.services.inet_queries import (
    RESOURCES,
    can_mutate,
    filter_resource_queryset,
    resource_queryset,
    serialize_item,
)
from VAT.services.inet_workflow import (
    actualizar_centro,
    contacto_formset,
    crear_centro,
    crear_comision,
    guardar_asistencia,
    reemplazar_horarios,
    sync_responsable_principal,
    validate_horarios,
)
from VAT.services.inscripcion_service import InscripcionService
from VAT.services.sesion_comision_service.impl import SesionComisionService
from ciudadanos.models import Ciudadano
from iam.services import user_has_permission_code


# Campos de los filtros de búsqueda: sus catálogos alcanzan con permiso de lectura.
FILTER_FIELDS = {
    "centros": {"provincia", "municipio", "localidad"},
    "planes": {"sector"},
}


class InetSessionAuthentication(SessionAuthentication):
    """Sesión/CSRF de Django con 401 explícito si no hay sesión."""

    def authenticate_header(self, request):
        return "Session"


class InetSessionScheme(SessionScheme):
    target_class = "VAT.api_inet_views.InetSessionAuthentication"
    priority = 1


class InetSchema(AutoSchema):
    def get_operation_id(self):
        return (
            "inet_"
            + "_".join(
                part.strip("{}").replace("-", "_")
                for part in self.path.strip("/").split("/")[2:]
            )
            + "_"
            + self.method.lower()
        )


class InetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 200


class InetAPIView(APIView):
    authentication_classes = [InetSessionAuthentication]
    permission_classes = [IsAuthenticated]
    resource = "centros"
    schema = InetSchema()

    def check_read(self):
        _, codename = RESOURCES[self.resource]
        if not user_has_permission_code(self.request.user, f"VAT.view_{codename}"):
            raise PermissionDenied()
        if self.resource == "planes" and not (
            is_vat_sse(self.request.user) or is_vat_provincial(self.request.user)
        ):
            raise PermissionDenied()

    def get_item(self, pk):
        self.check_read()
        return get_object_or_404(
            resource_queryset(self.resource, self.request.user), pk=pk
        )

    def check_write(self, item, action="change"):
        if not can_mutate(self.resource, self.request.user, item, action):
            raise PermissionDenied()

    def page(self, queryset, serializer):
        pagination = InetPagination()
        rows = pagination.paginate_queryset(queryset, self.request, view=self)
        return pagination.get_paginated_response(serializer(rows))


@method_decorator(ensure_csrf_cookie, name="dispatch")
class InetSessionView(InetAPIView):
    @extend_schema(responses=InetSessionSerializer)
    def get(self, request):
        self.check_read()
        permissions = [
            f"{action}_{codename}"
            for _, codename in RESOURCES.values()
            for action in ("view", "add", "change", "delete")
            if user_has_permission_code(request.user, f"VAT.{action}_{codename}")
        ]
        return Response(
            {
                "username": request.user.get_username(),
                "nombre": request.user.get_full_name(),
                "permissions": permissions,
                "puede_ver_planes": is_vat_sse(request.user)
                or is_vat_provincial(request.user),
            }
        )


class InetCollectionView(InetAPIView):
    @extend_schema(responses=InetPageSerializer)
    def get(self, request):
        self.check_read()
        queryset = filter_resource_queryset(
            resource_queryset(self.resource, request.user),
            self.resource,
            request.query_params,
        )
        return self.page(
            queryset,
            lambda rows: [
                serialize_item(self.resource, row, request.user) for row in rows
            ],
        )

    @extend_schema(request=InetFormInputSerializer, responses={201: InetItemSerializer})
    @transaction.atomic
    def post(self, request):
        if self.resource not in FORM_CLASSES:
            raise PermissionDenied()
        serializer = InetFormInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        values = payload["campos"]
        authorize_create(self.resource, request.user, values)
        form = validate_form(build_form(self.resource, request.user, values=values))
        if self.resource == "centros":
            contacts = contacto_formset(form.instance, payload.get("contactos", []))
            item = crear_centro(form, contacts)
        elif self.resource == "comisiones":
            item, _ = crear_comision(
                form.curso,
                form.cleaned_data,
                validate_horarios(payload.get("horarios", [])),
            )
        else:
            if self.resource == "planes":
                form.instance.provincia_id = get_user_provincia_id(request.user)
            item = form.save()
            if self.resource == "contactos":
                sync_responsable_principal(item.centro)
            if self.resource == "horarios":
                SesionComisionService.generar_para_horario(item)
        return Response(serialize_item(self.resource, item, request.user), status=201)


class InetDetailView(InetAPIView):
    @extend_schema(responses=InetItemSerializer)
    def get(self, request, pk):
        return Response(serialize_item(self.resource, self.get_item(pk), request.user))

    @extend_schema(request=InetFormInputSerializer, responses=InetItemSerializer)
    @transaction.atomic
    def put(self, request, pk):
        item = self.get_item(pk)
        self.check_write(item)
        previous_dates = (
            getattr(item, "fecha_inicio", None),
            getattr(item, "fecha_fin", None),
        )
        if self.resource not in FORM_CLASSES:
            raise PermissionDenied()
        serializer = InetFormInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        form = validate_form(
            build_form(self.resource, request.user, item=item, values=payload["campos"])
        )
        if self.resource == "centros":
            # Si no se envía la sección de contactos, conservar los existentes.
            rows = payload.get("contactos")
            if rows is None:
                rows = list(
                    item.contactos_adicionales.values(
                        "id",
                        "nombre_contacto",
                        "rol_area",
                        "documento",
                        "telefono_contacto",
                        "email_contacto",
                        "es_principal",
                    )
                )
            item = actualizar_centro(form, contacto_formset(item, rows))
        else:
            item = form.save()
            if self.resource == "comisiones" and "horarios" in payload:
                if not all(
                    user_has_permission_code(request.user, code)
                    for code in (
                        "VAT.add_comisionhorario",
                        "VAT.change_comisionhorario",
                    )
                ):
                    raise PermissionDenied()
                reemplazar_horarios(item, payload["horarios"])
            if self.resource == "comisiones" and previous_dates != (
                item.fecha_inicio,
                item.fecha_fin,
            ):
                SesionComisionService.regenerar_para_comision(
                    item,
                    fechas_excluidas=set(
                        item.sesiones.exclude(estado="programada").values_list(
                            "fecha", flat=True
                        )
                    ),
                )
            if self.resource == "contactos":
                sync_responsable_principal(item.centro)
            if self.resource == "horarios":
                SesionComisionService.regenerar_para_horario(item)
        return Response(serialize_item(self.resource, item, request.user))

    @extend_schema(responses={204: None})
    @transaction.atomic
    def delete(self, request, pk):
        item = self.get_item(pk)
        self.check_write(item, "delete")
        if self.resource in ("inscripciones", "sesiones"):
            raise PermissionDenied()
        if self.resource == "horarios":
            if item.sesiones.exclude(estado="programada").exists():
                raise ValidationError(
                    {
                        "detail": "Este horario tiene clases realizadas o canceladas. Desactivalo para conservar el historial."
                    }
                )
            SesionComisionService.eliminar_para_horario(item)
            item.delete()
        else:
            item.delete(user=request.user)
        return Response(status=204)


class InetFormView(InetAPIView):
    @extend_schema(responses=InetFormSerializer)
    def get(self, request, pk=None):
        item = self.get_item(pk) if pk else None
        if item:
            self.check_write(item)
        else:
            authorize_create(self.resource, request.user, request.query_params)
        return Response(
            serialize_form(
                build_form(
                    self.resource, request.user, item=item, initial=request.query_params
                )
            )
        )


class InetOptionsView(InetAPIView):
    @extend_schema(responses=InetOptionsPageSerializer)
    def get(self, request, field, pk=None):
        self.check_read()
        item = self.get_item(pk) if pk else None
        if field not in FILTER_FIELDS.get(self.resource, ()):
            # Catálogos de alta/edición (p. ej. usuarios referentes): mismo
            # permiso que el formulario, no alcanza con poder ver el recurso.
            if item:
                self.check_write(item)
            elif not user_has_permission_code(
                request.user, f"VAT.add_{RESOURCES[self.resource][1]}"
            ):
                raise PermissionDenied()
        form = build_form(
            self.resource, request.user, item=item, initial=request.query_params
        )
        if (
            field not in form.fields
            or form.fields[field].widget.is_hidden
            or not isinstance(form.fields[field], forms.ChoiceField)
        ):
            raise ValidationError({"field": ["Catálogo no disponible."]})
        choice = form.fields[field]
        if isinstance(choice, forms.ModelChoiceField):
            queryset = choice_queryset(
                choice, query=request.query_params.get("search", "")
            )
            return self.page(
                queryset,
                lambda rows: [
                    {"value": str(row.pk), "label": choice.label_from_instance(row)}
                    for row in rows
                ],
            )
        return self.page(choice_options(choice), lambda rows: rows)


class InetFilterFormView(InetAPIView):
    @extend_schema(responses=InetFormSerializer)
    def get(self, request):
        self.check_read()
        form = build_form(self.resource, request.user, initial=request.query_params)
        names = FILTER_FIELDS[self.resource]
        result = serialize_form(form)
        result["fields"] = [
            field for field in result["fields"] if field["name"] in names
        ]
        for field in result["fields"]:
            field["required"] = False
        return Response(result)


class InetDeletePreviewView(InetAPIView):
    @extend_schema(responses=InetDeletePreviewSerializer)
    def get(self, request, pk):
        from core.soft_delete.preview import build_delete_preview

        item = self.get_item(pk)
        self.check_write(item, "delete")
        return Response(
            InetDeletePreviewSerializer(build_delete_preview(item, sample_limit=0)).data
        )


class InetHorarioFormView(InetAPIView):
    @extend_schema(responses=InetFormSerializer)
    def get(self, request):
        self.check_read()
        form = ComisionCursoWizardHorarioForm()
        result = serialize_form(form)
        for field in result["fields"]:
            if field["name"] == "dia_semana":
                field["options"] = choice_options(form.fields["dia_semana"])
                field["remote_options"] = False
        return Response(result)


class InetCiudadanoFormView(InetAPIView):
    @extend_schema(responses=InetFormSerializer)
    def get(self, request):
        self.check_read()
        if not user_has_permission_code(request.user, "VAT.add_inscripcion"):
            raise PermissionDenied()
        form = (
            InetSinDniForm()
            if request.query_params.get("sin_dni") == "true"
            else InetCiudadanoForm()
        )
        result = serialize_form(form)
        for field in result["fields"]:
            if field["remote_options"]:
                field["options"] = choice_options(form.fields[field["name"]])
                field["remote_options"] = False
        return Response(result)


class InetHorariosView(InetAPIView):
    resource = "comisiones"

    @extend_schema(responses=InetHorarioSerializer(many=True))
    def get(self, request, pk):
        comision = self.get_item(pk)
        return Response(
            [
                {
                    "id": row.pk,
                    "dia": str(row.dia_semana),
                    "hora_desde": row.hora_desde,
                    "hora_hasta": row.hora_hasta,
                    "vigente": row.vigente,
                }
                for row in comision.horarios.select_related("dia_semana").all()
            ]
        )


class InetCiudadanosView(InetAPIView):
    resource = "comisiones"

    @extend_schema(responses=InetCiudadanoPageSerializer)
    def get(self, request, pk):
        comision = self.get_item(pk)
        if not user_has_permission_code(request.user, "VAT.add_inscripcion"):
            raise PermissionDenied()
        from VAT.services.access_scope import can_user_edit_centro

        if not can_user_edit_centro(request.user, comision.curso.centro):
            raise PermissionDenied()
        # Búsqueda exacta por documento; nunca exponer el padrón completo.
        query = request.query_params.get("documento", "").strip()
        rows = Ciudadano.objects.none()
        if 6 <= len(query) <= 15:
            condition = Q(documento_pasaporte=query.upper())
            if query.isdigit():
                condition |= Q(documento=int(query))
            rows = Ciudadano.objects.filter(condition)
        return self.page(
            rows.order_by("id"),
            lambda items: [
                {
                    "id": row.pk,
                    "nombre": row.nombre,
                    "apellido": row.apellido,
                    "documento": str(row.documento_pasaporte or row.documento or ""),
                    "fecha_nacimiento": row.fecha_nacimiento,
                }
                for row in items
            ],
        )


class InetInscribirView(InetAPIView):
    resource = "comisiones"

    @extend_schema(
        request=InetInscripcionInputSerializer, responses={201: InetItemSerializer}
    )
    @transaction.atomic
    def post(self, request, pk):
        comision = self.get_item(pk)
        from VAT.services.access_scope import can_user_edit_centro

        if not user_has_permission_code(
            request.user, "VAT.add_inscripcion"
        ) or not can_user_edit_centro(request.user, comision.curso.centro):
            raise PermissionDenied()
        serializer = InetInscripcionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data.get("ciudadano_id"):
            ciudadano = get_object_or_404(Ciudadano, pk=data["ciudadano_id"])
        else:
            values = data.get("ciudadano", {})
            if values.get("tipo_registro_identidad") == Ciudadano.TIPO_REGISTRO_SIN_DNI:
                form = InetSinDniForm(form_data(values))
            else:
                form = InetCiudadanoForm(form_data(values))
            validate_form(form)
            ciudadano = form.save(commit=False)
            ciudadano.creado_por = ciudadano.modificado_por = request.user
            ciudadano.origen_dato = "manual"
            ciudadano.save()
        try:
            item = InscripcionService.crear_inscripcion(
                ciudadano=ciudadano,
                comision=comision,
                programa=comision.curso.programa,
                estado="inscripta",
                origen_canal="backoffice",
                observaciones=data.get("observaciones", ""),
                usuario=request.user,
            )
        except (ValueError, IntegrityError) as error:
            raise ValidationError(
                {
                    "detail": (
                        str(error)
                        if isinstance(error, ValueError)
                        else "La inscripción ya existe."
                    )
                }
            ) from error
        return Response(serialize_item("inscripciones", item, request.user), status=201)


class InetEstadoView(InetAPIView):
    resource = "inscripciones"

    @extend_schema(responses=InetFormSerializer)
    def get(self, request, pk):
        item = self.get_item(pk)
        self.check_write(item)
        form = InscripcionForm(instance=item)
        result = serialize_form(form)
        result["fields"] = [
            field
            for field in result["fields"]
            if field["name"] in ("estado", "observaciones")
        ]
        return Response(result)

    @extend_schema(request=InetEstadoInputSerializer, responses=InetItemSerializer)
    @transaction.atomic
    def post(self, request, pk):
        item = self.get_item(pk)
        self.check_write(item)
        serializer = InetEstadoInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            item = InscripcionService.actualizar_estado_inscripcion(
                inscripcion=item,
                nuevo_estado=serializer.validated_data["estado"],
                usuario=request.user,
            )
        except ValueError as error:
            raise ValidationError({"estado": [str(error)]}) from error
        if "observaciones" in serializer.validated_data:
            item.observaciones = serializer.validated_data["observaciones"]
            item.save(update_fields=["observaciones"])
        return Response(serialize_item("inscripciones", item, request.user))


class InetAsistenciaView(InetAPIView):
    resource = "sesiones"

    @extend_schema(responses=InetAsistenciaSerializer)
    def get(self, request, pk):
        sesion = self.get_item(pk)
        existing = {row.inscripcion_id: row for row in sesion.asistencias.all()}
        rows = []
        for item in (
            models.Inscripcion.objects.filter(
                comision_curso=sesion.comision_curso,
                estado__in=("inscripta", "validada_presencial"),
            )
            .select_related("ciudadano")
            .order_by("ciudadano__apellido", "ciudadano__nombre")
        ):
            attendance = existing.get(item.pk)
            rows.append(
                {
                    "inscripcion_id": item.pk,
                    "nombre": item.ciudadano.nombre_completo,
                    "documento": str(
                        item.ciudadano.documento_pasaporte
                        or item.ciudadano.documento
                        or "Sin DNI"
                    ),
                    "presente": attendance.presente if attendance else None,
                    "observaciones": (
                        attendance.observaciones or "" if attendance else ""
                    ),
                }
            )
        return Response({"sesion_id": sesion.pk, "fecha": sesion.fecha, "filas": rows})

    @extend_schema(request=InetAsistenciaSerializer, responses={204: None})
    def put(self, request, pk):
        sesion = self.get_item(pk)
        self.check_write(sesion)
        serializer = InetAsistenciaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        guardar_asistencia(sesion, serializer.validated_data["filas"], request.user)
        return Response(status=204)
