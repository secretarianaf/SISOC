"""Explicit local React preview of the admision circuit pages (AD03.01, AD03.02).

Never mounted by a production URLconf. Each entry keeps the native URL, the
native route decorator (``permissions_any_required``) and the native view's
dispatch and queryset: users the decorator rejects get the native 403, an
invalid page the native 404. Only then a GET returns the frozen React
``index.html``, which loads its data from ``/api/web/comedores/admisiones/``.
The native ``post()`` handlers are untouched.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from core.decorators import permissions_any_required
from comedores.web_preview_catalogos import (
    BUILD_ASSETS,
    PUBLIC_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)
from admisiones.views.web_views import (
    AdmisionDetailView,
    AdmisionesLegalesListView,
    AdmisionesTecnicosListView,
    AdmisionesTecnicosUpdateView,
)
from admisiones.web_api_listas import LEGALES_PERMISSIONS, TECNICOS_PERMISSIONS


def _serve_list(vista, request):
    """The native queryset and pagination checks, then the frozen index."""
    vista.object_list = vista.get_queryset()
    # Same Http404 as the native list for a page that does not exist.
    vista.paginate_queryset(vista.object_list, vista.get_paginate_by(vista.object_list))
    return _index(request, vista.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class TecnicosListEntry(AdmisionesTecnicosListView):
    """GET serves the index after the native checks."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _serve_list(self, request)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class LegalesListEntry(AdmisionesLegalesListView):
    """GET serves the index after the native checks."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _serve_list(self, request)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DetalleEntry(AdmisionDetailView):
    """GET serves the index after the native lookup; the native ``post()`` stays."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EditorEntry(AdmisionesTecnicosUpdateView):
    """GET serves the index after the native lookup.

    While the native page draws the embedded report and cover form (the technician can edit
    the report) the native page itself is served, so that no control is left inert; the
    native ``post()`` stays for it.
    """

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        if context.get("informe_form"):
            return self.render_to_response(context)
        return _index(request, self.index_bytes)


def seguimiento_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf."""
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Admision preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )

    def entry(vista, permisos):
        return permissions_any_required(permisos)(
            vista.as_view(index_bytes=index_bytes)
        )

    return [
        path(
            "comedores/admisiones/tecnicos/listar",
            entry(TecnicosListEntry, TECNICOS_PERMISSIONS),
        ),
        path(
            "comedores/admisiones/legales/listar",
            entry(LegalesListEntry, LEGALES_PERMISSIONS),
        ),
        path(
            "comedores/<int:comedor_pk>/admision/<int:pk>/detalle/",
            entry(DetalleEntry, TECNICOS_PERMISSIONS),
        ),
        path(
            "comedores/admisiones/tecnicos/editar/<int:pk>",
            entry(EditorEntry, TECNICOS_PERMISSIONS),
        ),
        path(
            "comedores/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
