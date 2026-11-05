"""Session-only read APIs for INS-A; legacy routes remain unchanged."""

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
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.web_api_views import WebSessionSchema
from usuarios.web_session import resolve_web_access
from core.templatetags.custom_filters import has_perm_code
from insumos.services import get_categorias_queryset, get_insumos_queryset
from insumos.web_api_serializers import InsumoPageSerializer, InsumosOptionsSerializer


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
