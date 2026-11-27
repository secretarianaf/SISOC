"""Explicit local React preview of the relevamiento pages (R01.01, R03.01, R02.01); never mounted by a production URLconf.

The entries keep the native URLs, their route decorator and the native views'
dispatch: anonymous users and users without ``view_relevamiento`` get the
native 403, an unknown comedor (list) or relevamiento (detail, including soft
deleted ones) the native 404. Only then a GET returns the frozen React
``index.html``, which loads its data from ``/api/web/comedores/relevamientos/``.
POSTs reach the native views. Assets are served under the backend's own prefix
``/comedores/react/`` (shared with the other comedores entries, routed to this backend).
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
from relevamientos.views.backoffice_views import (
    ActaComplementariaDetailView,
    ActaComplementariaFormView,
    SeguimientoUpdateView,
    SeguimientoPnudDetailView,
)
from relevamientos.views.seguimiento_helpers import (
    resolver_seguimiento,
    seguimiento_queryset,
)
from relevamientos.views.web_views import (
    PrimerSeguimientoDetailView,
    RelevamientoCreateView,
    RelevamientoDeleteView,
    RelevamientoDetailView,
    RelevamientoListView,
    RelevamientoUpdateView,
)
from relevamientos.web_api_views import VIEW_PERMISSIONS

PUBLIC_ASSETS = "/comedores/react/assets/"


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


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SeguimientoEntry(PrimerSeguimientoDetailView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        # Same Http404 as the native view (also the alias without instances).
        self.get_object()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PnudEntry(SeguimientoPnudDetailView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.get_object()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ActaEntry(ActaComplementariaDetailView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.get_object()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EliminarEntry(RelevamientoDeleteView):
    """GET gets the React page after the native lookup; POST stays the native baja."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        # Same Http404 as the native confirmation (unknown or soft deleted).
        self.get_object()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SeguimientoEditarEntry(SeguimientoUpdateView):
    """GET gets the React page after the native lookup; POST stays the native editor."""

    index_bytes = b""

    def get(self, request, **kwargs):
        resolver_seguimiento(self.kwargs, seguimiento_queryset())
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ActaFormularioEntry(ActaComplementariaFormView):
    index_bytes = b""

    def get(self, request, **kwargs):
        self._cargar()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CrearRelevamientoEntry(RelevamientoCreateView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        get_object_or_404(Comedor, pk=self.kwargs["comedor_pk"])
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EditarRelevamientoEntry(RelevamientoUpdateView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
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
            "comedores/<int:comedor_pk>/relevamiento/crear",
            permissions_any_required(["relevamientos.add_relevamiento"])(
                CrearRelevamientoEntry.as_view(index_bytes=index_bytes)
            ),
            name="relevamiento_crear",
        ),
        path(
            "comedores/<int:comedor_pk>/relevamiento/<int:pk>/editar",
            permissions_any_required(["relevamientos.change_relevamiento"])(
                EditarRelevamientoEntry.as_view(index_bytes=index_bytes)
            ),
            name="relevamiento_editar",
        ),
        path(
            "comedores/<comedor_pk>/relevamiento/listar",
            guard(ListadoEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "comedores/<comedor_pk>/relevamiento/<int:pk>/eliminar",
            permissions_any_required(["relevamientos.change_relevamiento"])(
                EliminarEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "comedores/<comedor_pk>/relevamiento/<int:pk>",
            guard(DetalleEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "comedores/<int:comedor_pk>/relevamiento/<int:relevamiento_pk>/seguimiento/<int:pk>/",
            guard(SeguimientoEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "comedores/<int:comedor_pk>/relevamiento/<int:relevamiento_pk>/seguimiento/<int:pk>/editar",
            permissions_any_required(["relevamientos.change_primerseguimiento"])(
                SeguimientoEditarEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "comedores/<int:comedor_pk>/acta-complementaria/crear",
            permissions_any_required(["relevamientos.add_actacomplementaria"])(
                ActaFormularioEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "comedores/<int:comedor_pk>/acta-complementaria/<int:pk>/editar",
            permissions_any_required(["relevamientos.change_actacomplementaria"])(
                ActaFormularioEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "comedores/<int:comedor_pk>/relevamiento/<int:relevamiento_pk>/primer-seguimiento/",
            guard(SeguimientoEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "comedores/<int:comedor_pk>/seguimiento-pnud/<int:pk>",
            guard(PnudEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "comedores/<int:comedor_pk>/acta-complementaria/<int:pk>",
            guard(ActaEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "comedores/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
