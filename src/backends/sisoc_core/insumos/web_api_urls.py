"""Session-authenticated INS-A read routes owned by Insumos."""

from django.urls import include, path

from insumos.web_api_views import (
    InsumosWebCreateView,
    InsumosWebDeleteView,
    InsumosWebEditView,
    InsumosWebListView,
    InsumosWebOptionsView,
)

urlpatterns = [
    path("categorias/", include("insumos.web_categoria_api_urls")),
    path("", InsumosWebListView.as_view(), name="web_insumos_list"),
    path("options/", InsumosWebOptionsView.as_view(), name="web_insumos_options"),
    path("crear/", InsumosWebCreateView.as_view(), name="web_insumos_create"),
    path("<int:pk>/editar/", InsumosWebEditView.as_view(), name="web_insumos_edit"),
    path(
        "<int:pk>/eliminar/", InsumosWebDeleteView.as_view(), name="web_insumos_delete"
    ),
]
