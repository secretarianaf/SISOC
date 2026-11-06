"""Explicit local identity preview; never mounted by the production URLconf."""

import hashlib
import mimetypes
from pathlib import Path
from types import MappingProxyType

from django.contrib.auth.views import PasswordChangeDoneView, PasswordChangeView
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.urls import path
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie

from core.views import inicio_view
from core.decorators import permissions_any_required
from usuarios.views import GroupCreateView, GroupListView, GroupUpdateView

from usuarios.auth_views import (
    ConfirmacionDatosView,
    FirstLoginPasswordChangeView,
    MiCuentaView,
    UsuariosLoginView,
)


class _IdentityEntry(View):
    """Reuse source dispatch and POST behavior, changing only the local GET body."""

    index_bytes = b""

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response

    def get(self, request, *args, **kwargs):
        response = HttpResponse(
            b"" if request.method == "HEAD" else self.index_bytes,
            content_type="text/html; charset=utf-8",
        )
        response["Content-Length"] = str(len(self.index_bytes))
        return response


@method_decorator(ensure_csrf_cookie, name="dispatch")
class IdentityLoginEntry(_IdentityEntry, UsuariosLoginView):
    """Anonymous preview entry retaining the real LoginView redirect policy."""


@method_decorator(ensure_csrf_cookie, name="dispatch")
class IdentityPasswordEntry(_IdentityEntry, FirstLoginPasswordChangeView):
    """Required-password preview retaining the original prerequisite dispatch."""


@method_decorator(ensure_csrf_cookie, name="dispatch")
class IdentityAccountEntry(_IdentityEntry, MiCuentaView):
    """Own-account preview retaining the original form-view behavior."""


@method_decorator(ensure_csrf_cookie, name="dispatch")
class IdentityAccountConfirmationEntry(_IdentityEntry, ConfirmacionDatosView):
    """Profile confirmation preserving the source early redirect."""


@method_decorator(ensure_csrf_cookie, name="dispatch")
class IdentityVoluntaryPasswordEntry(_IdentityEntry, PasswordChangeView):
    """Voluntary-password preview without required-password effects."""


class IdentityVoluntaryPasswordDoneEntry(_IdentityEntry, PasswordChangeDoneView):
    """Source completion entry without an additional mutation."""


@method_decorator(login_required, name="dispatch")
@method_decorator(ensure_csrf_cookie, name="dispatch")
class IdentityHomeEntry(_IdentityEntry):
    """Local React Home GET; other methods retain the source function view."""

    def dispatch(self, request, *args, **kwargs):
        if request.method not in {"GET", "HEAD"}:
            return inicio_view(request)
        return super().dispatch(request, *args, **kwargs)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class GroupListEntry(_IdentityEntry, GroupListView):
    """Local GET body with unchanged native list permission and methods."""


@method_decorator(ensure_csrf_cookie, name="dispatch")
class GroupCreateEntry(_IdentityEntry, GroupCreateView):
    """Local form GET; POST remains the original GroupForm save."""


@method_decorator(ensure_csrf_cookie, name="dispatch")
class GroupUpdateEntry(_IdentityEntry, GroupUpdateView):
    """Resolve the original object before serving the local React edit entry."""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)


class IdentityAssetView(View):
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


def identity_preview_patterns(build_directory):
    """Freeze an explicit local build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    No production URLconf imports this factory or enables these HTML entries.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Identity preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace("/v2/sisoc/assets/", "/static/sisoc-identity/assets/")
        .encode("utf-8")
    )
    assets = {}
    allowed_suffixes = {
        ".js",
        ".css",
        ".woff",
        ".woff2",
        ".svg",
        ".png",
        ".jpg",
        ".ico",
    }
    asset_root = root / "assets"
    if asset_root.is_symlink():
        raise ValueError("Identity preview assets must not be symlinks")
    for file in asset_root.rglob("*"):
        if not file.is_file() or file.suffix not in allowed_suffixes:
            continue
        if file.is_symlink() or not file.resolve().is_relative_to(root):
            raise ValueError("Identity preview assets must stay inside the build")
        body = file.read_bytes()
        content_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        assets[file.relative_to(root).as_posix()] = (
            body,
            content_type,
            hashlib.sha256(body).hexdigest(),
        )
    frozen_assets = MappingProxyType(assets)
    return [
        path(
            "grupos/",
            permissions_any_required(["auth.view_group"])(
                GroupListEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "grupos/crear/",
            permissions_any_required(["auth.add_group"])(
                GroupCreateEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "grupos/editar/<int:pk>/",
            permissions_any_required(["auth.change_group"])(
                GroupUpdateEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path("", IdentityLoginEntry.as_view(index_bytes=index_bytes)),
        path("login/", IdentityLoginEntry.as_view(index_bytes=index_bytes)),
        path("inicio/", IdentityHomeEntry.as_view(index_bytes=index_bytes)),
        path(
            "password/first-change/",
            IdentityPasswordEntry.as_view(index_bytes=index_bytes),
        ),
        path("mi-cuenta/", IdentityAccountEntry.as_view(index_bytes=index_bytes)),
        path(
            "mi-cuenta/confirmar/",
            IdentityAccountConfirmationEntry.as_view(index_bytes=index_bytes),
        ),
        path(
            "password_change/",
            IdentityVoluntaryPasswordEntry.as_view(index_bytes=index_bytes),
        ),
        path(
            "password_change/done/",
            IdentityVoluntaryPasswordDoneEntry.as_view(index_bytes=index_bytes),
        ),
        path(
            "static/sisoc-identity/<path:asset_path>",
            IdentityAssetView.as_view(assets=frozen_assets),
        ),
    ]
