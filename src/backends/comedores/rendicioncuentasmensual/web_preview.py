"""React entries for the native Rendiciones routes.

The activation registry mounts these entries for Comedores when a SISOC
build is available. Each entry keeps the native URL and its guard. The lists
keep the native page validation and the global CSV stays a native download.
Assets are served under ``/rendicioncuentasmensual/react/``.
"""

from pathlib import Path

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from core.decorators import permissions_any_required
from comedores.models import Comedor
from comedores.web_preview_catalogos import (
    BUILD_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)
from rendicioncuentasmensual.auditoria import AuditoriaService
from rendicioncuentasmensual.urls import _RENDICION_ACCESS_PERMS
from rendicioncuentasmensual.urls import _RENDICION_PERM
from rendicioncuentasmensual.views import (
    RendicionCuentaMensualDetailView,
    RendicionCuentaMensualGlobalListView,
    RendicionCuentaMensualListView,
)
from rendicioncuentasmensual.views import (
    RendicionCuentaMensualCreateView,
    RendicionCuentaMensualDeleteView,
    RendicionAuditoriaView,
    RendicionCuentaMensualUpdateView,
)

PUBLIC_ASSETS = "/rendicioncuentasmensual/react/assets/"
PERMISO_AUDITORIA = ["rendicioncuentasmensual.manage_auditoria_stage"]


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


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PorComedorEntry(RendicionCuentaMensualListView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        # Validate the comedor and page without evaluating the projected rows.
        self.object_list = self.get_queryset()
        try:
            self.get_context_data()
        except Comedor.DoesNotExist as exc:
            raise Http404 from exc
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DetalleEntry(RendicionCuentaMensualDetailView):
    """Detail (RM01.01): a GET gets the frozen index, every POST stays the native one."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        # Same Http404 as the native detail for a missing or deleted rendición.
        self.object = self.get_object()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class NuevaEntry(RendicionCuentaMensualCreateView):
    """Create form (RM01.02): the native GET has no lookup, every POST stays native."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EditarEntry(RendicionCuentaMensualUpdateView):
    """Data form (RM01.02): the native dispatch keeps its extra permission check."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        # Same Http404 as the native form for a missing or deleted rendición.
        self.object = self.get_object()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class BajaEntry(RendicionCuentaMensualDeleteView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class AuditoriaEntry(RendicionAuditoriaView):
    """Audit search and form (RM01.03): the native redirect and 404 first, then the index."""

    index_bytes = b""

    def get(self, request, pk=None):
        if pk is None and request.GET.get("rendicion"):
            # ``?rendicion=<id>``: the native redirect to the audit form, or its 404.
            return super().get(request, pk=pk)
        if pk is not None:
            get_object_or_404(AuditoriaService.disponibles(), pk=pk)
        return _index(request, self.index_bytes)


def rendicion_preview_patterns(build_directory):
    """Freeze an explicit ``apps/sisoc`` build for the React route overrides.

    The caller supplies the build directory, never a request path.
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
            "rendicioncuentasmensual/rendicioncuentasmensual/<int:comedor_id>/",
            permissions_any_required(_RENDICION_ACCESS_PERMS)(
                PorComedorEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "rendicioncuentasmensual/rendicioncuentasmensual/detalle/<int:pk>/",
            permissions_any_required(_RENDICION_ACCESS_PERMS)(
                DetalleEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "rendicioncuentasmensual/rendicioncuentasmensual/nuevo/<int:comedor_id>/",
            permissions_any_required(_RENDICION_PERM)(
                NuevaEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "rendicioncuentasmensual/rendicioncuentasmensual/editar/<int:pk>/",
            permissions_any_required(_RENDICION_PERM)(
                EditarEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "rendicioncuentasmensual/rendicioncuentasmensual/eliminar/<int:pk>/",
            permissions_any_required(_RENDICION_PERM)(
                BajaEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "rendicioncuentasmensual/rendicioncuentasmensual/auditoria/",
            permissions_any_required(PERMISO_AUDITORIA)(
                AuditoriaEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "rendicioncuentasmensual/rendicioncuentasmensual/auditoria/<int:pk>/",
            permissions_any_required(PERMISO_AUDITORIA)(
                AuditoriaEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "rendicioncuentasmensual/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
