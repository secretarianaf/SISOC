"""Explicit local React preview of the comunicados (CM03.01, CM02.01); never mounted by a production URLconf.

The entries keep the native URLs and the native views' dispatch: anonymous
users get the login redirect of ``LoginRequiredMixin``, an invalid ``page`` the
native 404 and an id outside the native detail queryset the native 404. Only
then a GET returns the frozen React ``index.html``, which loads its data from
``/api/web/comedores/comunicados/``. The management list (CM02.01) keeps the
native 403 for users without ``can_manage_comunicados``; the detail serves
both variants (reader, and manager with its footer). Assets
are served under the backend's own prefix ``/comunicados/react/``.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from comedores.web_preview_catalogos import (
    BUILD_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)
from comunicados.views import (
    ComunicadoDetailView,
    ComunicadoGestionListView,
    ComunicadoListView,
)

PUBLIC_ASSETS = "/comunicados/react/assets/"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ListadoEntry(ComunicadoListView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        # Same Http404 as the native list for an invalid or out-of-range page.
        self.paginate_queryset(self.object_list, self.get_paginate_by(self.object_list))
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class GestionEntry(ComunicadoGestionListView):
    """Native ``dispatch`` (403 without management) and paginator 404 first."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        self.paginate_queryset(self.object_list, self.get_paginate_by(self.object_list))
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DetalleEntry(ComunicadoDetailView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        # Same Http404 as the native detail outside its queryset.
        self.get_object()
        return _index(request, self.index_bytes)


def comunicados_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Comunicados preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path("comunicados/", ListadoEntry.as_view(index_bytes=index_bytes)),
        path("comunicados/gestion/", GestionEntry.as_view(index_bytes=index_bytes)),
        path(
            "comunicados/ver/<int:pk>/",
            DetalleEntry.as_view(index_bytes=index_bytes),
        ),
        path(
            "comunicados/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
