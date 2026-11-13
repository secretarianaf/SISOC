"""Explicit local React preview of the comedor list, form and baja (CO07.01/02).

Never mounted by a production URLconf. The entry keeps the native URL, the
native route decorator and the native view's dispatch (login, scope, page
validation): users the decorator rejects get the native 403 and an invalid
page the native 404. Only then a GET returns the frozen React ``index.html``,
which loads its data from ``/api/web/comedores/comedores/``. The CSV export,
the CSV export and the AJAX endpoints are not listed here and
stay native. Assets are served under ``/comedores/react/`` by the shared
catalog preview.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from core.decorators import permissions_any_required
from comedores.views.comedor import (
    ComedorCreateView,
    ComedorDeleteView,
    ComedorListView,
    ComedorUpdateView,
)
from comedores.web_api_comedor_form import CREATE_PERMISSIONS, EDIT_PERMISSIONS
from comedores.web_api_comedores import DELETE_PERMISSIONS, LIST_PERMISSIONS
from comedores.web_preview_catalogos import (
    BUILD_ASSETS,
    PUBLIC_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ListEntry(ComedorListView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        # Same page validation as the native list.
        self.paginate_queryset(self.object_list, self.get_paginate_by(self.object_list))
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CreateEntry(ComedorCreateView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class UpdateEntry(ComedorUpdateView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        # Scoped lookup: a comedor outside the user's scope is the native 404.
        self.object = self.get_object()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DeleteEntry(ComedorDeleteView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        # Scoped lookup: a comedor outside the user's scope is the native 404.
        self.object = self.get_object()
        return _index(request, self.index_bytes)


def comedores_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf."""
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Comedores preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path(
            "comedores/listar",
            permissions_any_required(LIST_PERMISSIONS)(
                ListEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "comedores/crear",
            permissions_any_required(CREATE_PERMISSIONS)(
                CreateEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "comedores/<int:pk>/editar",
            permissions_any_required(EDIT_PERMISSIONS)(
                UpdateEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "comedores/<int:pk>/eliminar",
            permissions_any_required(DELETE_PERMISSIONS)(
                DeleteEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "comedores/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
