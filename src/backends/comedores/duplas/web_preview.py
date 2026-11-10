"""Explicit local React preview of the Duplas screens; never mounted by a production URLconf.

Each entry keeps the native URL (``/equipo-tecnico/...``), the native URL
guard (``permissions_any_required(["auth.role_admin"])``) and the native view's
dispatch: a user without the role gets the native 403, an invalid page or a
missing equipo the native 404. Only then the GET returns the frozen React
``index.html``, which loads its data from ``/api/web/comedores/duplas/``.
Assets stay under the backend's own prefix (``/equipo-tecnico/react/``), so
the core forwards them like any other route.

The asset handling mirrors ``inspecciones.web_preview`` (verticals cannot
import each other).
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

from core.decorators import permissions_any_required
from duplas.views import DuplaDetailView, DuplaListView

BUILD_ASSETS = "/v2/sisoc/assets/"
PUBLIC_ASSETS = "/equipo-tecnico/react/assets/"
ASSET_SUFFIXES = {".js", ".css", ".woff", ".woff2", ".svg", ".png", ".jpg", ".ico"}
ADMIN = ["auth.role_admin"]


def _index_response(request, index_bytes):
    response = HttpResponse(
        b"" if request.method == "HEAD" else index_bytes,
        content_type="text/html; charset=utf-8",
    )
    response["Content-Length"] = str(len(index_bytes))
    patch_cache_control(response, private=True, no_store=True)
    patch_vary_headers(response, ("Cookie",))
    return response


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ListEntry(DuplaListView):
    """Native guards and page validation, then the frozen React index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        # Same Http404 as the native list for a page that does not exist.
        self.paginate_queryset(self.object_list, self.get_paginate_by(self.object_list))
        return _index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DetailEntry(DuplaDetailView):
    """Native guards and object lookup (404), then the frozen React index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return _index_response(request, self.index_bytes)


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
        raise ValueError("Duplas preview assets must not be symlinks")
    assets = {}
    for file in asset_root.rglob("*"):
        if not file.is_file() or file.suffix not in ASSET_SUFFIXES:
            continue
        if file.is_symlink() or not file.resolve().is_relative_to(root):
            raise ValueError("Duplas preview assets must stay inside the build")
        body = file.read_bytes()
        content_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        assets[file.relative_to(root).as_posix()] = (
            body,
            content_type,
            hashlib.sha256(body).hexdigest(),
        )
    return MappingProxyType(assets)


def frozen_index(build_directory):
    """Read a fixed ``index.html`` and point its assets to the public prefix."""
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Duplas preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return root, index_bytes


def _guarded(view):
    return permissions_any_required(ADMIN)(view)


def duplas_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    root, index_bytes = frozen_index(build_directory)
    return [
        path(
            "equipo-tecnico/",
            _guarded(ListEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "equipo-tecnico/<int:pk>/",
            _guarded(DetailEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "equipo-tecnico/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
