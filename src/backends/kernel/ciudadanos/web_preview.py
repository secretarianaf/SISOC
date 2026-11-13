"""Explicit local React preview of Ciudadano 360 (C05); never mounted by a production URLconf.

Every entry keeps the native URL and guards (login redirect, the native permission, the native
404) and only then returns the frozen React ``index.html``:

- ``ciudadanos/ver/<pk>``: the whole ficha, from ``/api/web/ciudadanos/<pk>/`` and the aportes of
  the verticals. Its ``Historial`` link stays native; ``Marcar revisado`` posts to
  ``/api/web/ciudadanos/<pk>/marcar-revisado/``.
- ``ciudadanos/eliminar/<pk>`` (C05.03), ``ciudadanos/<pk>/familiares/nuevo`` (C05.02),
  ``ciudadanos/crear/`` and ``ciudadanos/editar/<pk>`` (C05.02): their React pages.

Assets are served under ``/ciudadanos/react/``.
"""

import hashlib
import mimetypes
from pathlib import Path
from types import MappingProxyType

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.urls import path
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie

from ciudadanos.views import (
    CiudadanosCreateView,
    CiudadanosDeleteView,
    CiudadanosDetailView,
    CiudadanosUpdateView,
    GrupoFamiliarCreateView,
)

BUILD_ASSETS = "/v2/sisoc/assets/"
PUBLIC_ASSETS = "/ciudadanos/react/assets/"
ASSET_SUFFIXES = {".js", ".css", ".woff", ".woff2", ".svg", ".png", ".jpg", ".ico"}


def _index(request, index_bytes):
    response = HttpResponse(
        b"" if request.method == "HEAD" else index_bytes,
        content_type="text/html; charset=utf-8",
    )
    response["Content-Length"] = str(len(index_bytes))
    patch_cache_control(response, private=True, no_store=True)
    patch_vary_headers(response, ("Cookie",))
    return response


@method_decorator(ensure_csrf_cookie, name="dispatch")
class FichaEntry(CiudadanosDetailView):
    """Native login, permission and 404 first, then the frozen React index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class BajaEntry(CiudadanosDeleteView):
    """Native login, ``ciudadanos.delete_ciudadano`` and 404 first, then the frozen React index (C05.03)."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class FamiliarNuevoEntry(GrupoFamiliarCreateView):
    """Native 404 (ciudadano), login and ``change_ciudadano`` first, then the React index (C05.02)."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CrearEntry(CiudadanosCreateView):
    """Native login and ``add_ciudadano`` first, then the React index (C05.02).

    The RENAPER search of the native ``get`` is not run here: the page asks the web API for it.
    """

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EditarEntry(CiudadanosUpdateView):
    """Native login, ``change_ciudadano`` and 404 first, then the React index (C05.02)."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return _index(request, self.index_bytes)


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
        raise ValueError("Ciudadanos preview assets must not be symlinks")
    assets = {}
    for file in asset_root.rglob("*"):
        if not file.is_file() or file.suffix not in ASSET_SUFFIXES:
            continue
        if file.is_symlink() or not file.resolve().is_relative_to(root):
            raise ValueError("Ciudadanos preview assets must stay inside the build")
        body = file.read_bytes()
        content_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        assets[file.relative_to(root).as_posix()] = (
            body,
            content_type,
            hashlib.sha256(body).hexdigest(),
        )
    return MappingProxyType(assets)


def ciudadanos_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Ciudadanos preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path(
            "ciudadanos/ver/<int:pk>",
            login_required(FichaEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "ciudadanos/eliminar/<int:pk>",
            login_required(BajaEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "ciudadanos/<int:pk>/familiares/nuevo",
            login_required(FamiliarNuevoEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "ciudadanos/crear/",
            login_required(CrearEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "ciudadanos/editar/<int:pk>",
            login_required(EditarEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "ciudadanos/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
