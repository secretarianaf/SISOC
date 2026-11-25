"""Session-only read and form APIs for INS-A; legacy routes remain unchanged."""

from django.utils.cache import patch_cache_control, patch_vary_headers
from django.core.paginator import InvalidPage, Paginator
from django.db.models import Q
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.timezone import localtime
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotAuthenticated, NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.web_api_views import WebSessionSchema
from usuarios.web_session import resolve_web_access
from core.templatetags.custom_filters import has_perm_code
from insumos.forms import InsumoForm
from insumos.models import Insumo
from insumos.services import (
    delete_insumo,
    get_categorias_queryset,
    get_insumos_queryset,
    save_insumo_from_form,
)
from insumos.web_api_serializers import (
    InsumoCreateRequestSerializer,
    InsumoDeleteConfirmationSerializer,
    InsumoEditRequestSerializer,
    InsumoFormErrorsSerializer,
    InsumoFormSchema,
    InsumoMutationSuccessSerializer,
    InsumoPageSerializer,
    InsumosWebErrorSerializer,
    InsumosOptionsSerializer,
)


class WebPrerequisiteRequired(PermissionDenied):
    """Carry the existing prerequisite without coercing its nullable URL."""

    def __init__(self, access):
        self.access = access
        super().__init__("Debe completar el requisito de acceso web.")


class InsumosWebReadView(APIView):
    """Private cookie-authenticated transport, not an action-permission grant."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head", "options"]
    schema = WebSessionSchema()

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        access = resolve_web_access(request)
        if access.state != "ready":
            raise WebPrerequisiteRequired(access)
        if not has_perm_code(request.user, "insumos.view_insumo"):
            raise PermissionDenied()

    def get_authenticate_header(self, request):
        return "Session"

    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        if isinstance(exc, NotAuthenticated):
            response.data = {"detail": "Inicie sesión para continuar."}
        elif isinstance(exc, WebPrerequisiteRequired):
            response.data = {
                "detail": str(exc.detail),
                "state": exc.access.state,
                "required_action_url": exc.access.required_action_url,
            }
        return response

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response


class InsumosWebListView(InsumosWebReadView):
    @extend_schema(
        parameters=[
            OpenApiParameter("busqueda", OpenApiTypes.STR, OpenApiParameter.QUERY),
            OpenApiParameter("categoria", OpenApiTypes.STR, OpenApiParameter.QUERY),
            OpenApiParameter("page", OpenApiTypes.STR, OpenApiParameter.QUERY),
        ],
        responses={200: InsumoPageSerializer},
    )
    def get(self, request):
        queryset = get_insumos_queryset()
        category = (request.query_params.get("categoria") or "").strip()
        if category == "sin":
            queryset = queryset.filter(categoria__isnull=True)
        elif category.isdigit():
            queryset = queryset.filter(categoria_id=int(category))

        search = (request.query_params.get("busqueda") or "").strip()
        if search:
            queryset = queryset.filter(
                Q(titulo__icontains=search) | Q(descripcion__icontains=search)
            )

        paginator = Paginator(queryset, 20)
        number = request.query_params.get("page") or 1
        if number == "last":
            number = paginator.num_pages
        try:
            page = paginator.page(number)
        except InvalidPage as exc:
            raise NotFound("Página no válida.") from exc
        rows = [
            {
                "id": item.pk,
                "titulo": item.titulo,
                "activo": item.activo,
                "categoria": item.categoria_display,
                "fecha_carga": date_format(localtime(item.fecha_creacion), "d/m/Y H:i"),
                "cargado_por": item.creado_por_display,
                "download_url": reverse("insumos_descargar", args=[item.pk]),
            }
            for item in page.object_list
        ]
        return Response(
            InsumoPageSerializer(
                {
                    "count": paginator.count,
                    "page": page.number,
                    "page_size": 20,
                    "pages": paginator.num_pages,
                    "filters": {"busqueda": search, "categoria": category},
                    "results": rows,
                }
            ).data
        )


class InsumosWebOptionsView(InsumosWebReadView):
    @extend_schema(responses={200: InsumosOptionsSerializer})
    def get(self, request):
        categories = get_categorias_queryset().filter(activo=True)
        return Response(
            InsumosOptionsSerializer(
                {
                    "categories": [
                        {"id": category.pk, "nombre": category.nombre}
                        for category in categories
                    ]
                }
            ).data
        )


class InsumosWebMutationView(APIView):
    """Private session transport with an action-specific permission guard."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer]
    parser_classes = [MultiPartParser]
    http_method_names = ["get", "head", "post", "options"]
    schema = WebSessionSchema()
    permission_code = None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        access = resolve_web_access(request)
        if access.state != "ready":
            raise WebPrerequisiteRequired(access)
        if not has_perm_code(request.user, self.permission_code):
            raise PermissionDenied()

    def get_authenticate_header(self, request):
        return "Session"

    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        if isinstance(exc, NotAuthenticated):
            response.data = {"detail": "Inicie sesión para continuar."}
        elif isinstance(exc, WebPrerequisiteRequired):
            response.data = {
                "detail": str(exc.detail),
                "state": exc.access.state,
                "required_action_url": exc.access.required_action_url,
            }
        return response

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response


class InsumosWebCreateView(InsumosWebMutationView):
    permission_code = "insumos.add_insumo"

    @extend_schema(
        responses={
            200: InsumoFormSchema,
            401: InsumosWebErrorSerializer,
            403: InsumosWebErrorSerializer,
        }
    )
    def get(self, request):
        form = InsumoForm()
        return Response(_form_metadata(form))

    @extend_schema(
        request=InsumoCreateRequestSerializer,
        responses={
            200: InsumoMutationSuccessSerializer,
            400: InsumoFormErrorsSerializer,
            401: InsumosWebErrorSerializer,
            403: InsumosWebErrorSerializer,
            415: InsumosWebErrorSerializer,
        },
    )
    def post(self, request):
        form = InsumoForm(request.data, request.FILES)
        if not form.is_valid():
            return Response({"errors": form.errors.get_json_data()}, status=400)
        save_insumo_from_form(form, request.user)
        return Response(
            {
                "ok": True,
                "message": "Insumo creado correctamente.",
                "redirect": reverse("insumos_listar"),
            }
        )


class InsumosWebEditView(InsumosWebMutationView):
    permission_code = "insumos.change_insumo"

    def get_object(self, pk):
        try:
            return get_insumos_queryset().get(pk=pk)
        except Insumo.DoesNotExist as exc:
            raise NotFound() from exc

    @extend_schema(
        responses={
            200: InsumoFormSchema,
            401: InsumosWebErrorSerializer,
            403: InsumosWebErrorSerializer,
            404: InsumosWebErrorSerializer,
        }
    )
    def get(self, request, pk):
        instance = self.get_object(pk)
        form = InsumoForm(instance=instance)
        return Response(
            _form_metadata(
                form,
                instance,
                include_download=has_perm_code(request.user, "insumos.view_insumo"),
            )
        )

    @extend_schema(
        request=InsumoEditRequestSerializer,
        responses={
            200: InsumoMutationSuccessSerializer,
            400: InsumoFormErrorsSerializer,
            401: InsumosWebErrorSerializer,
            403: InsumosWebErrorSerializer,
            404: InsumosWebErrorSerializer,
            415: InsumosWebErrorSerializer,
        },
    )
    def post(self, request, pk):
        instance = self.get_object(pk)
        form = InsumoForm(request.data, request.FILES, instance=instance)
        if not form.is_valid():
            return Response({"errors": form.errors.get_json_data()}, status=400)
        save_insumo_from_form(form, request.user, instance=instance)
        return Response(
            {
                "ok": True,
                "message": "Insumo actualizado correctamente.",
                "redirect": reverse("insumos_listar"),
            }
        )


class InsumosWebDeleteView(InsumosWebMutationView):
    permission_code = "insumos.delete_insumo"

    def get_object(self, pk):
        try:
            return get_insumos_queryset().get(pk=pk)
        except Insumo.DoesNotExist as exc:
            raise NotFound() from exc

    @extend_schema(
        responses={
            200: InsumoDeleteConfirmationSerializer,
            401: InsumosWebErrorSerializer,
            403: InsumosWebErrorSerializer,
            404: InsumosWebErrorSerializer,
        }
    )
    def get(self, request, pk):
        instance = self.get_object(pk)
        return Response({"id": instance.pk, "titulo": instance.titulo})

    @extend_schema(
        request=None,
        responses={
            200: InsumoMutationSuccessSerializer,
            401: InsumosWebErrorSerializer,
            403: InsumosWebErrorSerializer,
            404: InsumosWebErrorSerializer,
        },
    )
    def post(self, request, pk):
        instance = self.get_object(pk)
        delete_insumo(instance)
        return Response(
            {
                "ok": True,
                "message": "Insumo eliminado correctamente.",
                "redirect": reverse("insumos_listar"),
            }
        )


def _form_metadata(form, instance=None, include_download=False):
    initial = {}
    for name in ("programa", "categoria", "titulo", "descripcion", "activo"):
        value = form[name].value()
        if name in ("programa", "categoria"):
            value = "" if value in (None, "") else str(value)
        elif name in ("titulo", "descripcion"):
            value = value or ""
        initial[name] = value
    options = {}
    for name in ("programa", "categoria"):
        field = form.fields[name]
        values = []
        for value, label in field.choices:
            option = {"value": str(value), "label": str(label)}
            if name == "categoria" and str(value):
                category = field.queryset.filter(pk=str(value)).first()
                if category is not None:
                    option["programa_id"] = str(category.programa_id)
            values.append(option)
        options[name] = values
    current_file = None
    if instance is not None and instance.archivo:
        current_file = {
            "name": instance.archivo.name.rsplit("/", 1)[-1],
            "download_url": None,
        }
        if include_download:
            current_file["download_url"] = reverse(
                "insumos_descargar", args=[instance.pk]
            )
    return {"initial": initial, "options": options, "current_file": current_file}
