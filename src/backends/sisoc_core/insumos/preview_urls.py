from django.urls import path, re_path

from core.decorators import permissions_any_required

from .preview_views import InsumosPreviewEntryView


def _preview(permission_code, asset_path=None):
    view_kwargs = {} if asset_path is None else {"asset_path": asset_path}
    return permissions_any_required([permission_code])(
        InsumosPreviewEntryView.as_view(**view_kwargs)
    )


urlpatterns = [
    path(
        "insumos/categorias/",
        _preview("insumos.view_insumocategoria", "insumos/categorias/"),
        name="insumos_categories_preview_list",
    ),
    path(
        "insumos/categorias/crear",
        _preview("insumos.add_insumocategoria", "insumos/categorias/crear"),
        name="insumos_categories_preview_create",
    ),
    re_path(
        r"^(?P<asset_path>insumos/categorias/[0-9]+/editar)$",
        _preview("insumos.change_insumocategoria"),
        name="insumos_categories_preview_edit",
    ),
    re_path(
        r"^(?P<asset_path>insumos/categorias/[0-9]+/eliminar)$",
        _preview("insumos.delete_insumocategoria"),
        name="insumos_categories_preview_delete",
    ),
    path(
        "insumos",
        _preview("insumos.view_insumo", "insumos"),
        name="insumos_preview_list_no_slash",
    ),
    path(
        "insumos/",
        _preview("insumos.view_insumo", "insumos/"),
        name="insumos_preview_list",
    ),
    path(
        "insumos/crear",
        _preview("insumos.add_insumo", "insumos/crear"),
        name="insumos_preview_create_no_slash",
    ),
    path(
        "insumos/crear/",
        _preview("insumos.add_insumo", "insumos/crear/"),
        name="insumos_preview_create",
    ),
    re_path(
        r"^(?P<asset_path>insumos/[0-9]+/editar/?)$",
        _preview("insumos.change_insumo"),
        name="insumos_preview_edit",
    ),
    re_path(
        r"^(?P<asset_path>insumos/[0-9]+/eliminar/?)$",
        _preview("insumos.delete_insumo"),
        name="insumos_preview_delete",
    ),
]
