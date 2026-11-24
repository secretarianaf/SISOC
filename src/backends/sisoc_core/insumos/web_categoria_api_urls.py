"""INS-B category routes, nested under the existing private Insumos API."""

from django.urls import path

from insumos.web_categoria_api_views import (
    CategoriaWebCreateView,
    CategoriaWebDeleteView,
    CategoriaWebEditView,
    CategoriaWebListView,
)

urlpatterns = [
    path("", CategoriaWebListView.as_view(), name="web_insumos_categorias_list"),
    path(
        "crear/", CategoriaWebCreateView.as_view(), name="web_insumos_categorias_create"
    ),
    path(
        "<int:pk>/editar/",
        CategoriaWebEditView.as_view(),
        name="web_insumos_categorias_edit",
    ),
    path(
        "<int:pk>/eliminar/",
        CategoriaWebDeleteView.as_view(),
        name="web_insumos_categorias_delete",
    ),
]
