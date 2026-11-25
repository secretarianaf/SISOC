"""Serve the existing Insumos SPA at the eight canonical HTML entries."""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from core.decorators import permissions_any_required
from core.web_preview_core_pages import ReactAssetView, _frozen_assets, _index

from .views import (
    InsumoCategoriaCreateView,
    InsumoCategoriaDeleteView,
    InsumoCategoriaListView,
    InsumoCategoriaUpdateView,
    InsumoCreateView,
    InsumoDeleteView,
    InsumoListView,
    InsumoUpdateView,
)


class _IndexMixin:
    index_bytes = b""

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return _index(request, self.index_bytes)


class _ListEntryMixin(_IndexMixin):
    def get(self, request, *args, **kwargs):
        if request.GET.get("page"):
            # Preserve the native 404 for an invalid page without rendering its template.
            self.get_context_data(object_list=self.get_queryset())
        return super().get(request, *args, **kwargs)


class _ObjectEntryMixin(_IndexMixin):
    def get(self, request, *args, **kwargs):
        self.get_object()
        return super().get(request, *args, **kwargs)


class _InsumoListEntry(_ListEntryMixin, InsumoListView):
    pass


class _InsumoCreateEntry(_IndexMixin, InsumoCreateView):
    pass


class _InsumoUpdateEntry(_ObjectEntryMixin, InsumoUpdateView):
    pass


class _InsumoDeleteEntry(_ObjectEntryMixin, InsumoDeleteView):
    pass


class _CategoriaListEntry(_ListEntryMixin, InsumoCategoriaListView):
    pass


class _CategoriaCreateEntry(_IndexMixin, InsumoCategoriaCreateView):
    pass


class _CategoriaUpdateEntry(_ObjectEntryMixin, InsumoCategoriaUpdateView):
    pass


class _CategoriaDeleteEntry(_ObjectEntryMixin, InsumoCategoriaDeleteView):
    pass


def insumos_preview_patterns(build_directory):
    """Shadow only the HTML entries; the Django names and downloads stay native."""
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Insumos requires a regular fixed index.html")
    html = index.read_bytes().replace(b"/v2/sisoc/assets/", b"/insumos/react/assets/")

    def entry(route, view, permission):
        return path(
            route,
            permissions_any_required([f"insumos.{permission}"])(
                view.as_view(index_bytes=html)
            ),
        )

    return [
        entry("insumos/", _InsumoListEntry, "view_insumo"),
        entry("insumos/crear", _InsumoCreateEntry, "add_insumo"),
        entry("insumos/<int:pk>/editar", _InsumoUpdateEntry, "change_insumo"),
        entry("insumos/<int:pk>/eliminar", _InsumoDeleteEntry, "delete_insumo"),
        entry("insumos/categorias/", _CategoriaListEntry, "view_insumocategoria"),
        entry("insumos/categorias/crear", _CategoriaCreateEntry, "add_insumocategoria"),
        entry(
            "insumos/categorias/<int:pk>/editar",
            _CategoriaUpdateEntry,
            "change_insumocategoria",
        ),
        entry(
            "insumos/categorias/<int:pk>/eliminar",
            _CategoriaDeleteEntry,
            "delete_insumocategoria",
        ),
        path(
            "insumos/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
