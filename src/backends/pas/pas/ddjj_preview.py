"""Explicit local React preview of the public DDJJ; never mounted by a production URLconf.

The entry keeps the canonical invitation URL and the native view: unknown (404)
and unavailable (410) invitations and every POST still get the native response.
Only an available invitation's GET returns the frozen React ``index.html``.
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

from pas.views import PasDDJJFormularioView

BUILD_ASSETS = "/v2/pas/assets/"
PUBLIC_ASSETS = "/pas/ddjj/react/assets/"
ASSET_SUFFIXES = {".js", ".css", ".woff", ".woff2", ".svg", ".png", ".jpg", ".ico"}


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
class PasDDJJFormularioEntry(PasDDJJFormularioView):
    """React GET for an available invitation; native 404/410 and POST otherwise."""

    index_bytes = b""

    def get(self, request, token):
        invitacion = self._invitacion(token)
        if not invitacion.disponible:
            return super().get(request, token)
        return _index_response(request, self.index_bytes)


class PasDDJJConfirmacionEntry(View):
    """Generic confirmation rendered by React; no identifier or query is read."""

    http_method_names = ["get", "head"]
    index_bytes = b""

    def get(self, request):
        return _index_response(request, self.index_bytes)


class PasDDJJAssetView(View):
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
        raise ValueError("DDJJ preview assets must not be symlinks")
    assets = {}
    for file in asset_root.rglob("*"):
        if not file.is_file() or file.suffix not in ASSET_SUFFIXES:
            continue
        if file.is_symlink() or not file.resolve().is_relative_to(root):
            raise ValueError("DDJJ preview assets must stay inside the build")
        body = file.read_bytes()
        content_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        assets[file.relative_to(root).as_posix()] = (
            body,
            content_type,
            hashlib.sha256(body).hexdigest(),
        )
    return MappingProxyType(assets)


def ddjj_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/pas`` build for a disposable preview URLconf."""
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("DDJJ preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path(
            "pas/ddjj/formulario/<uuid:token>",
            PasDDJJFormularioEntry.as_view(index_bytes=index_bytes),
        ),
        path(
            "pas/ddjj/confirmacion",
            PasDDJJConfirmacionEntry.as_view(index_bytes=index_bytes),
        ),
        path(
            "pas/ddjj/react/<path:asset_path>",
            PasDDJJAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
