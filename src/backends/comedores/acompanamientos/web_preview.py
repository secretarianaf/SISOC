"""Explicit local React preview of the acompañamiento list and ficha (AC01).

Never mounted by a production URLconf. Each entry keeps the native URL, the
native route decorator and the native view's dispatch (login, scope): users the
decorator rejects get the native 403, a comedor outside the user's scope or an
invalid page the native 404. Only then a GET returns the frozen React
``index.html``, which loads its data from ``/api/web/comedores/acompanamientos/``.
The CSV export, the AJAX endpoint and the native ``restaurar-hito`` POST are not
listed here and stay native. Assets are served under the backend's own prefix
``/acompanamientos/react/``.
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
from acompanamientos.views import (
    AcompanamientoDetailView,
    ComedoresAcompanamientoListView,
)

PUBLIC_ASSETS = "/acompanamientos/react/assets/"
VIEW_PERMISSIONS = ["acompanamientos.view_informacionrelevante"]


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ListEntry(ComedoresAcompanamientoListView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        # Same Http404 as the native list for a page that does not exist.
        self.paginate_queryset(self.object_list, self.get_paginate_by(self.object_list))
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DetailEntry(AcompanamientoDetailView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        # Scoped lookup: a comedor outside the user's scope is the native 404.
        self.object = self.get_object()
        return _index(request, self.index_bytes)


def acompanamientos_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Acompanamientos preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )

    def entry(vista):
        return permissions_any_required(VIEW_PERMISSIONS)(
            vista.as_view(index_bytes=index_bytes)
        )

    return [
        path("acompanamientos/acompanamiento/", entry(ListEntry)),
        path(
            "acompanamientos/acompanamiento/<int:comedor_id>/detalle/",
            entry(DetailEntry),
        ),
        path(
            "acompanamientos/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
