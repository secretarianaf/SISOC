"""Explicit local React preview of the payment files (EX01); never mounted by a production URLconf.

Each entry keeps the native URL, its route decorator and the native view's
dispatch: anonymous users get the native login redirect (list and detail) or
403 (operations), users without the four read codes the native 403, a missing
expediente or an invalid ``page`` the native 404. Only then a GET returns the
frozen React ``index.html``, which loads its data from
``/api/web/comedores/expedientespagos/``. Other methods reach the native view
unchanged. Assets are served under the backend's own prefix
``/expedientespagos/react/``.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic.detail import SingleObjectMixin

from core.decorators import permissions_any_required
from comedores.web_preview_catalogos import (
    BUILD_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)
from expedientespagos.views import (
    ExpedientesPagosCreateView,
    ExpedientesPagosDeleteView,
    ExpedientesPagosDetailView,
    ExpedientesPagosListView,
    ExpedientesPagosUpdateView,
)
from expedientespagos.web_api import OPERATION_PERMISSIONS

PUBLIC_ASSETS = "/expedientespagos/react/assets/"


class _ObjectEntry(SingleObjectMixin):
    """Native object lookup (404) before the index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = (
            self.get_object()
        )  # pylint: disable=attribute-defined-outside-init
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ListEntry(ExpedientesPagosListView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        # Same Http404 as the native list for a page of the global paginator.
        self.paginate_queryset(self.object_list, self.get_paginate_by(self.object_list))
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DetailEntry(_ObjectEntry, ExpedientesPagosDetailView):
    pass


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CreateEntry(ExpedientesPagosCreateView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class UpdateEntry(_ObjectEntry, ExpedientesPagosUpdateView):
    pass


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DeleteEntry(_ObjectEntry, ExpedientesPagosDeleteView):
    pass


def expedientes_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Expedientes preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )

    def entry(vista):
        return vista.as_view(index_bytes=index_bytes)

    def operation(vista):
        return permissions_any_required(OPERATION_PERMISSIONS)(entry(vista))

    base = "expedientespagos/expedientespagos/"
    return [
        path(f"{base}<int:pk>/", entry(ListEntry)),
        path(f"{base}<int:pk>/detalle/", entry(DetailEntry)),
        path(f"{base}<int:pk>/nuevo/", operation(CreateEntry)),
        path(f"{base}<int:pk>/editar/", operation(UpdateEntry)),
        path(f"{base}<int:pk>/eliminar/", operation(DeleteEntry)),
        path(
            "expedientespagos/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
