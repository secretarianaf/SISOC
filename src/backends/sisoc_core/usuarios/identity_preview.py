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
from core.decorators import permissions_all_required, permissions_any_required
from users.services import BULK_CREDENTIALS_PERMISSION_CODE
from usuarios.services_bulk_credentials_jobs import get_bulk_credentials_job_or_404
from usuarios.services_user_import_jobs import get_user_import_job_or_404
from usuarios.views import (
    BulkCredentialsJobDetailView,
    BulkCredentialsUploadView,
    GroupCreateView,
    GroupListView,
    GroupUpdateView,
    UserActiveView,
    UserCreateView,
    UserDeleteView,
    UserListView,
    UserUpdateView,
)
from usuarios.views_user_import import UserImportJobCreateView, UserImportJobDetailView

from usuarios.auth_views import (
    ConfirmacionDatosView,
    FirstLoginPasswordChangeView,
    MiCuentaView,
    PasswordResetConfirmCustomView,
    SisocPasswordResetCompleteView,
    SisocPasswordResetDoneView,
    SisocPasswordResetView,
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


@method_decorator(ensure_csrf_cookie, name="dispatch")
class IdentityPasswordResetEntry(_IdentityEntry, SisocPasswordResetView):
    """Public recovery request; POST keeps the source form and mail send."""


class IdentityPasswordResetDoneEntry(_IdentityEntry, SisocPasswordResetDoneView):
    """Single source done page, whether or not an account matched."""


@method_decorator(ensure_csrf_cookie, name="dispatch")
class IdentityPasswordResetConfirmEntry(_IdentityEntry, PasswordResetConfirmCustomView):
    """Keep the source token-to-session redirect before serving the fixed index.

    A valid URL token is exchanged and redirected to ``set-password`` by the
    source dispatch, so the index is only served without a token in the path or
    for an invalid link. POST keeps the source form, including direct posts.
    """

    def render_to_response(self, context, **response_kwargs):
        if self.request.method in ("GET", "HEAD"):
            return self.get(self.request)
        return super().render_to_response(context, **response_kwargs)


class IdentityPasswordResetCompleteEntry(
    _IdentityEntry, SisocPasswordResetCompleteView
):
    """Source completion page without an automatic login."""


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


@method_decorator(ensure_csrf_cookie, name="dispatch")
class UserImportEntry(_IdentityEntry, UserImportJobCreateView):
    """Local upload GET; POST remains the native enqueue."""


@method_decorator(ensure_csrf_cookie, name="dispatch")
class UserImportJobEntry(_IdentityEntry, UserImportJobDetailView):
    """Resolve the native job (404) before serving the local React detail."""

    def get(self, request, *args, **kwargs):
        get_user_import_job_or_404(job_id=kwargs["pk"])
        return super().get(request, *args, **kwargs)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class BulkCredentialsEntry(_IdentityEntry, BulkCredentialsUploadView):
    """Local upload GET; POST remains the native enqueue."""


@method_decorator(ensure_csrf_cookie, name="dispatch")
class BulkCredentialsJobEntry(_IdentityEntry, BulkCredentialsJobDetailView):
    """Resolve the native job (404) before serving the local React detail."""

    def get(self, request, *args, **kwargs):
        get_bulk_credentials_job_or_404(job_id=kwargs["pk"])
        return super().get(request, *args, **kwargs)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class UserListEntry(_IdentityEntry, UserListView):
    """Local GET body with the unchanged native list permission and methods."""


@method_decorator(ensure_csrf_cookie, name="dispatch")
class UserDeactivateEntry(_IdentityEntry, UserDeleteView):
    """Resolve the in-scope user (404) before serving the local confirm step."""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class UserActivateEntry(_IdentityEntry, UserActiveView):
    """Resolve the in-scope user (404) before serving the local confirm step."""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class UserCreateEntry(_IdentityEntry, UserCreateView):
    """Local form GET; the Comedores forward of the native entry is not served."""


@method_decorator(ensure_csrf_cookie, name="dispatch")
class UserUpdateEntry(_IdentityEntry, UserUpdateView):
    """Resolve the in-scope user (404) before serving the local React form."""

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
        .replace("/v2/sisoc/assets/", "/sisoc-identity/react/assets/")
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
        path(
            "usuarios/",
            permissions_any_required(["auth.view_user"])(
                UserListEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "usuarios/crear/",
            permissions_any_required(["auth.add_user"])(
                UserCreateEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "usuarios/editar/<int:pk>/",
            permissions_any_required(["auth.change_user"])(
                UserUpdateEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "usuarios/borrar/<int:pk>/",
            permissions_any_required(["auth.delete_user"])(
                UserDeactivateEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "usuarios/activar/<int:pk>/",
            permissions_any_required(["auth.delete_user"])(
                UserActivateEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "usuarios/importar/",
            permissions_any_required(["auth.add_user"])(
                UserImportEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "usuarios/importar/lotes/<int:pk>/",
            permissions_any_required(["auth.add_user"])(
                UserImportJobEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "usuarios/credenciales-masivas/",
            permissions_all_required(
                ["auth.change_user", BULK_CREDENTIALS_PERMISSION_CODE]
            )(BulkCredentialsEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "usuarios/credenciales-masivas/lotes/<int:pk>/",
            permissions_all_required(
                ["auth.change_user", BULK_CREDENTIALS_PERMISSION_CODE]
            )(BulkCredentialsJobEntry.as_view(index_bytes=index_bytes)),
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
            "password_reset/",
            IdentityPasswordResetEntry.as_view(index_bytes=index_bytes),
        ),
        path(
            "password_reset/done/",
            IdentityPasswordResetDoneEntry.as_view(index_bytes=index_bytes),
        ),
        path(
            "reset/<uidb64>/<token>/",
            IdentityPasswordResetConfirmEntry.as_view(index_bytes=index_bytes),
        ),
        path(
            "password/reset/confirm/<uidb64>/<token>/",
            IdentityPasswordResetConfirmEntry.as_view(index_bytes=index_bytes),
        ),
        path(
            "reset/done/",
            IdentityPasswordResetCompleteEntry.as_view(index_bytes=index_bytes),
        ),
        path(
            "sisoc-identity/react/<path:asset_path>",
            IdentityAssetView.as_view(assets=frozen_assets),
        ),
    ]
