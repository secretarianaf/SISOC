"""Explicit local React preview of the Actas tab; never mounted by a production URLconf.

The entries keep the native URLs (``/inspecciones/actas/`` and
``/inspecciones/actas/<numero>/``) and the native views' dispatch: anonymous
users go to the login, users without ``puede_gestionar`` get the native 403
and an invalid page or a missing acta the native 404. Only then the GET
returns the frozen React ``index.html``, which loads its data from
``/api/web/inspecciones/``. Assets stay under the backend's own prefix
(``/inspecciones/react/``), so the core forwards them like any other route.
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

from inspecciones.views_actas import ActaDetalleView, ActasView
from inspecciones.views_escuelas import (
    EscuelaCrearView,
    EscuelaEditarView,
    EscuelasView,
)

BUILD_ASSETS = "/v2/sisoc/assets/"
PUBLIC_ASSETS = "/inspecciones/react/assets/"
ASSET_SUFFIXES = {".js", ".css", ".woff", ".woff2", ".svg", ".png", ".jpg", ".ico"}


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ActasEntry(ActasView):
    """Native guards and page validation, then the frozen React index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        # Same Http404 as the native list for a page that does not exist.
        self.paginate_queryset(self.object_list, self.get_paginate_by(self.object_list))
        response = HttpResponse(
            b"" if request.method == "HEAD" else self.index_bytes,
            content_type="text/html; charset=utf-8",
        )
        response["Content-Length"] = str(len(self.index_bytes))
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response


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
class ActaDetalleEntry(ActaDetalleView):
    """Native guards and the native 404 of a missing acta, then the frozen index."""

    http_method_names = ["get", "head"]
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.get_acta()
        return _index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EscuelasEntry(EscuelasView):
    """Native guards and the native 404 of an invalid page, then the frozen index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        self.paginate_queryset(self.object_list, self.get_paginate_by(self.object_list))
        return _index_response(request, self.index_bytes)


def _escuela_form_entry(vista, request):
    """GET of a school form page: native guards (and the edit 404), then the index."""
    vista.get_form_kwargs()
    return _index_response(request, vista.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EscuelaNuevaEntry(EscuelaCrearView):
    """``/inspecciones/escuelas/nueva/`` as a page; its POST stays native."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _escuela_form_entry(self, request)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EscuelaEditarEntry(EscuelaEditarView):
    """``/inspecciones/escuelas/<pk>/editar/`` as a page; its POST stays native."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _escuela_form_entry(self, request)


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
        raise ValueError("Actas preview assets must not be symlinks")
    assets = {}
    for file in asset_root.rglob("*"):
        if not file.is_file() or file.suffix not in ASSET_SUFFIXES:
            continue
        if file.is_symlink() or not file.resolve().is_relative_to(root):
            raise ValueError("Actas preview assets must stay inside the build")
        body = file.read_bytes()
        content_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        assets[file.relative_to(root).as_posix()] = (
            body,
            content_type,
            hashlib.sha256(body).hexdigest(),
        )
    return MappingProxyType(assets)


def actas_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Actas preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path("inspecciones/actas/", ActasEntry.as_view(index_bytes=index_bytes)),
        path(
            "inspecciones/actas/<str:numero>/",
            ActaDetalleEntry.as_view(index_bytes=index_bytes),
        ),
        path("inspecciones/", EscuelasEntry.as_view(index_bytes=index_bytes)),
        path(
            "inspecciones/escuelas/nueva/",
            EscuelaNuevaEntry.as_view(index_bytes=index_bytes),
        ),
        path(
            "inspecciones/escuelas/<int:pk>/editar/",
            EscuelaEditarEntry.as_view(index_bytes=index_bytes),
        ),
        path(
            "inspecciones/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
