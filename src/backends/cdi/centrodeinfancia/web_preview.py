"""Explicit local React preview of CDI screens; never mounted by a production URLconf.

Each entry keeps the native URL and the native guards: the same
``permissions_any_required`` decorator as ``centrodeinfancia/urls.py`` and the
native view's own dispatch (login, scope). Only then the GET returns the frozen
React ``index.html``, which loads its data from ``/api/web/cdi/``. Other
methods keep the native behaviour. Assets stay under the backend's own prefix
(``/centrodeinfancia/react/``), so the core forwards them like any other route.
"""

import hashlib
import mimetypes
from pathlib import Path
from types import MappingProxyType

from django.http import HttpResponse
from django.urls import path
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie

from centrodeinfancia.views import (
    CentroDeInfanciaListView,
    NominaCentroInfanciaDestinatariosDetailView,
    ObservacionCentroInfanciaCreateView,
    ObservacionCentroInfanciaDeleteView,
    ObservacionCentroInfanciaDetailView,
    ObservacionCentroInfanciaUpdateView,
)
from centrodeinfancia.views_reportes import ReportesCDIView
from core.decorators import permissions_any_required

BUILD_ASSETS = "/v2/sisoc/assets/"
PUBLIC_ASSETS = "/centrodeinfancia/react/assets/"
ASSET_SUFFIXES = {".js", ".css", ".woff", ".woff2", ".svg", ".png", ".jpg", ".ico"}


def index_response(request, index_bytes):
    response = HttpResponse(
        b"" if request.method == "HEAD" else index_bytes,
        content_type="text/html; charset=utf-8",
    )
    response["Content-Length"] = str(len(index_bytes))
    patch_cache_control(response, private=True, no_store=True)
    patch_vary_headers(response, ("Cookie",))
    return response


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ReportesEntry(ReportesCDIView):
    """Native login and permission guards, then the frozen React index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CentrosListEntry(CentroDeInfanciaListView):
    """Native guards, then the page check (an invalid ``page`` is 404), then the index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        self.get_context_data()
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class NominaDestinatarioEntry(NominaCentroInfanciaDestinatariosDetailView):
    """Native guards and both scoped objects (404), then the index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.get_context_data()
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ObservacionCrearEntry(ObservacionCentroInfanciaCreateView):
    """Native guards and the scoped centre (404), then the index; POST stays native."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = None
        self.get_context_data()
        return index_response(request, self.index_bytes)


def _object_entry_get(view, request, *args, **kwargs):
    """GET resolves the scoped observation (404) like the native view, then the index."""
    view.object = view.get_object()
    return index_response(request, view.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ObservacionDetalleEntry(ObservacionCentroInfanciaDetailView):
    """Detail entry; the native view only answers GET/HEAD."""

    index_bytes = b""
    get = _object_entry_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ObservacionEditarEntry(ObservacionCentroInfanciaUpdateView):
    """Edit entry; POST stays the native form (with the CDI-A3 veto)."""

    index_bytes = b""
    get = _object_entry_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ObservacionEliminarEntry(ObservacionCentroInfanciaDeleteView):
    """Delete confirmation entry; POST stays the native soft delete."""

    index_bytes = b""
    get = _object_entry_get


class ReactAssetView(View):
    """Serve only frozen build assets; no request data reaches a static upstream."""

    http_method_names = ["get", "head"]
    assets = None

    def get(self, request, asset_path):
        asset = self.assets.get(asset_path) if self.assets is not None else None
        if request.META.get("QUERY_STRING") or asset is None:
            return HttpResponse(status=404)
        body, content_type, digest = asset
        response = HttpResponse(
            b"" if request.method == "HEAD" else body, content_type=content_type
        )
        response["Content-Length"] = str(len(body))
        response["ETag"] = f'"{digest}"'
        response["Cache-Control"] = "public, max-age=31536000, immutable"
        response["X-Content-Type-Options"] = "nosniff"
        return response


def _frozen_assets(root):
    asset_root = root / "assets"
    if asset_root.is_symlink():
        raise ValueError("CDI preview assets must not be symlinks")
    assets = {}
    for file in asset_root.rglob("*"):
        if not file.is_file() or file.suffix not in ASSET_SUFFIXES:
            continue
        if file.is_symlink() or not file.resolve().is_relative_to(root):
            raise ValueError("CDI preview assets must stay inside the build")
        body = file.read_bytes()
        content_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        assets[file.relative_to(root).as_posix()] = (
            body,
            content_type,
            hashlib.sha256(body).hexdigest(),
        )
    return MappingProxyType(assets)


def _entry(view_class, permission, index_bytes):
    return permissions_any_required([permission])(
        view_class.as_view(index_bytes=index_bytes)
    )


def cdi_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("CDI preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path(
            "centrodeinfancia/reportes/",
            _entry(ReportesEntry, "auth.role_reportes_cdi", index_bytes),
        ),
        path(
            "centrodeinfancia/listar",
            _entry(
                CentrosListEntry,
                "centrodeinfancia.view_centrodeinfancia",
                index_bytes,
            ),
        ),
        path(
            "centrodeinfancia/<int:pk>/nomina/<int:nomina_id>/ver/",
            _entry(
                NominaDestinatarioEntry,
                "centrodeinfancia.view_centrodeinfancia",
                index_bytes,
            ),
        ),
        path(
            "centrodeinfancia/<int:pk>/observacion/crear/",
            _entry(
                ObservacionCrearEntry,
                "centrodeinfancia.add_intervencioncentroinfancia",
                index_bytes,
            ),
        ),
        path(
            "centrodeinfancia/observacion/<int:pk>/",
            _entry(
                ObservacionDetalleEntry,
                "centrodeinfancia.view_centrodeinfancia",
                index_bytes,
            ),
        ),
        path(
            "centrodeinfancia/observacion/<int:pk>/editar/",
            _entry(
                ObservacionEditarEntry,
                "centrodeinfancia.change_intervencioncentroinfancia",
                index_bytes,
            ),
        ),
        path(
            "centrodeinfancia/observacion/<int:pk>/eliminar/",
            _entry(
                ObservacionEliminarEntry,
                "centrodeinfancia.delete_intervencioncentroinfancia",
                index_bytes,
            ),
        ),
        path(
            "centrodeinfancia/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
