"""Session-only category endpoints, preserving the existing Forms and services."""

from django.core.paginator import InvalidPage, Paginator
from django.urls import reverse
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser
from rest_framework.response import Response

from core.templatetags.custom_filters import has_perm_code
from insumos.forms import InsumoCategoriaForm
from insumos.models import InsumoCategoria
from insumos.services import (
    delete_categoria,
    get_categorias_queryset,
    save_categoria_from_form,
)
from insumos.web_api_serializers import (
    InsumoFormErrorsSerializer,
    InsumoMutationSuccessSerializer,
)
from insumos.web_api_views import InsumosWebMutationView
from insumos.web_categoria_api_serializers import (
    CategoriaConfirmationSerializer,
    CategoriaFormSerializer,
    CategoriaPageSerializer,
    CategoriaRequestSerializer,
)


class CategoriaWebView(InsumosWebMutationView):
    """Reuse prerequisite/session handling with category-specific permissions."""

    parser_classes = [FormParser]


class CategoriaWebListView(CategoriaWebView):
    permission_code = "insumos.view_insumocategoria"
    http_method_names = ["get", "head", "options"]

    @extend_schema(responses={200: CategoriaPageSerializer})
    def get(self, request):
        paginator = Paginator(get_categorias_queryset(), 20)
        number = request.query_params.get("page") or 1
        if number == "last":
            number = paginator.num_pages
        try:
            page = paginator.page(number)
        except InvalidPage as exc:
            raise NotFound("Página no válida.") from exc
        payload = {
            "count": paginator.count,
            "page": page.number,
            "page_size": 20,
            "pages": paginator.num_pages,
            "capabilities": {
                f"can_{action}": has_perm_code(
                    request.user, f"insumos.{action}_insumocategoria"
                )
                for action in ("add", "change", "delete")
            },
            "results": [
                {
                    "id": category.pk,
                    "nombre": category.nombre,
                    "programa": str(category.programa),
                    "orden": category.orden,
                    "activo": category.activo,
                }
                for category in page.object_list
            ],
        }
        return Response(CategoriaPageSerializer(payload).data)


def _category(pk):
    try:
        return get_categorias_queryset().get(pk=pk)
    except InsumoCategoria.DoesNotExist as exc:
        raise NotFound() from exc


def _metadata(form):
    initial = {}
    for name in ("programa", "nombre", "descripcion", "orden", "activo"):
        value = form[name].value()
        initial[name] = (
            bool(value)
            if name == "activo"
            else "" if value in (None, "") else str(value)
        )
    payload = {
        "initial": initial,
        "options": {
            "programa": [
                {"value": str(value), "label": str(label)}
                for value, label in form.fields["programa"].choices
            ]
        },
        "current_file": None,
    }
    return CategoriaFormSerializer(payload).data


def _save(form, message):
    if not form.is_valid():
        return Response({"errors": form.errors.get_json_data()}, status=400)
    save_categoria_from_form(form)
    return Response(
        {
            "ok": True,
            "message": message,
            "redirect": reverse("insumos_categorias_listar"),
        }
    )


class CategoriaWebCreateView(CategoriaWebView):
    permission_code = "insumos.add_insumocategoria"

    @extend_schema(responses={200: CategoriaFormSerializer})
    def get(self, request):
        return Response(_metadata(InsumoCategoriaForm()))

    @extend_schema(
        request=CategoriaRequestSerializer,
        responses={
            200: InsumoMutationSuccessSerializer,
            400: InsumoFormErrorsSerializer,
        },
    )
    def post(self, request):
        return _save(
            InsumoCategoriaForm(request.data), "Categoría creada correctamente."
        )


class CategoriaWebEditView(CategoriaWebView):
    permission_code = "insumos.change_insumocategoria"

    @extend_schema(responses={200: CategoriaFormSerializer})
    def get(self, request, pk):
        return Response(_metadata(InsumoCategoriaForm(instance=_category(pk))))

    @extend_schema(
        request=CategoriaRequestSerializer,
        responses={
            200: InsumoMutationSuccessSerializer,
            400: InsumoFormErrorsSerializer,
        },
    )
    def post(self, request, pk):
        return _save(
            InsumoCategoriaForm(request.data, instance=_category(pk)),
            "Categoría actualizada correctamente.",
        )


class CategoriaWebDeleteView(CategoriaWebView):
    permission_code = "insumos.delete_insumocategoria"

    @extend_schema(responses={200: CategoriaConfirmationSerializer})
    def get(self, request, pk):
        category = _category(pk)
        return Response({"id": category.pk, "nombre": category.nombre})

    @extend_schema(request=None, responses={200: InsumoMutationSuccessSerializer})
    def post(self, request, pk):
        # Parse even an unused body so unsupported transports cannot delete data.
        _ = request.data
        delete_categoria(_category(pk))
        return Response(
            {
                "ok": True,
                "message": "Categoría eliminada correctamente.",
                "redirect": reverse("insumos_categorias_listar"),
            }
        )
