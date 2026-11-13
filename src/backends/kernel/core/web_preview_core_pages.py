"""Explicit local React preview of the core pages (T02, T03, T05, T06); never mounted by a production URLconf.

Every entry keeps the native URL and guards (login redirect, the native permission, the native
404) and only then returns the frozen React ``index.html``:

- ``novedades/`` and ``arquitectura/`` (any authenticated user);
- ``programas/``, ``programas/<pk>/``, ``programas/crear/``, ``programas/<pk>/editar/`` and
  ``programas/<pk>/eliminar/`` (``Programa*View``: login only, the 404 of a missing object);
- ``papelera/`` and ``papelera/preview-restore/<app>/<model>/<pk>/`` (superuser only; 404 when the
  record is not in the trash).

Assets are served under ``/core/react/``.
"""

# pylint: disable=protected-access

from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.urls import path
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie

from ciudadanos.web_preview import ReactAssetView, _frozen_assets, _index
from core.trash_views import (
    TrashListView,
    TrashRestorePreviewView,
    _resolve_model_or_404,
)
from core.views import (
    ProgramaCreateView,
    ProgramaDeleteView,
    ProgramaDetailView,
    ProgramaListView,
    ProgramaUpdateView,
)

BUILD_ASSETS = "/v2/sisoc/assets/"
PUBLIC_ASSETS = "/core/react/assets/"


class _IndexMixin:
    index_bytes = b""

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ListEntry(_IndexMixin, ProgramaListView):
    """Native login first, then the frozen React index."""


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CreateEntry(_IndexMixin, ProgramaCreateView):
    """Native login first, then the frozen React index."""


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DetailEntry(ProgramaDetailView):
    """Native login and 404 first, then the frozen React index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class UpdateEntry(ProgramaUpdateView):
    """Native login and 404 first, then the frozen React index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DeleteEntry(ProgramaDeleteView):
    """Native login and 404 first, then the frozen React index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PlainEntry(View):
    """A page whose native view is a function: login first, then the frozen React index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class TrashEntry(_IndexMixin, TrashListView):
    """Native login and superuser guard first (403), then the frozen React index."""


@method_decorator(ensure_csrf_cookie, name="dispatch")
class TrashRestoreEntry(TrashRestorePreviewView):
    """Native guards and the 404 of a record outside the trash, then the frozen React index."""

    index_bytes = b""

    def get(self, request, app_label, model_name, pk):
        model = _resolve_model_or_404(app_label, model_name)
        if not model.all_objects.filter(pk=pk, deleted_at__isnull=False).exists():
            raise Http404("El registro no está en papelera.")
        return _index(request, self.index_bytes)


def core_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf."""
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Core preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path("novedades/", login_required(PlainEntry.as_view(index_bytes=index_bytes))),
        path(
            "arquitectura/", login_required(PlainEntry.as_view(index_bytes=index_bytes))
        ),
        path("programas/", ListEntry.as_view(index_bytes=index_bytes)),
        path("programas/crear/", CreateEntry.as_view(index_bytes=index_bytes)),
        path("programas/<int:pk>/", DetailEntry.as_view(index_bytes=index_bytes)),
        path(
            "programas/<int:pk>/editar/", UpdateEntry.as_view(index_bytes=index_bytes)
        ),
        path(
            "programas/<int:pk>/eliminar/",
            DeleteEntry.as_view(index_bytes=index_bytes),
        ),
        path("papelera/", TrashEntry.as_view(index_bytes=index_bytes)),
        path(
            "papelera/preview-restore/<str:app_label>/<str:model_name>/<int:pk>/",
            TrashRestoreEntry.as_view(index_bytes=index_bytes),
        ),
        path(
            "core/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
