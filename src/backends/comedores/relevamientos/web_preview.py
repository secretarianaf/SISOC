"""Explicit local React preview of the relevamiento list and detail (R01.01); never mounted by a production URLconf.

The entries keep the native URLs, their route decorator and the native views'
dispatch: anonymous users and users without ``view_relevamiento`` get the
native 403, an unknown comedor (list) or relevamiento (detail, including soft
deleted ones) the native 404. Only then a GET returns the frozen React
``index.html``, which loads its data from ``/api/web/comedores/relevamientos/``.
POSTs reach the native views. Assets are served under the backend's own prefix
``/comedores/react/relevamientos/``.
"""

from pathlib import Path

from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from comedores.models import Comedor
from comedores.web_preview_catalogos import (
    BUILD_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)
from core.decorators import permissions_any_required
from relevamientos.views.web_views import RelevamientoDetailView, RelevamientoListView
from relevamientos.web_api_views import VIEW_PERMISSIONS

PUBLIC_ASSETS = "/comedores/react/relevamientos/assets/"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ListadoEntry(RelevamientoListView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        # Same Http404 as the native list for an unknown comedor.
        get_object_or_404(Comedor, pk=self.kwargs["comedor_pk"])
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DetalleEntry(RelevamientoDetailView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        # Same Http404 as the native detail outside its queryset.
        self.get_object()
        return _index(request, self.index_bytes)


def relevamientos_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Relevamientos preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    guard = permissions_any_required(VIEW_PERMISSIONS)
    return [
        path(
            "comedores/<comedor_pk>/relevamiento/listar",
            guard(ListadoEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "comedores/<comedor_pk>/relevamiento/<int:pk>",
            guard(DetalleEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "comedores/react/relevamientos/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
