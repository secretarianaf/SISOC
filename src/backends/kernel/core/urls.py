from django.urls import path

from core.views import (
    changelog_view,
    mapa_arquitectura_datos,
    mapa_arquitectura_view,
    columnas_preferencias,
    detalle_filtro_favorito,
    filtros_favoritos,
    inicio_view,
    load_localidad,
    load_municipios,
    ProgramaListView,
    ProgramaCreateView,
    ProgramaDetailView,
    ProgramaUpdateView,
    ProgramaDeleteView,
)
from .trash_views import (
    TrashListView,
    TrashRestorePreviewView,
    TrashRestoreView,
)


urlpatterns = [
    path("inicio/", inicio_view, name="inicio"),
    path("novedades/", changelog_view, name="changelog"),
    path("arquitectura/", mapa_arquitectura_view, name="mapa_arquitectura"),
    path(
        "arquitectura/grafo.json",
        mapa_arquitectura_datos,
        name="mapa_arquitectura_datos",
    ),
    path(
        "ajax/load-municipios/",
        load_municipios,
        name="ajax_load_municipios",
    ),
    path(
        "ajax/load-localidades/",
        load_localidad,
        name="ajax_load_localidades",
    ),
    path(
        "ajax/filtros-favoritos/",
        filtros_favoritos,
        name="filtros_favoritos",
    ),
    path(
        "ajax/filtros-favoritos/<int:pk>/",
        detalle_filtro_favorito,
        name="detalle_filtro_favorito",
    ),
    path(
        "ajax/columnas-preferencias/",
        columnas_preferencias,
        name="column_preferences",
    ),
    path("programas/", ProgramaListView.as_view(), name="programa_listar"),
    path("programas/crear/", ProgramaCreateView.as_view(), name="programa_crear"),
    path("programas/<int:pk>/", ProgramaDetailView.as_view(), name="programa_detalle"),
    path(
        "programas/<int:pk>/editar/",
        ProgramaUpdateView.as_view(),
        name="programa_editar",
    ),
    path(
        "programas/<int:pk>/eliminar/",
        ProgramaDeleteView.as_view(),
        name="programa_eliminar",
    ),
    path("papelera/", TrashListView.as_view(), name="papelera_list"),
    path(
        "papelera/preview-restore/<str:app_label>/<str:model_name>/<int:pk>/",
        TrashRestorePreviewView.as_view(),
        name="papelera_preview_restore",
    ),
    path(
        "papelera/restore/<str:app_label>/<str:model_name>/<int:pk>/",
        TrashRestoreView.as_view(),
        name="papelera_restore",
    ),
]
