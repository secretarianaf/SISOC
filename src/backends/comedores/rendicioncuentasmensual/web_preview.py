"""Explicit local React preview of the global list of rendiciones (RM01.01); never mounted by a production URLconf.

The entry keeps the native URL, its route decorator and the native view's
dispatch: anonymous users and users without one of the five codes get the
native 403, an invalid ``page`` the native 404 and ``?export=csv`` the native
CSV download (with its own export check). Only then a GET returns the frozen
React ``index.html``, which loads its data from
``/api/web/comedores/rendicioncuentasmensual/listado/``. Assets are served under
the backend's own prefix ``/rendicioncuentasmensual/react/``.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from core.decorators import permissions_any_required
from comedores.web_preview_catalogos import (
    BUILD_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)
from rendicioncuentasmensual.urls import _RENDICION_ACCESS_PERMS
from rendicioncuentasmensual.views import RendicionCuentaMensualGlobalListView

PUBLIC_ASSETS = "/rendicioncuentasmensual/react/assets/"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ListadoEntry(RendicionCuentaMensualGlobalListView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        if request.GET.get("export") == "csv":
            return super().get(request, *args, **kwargs)
        self.object_list = self.get_queryset()
        # Same Http404 as the native list for an invalid or out-of-range page.
        self.paginate_queryset(self.object_list, self.get_paginate_by(self.object_list))
        return _index(request, self.index_bytes)


def rendicion_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Rendiciones preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    listado = permissions_any_required(_RENDICION_ACCESS_PERMS)(
        ListadoEntry.as_view(index_bytes=index_bytes)
    )
    return [
        path("rendicioncuentasmensual/rendicioncuentasmensual/listado/", listado),
        path(
            "rendicioncuentasmensual/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
