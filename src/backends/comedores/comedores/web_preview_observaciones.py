"""Explicit local React preview of the comedor observation screens (CO06).

Never mounted by a production URLconf. Each entry keeps the native URL, the
native route decorator and the native view's dispatch (login, permission) and
its scoped lookups: a comedor or observation outside the user's scope is the
native 404 (and a missing id on the detail page, a 500 natively, is a 404).
Only then a GET returns the frozen React ``index.html``, which loads its data
from ``/api/web/comedores/observaciones/``. Every POST stays native. Assets are
served under the backend's own prefix ``/observaciones/react/``.
"""

from pathlib import Path

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from comedores.services.comedor_service import ComedorService
from comedores.views.observacion import (
    ObservacionCreateView,
    ObservacionDeleteView,
    ObservacionDetailView,
    ObservacionUpdateView,
)
from comedores.web_preview_catalogos import (
    BUILD_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)
from core.decorators import permissions_any_required

PUBLIC_ASSETS = "/observaciones/react/assets/"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CrearEntry(ObservacionCreateView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        ComedorService.get_scoped_comedor_or_404(
            self.kwargs["comedor_pk"], request.user
        )
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DetalleEntry(ObservacionDetailView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        try:
            self.get_object()
        except ObjectDoesNotExist as exc:
            raise Http404() from exc
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EditarEntry(ObservacionUpdateView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.get_object()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class BajaEntry(ObservacionDeleteView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.get_object()
        return _index(request, self.index_bytes)


def observaciones_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Observaciones preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )

    def entry(vista, permiso):
        return permissions_any_required([permiso])(
            vista.as_view(index_bytes=index_bytes)
        )

    return [
        path(
            "comedores/<comedor_pk>/observacion/crear",
            entry(CrearEntry, "comedores.add_observacion"),
        ),
        path(
            "comedores/observacion/<int:pk>",
            entry(DetalleEntry, "comedores.view_observacion"),
        ),
        path(
            "comedores/observacion/<int:pk>/editar",
            entry(EditarEntry, "comedores.change_observacion"),
        ),
        path(
            "comedores/observacion/<int:pk>/eliminar",
            entry(BajaEntry, "comedores.delete_observacion"),
        ),
        path(
            "observaciones/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
