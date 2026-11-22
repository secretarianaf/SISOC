"""Explicit local React preview of the comedor intervention screens (CO02).

Never mounted by a production URLconf. Each entry keeps the native URL, the
native route decorator and the native view's dispatch (login, permission), and
the lookups that are a 404 for the native page. Only then a GET returns the
frozen React ``index.html``, which loads its data from
``/api/web/comedores/intervenciones/``. The subtype AJAX, the document upload and every
POST stay native. Assets are served under
the backend's own prefix ``/comedores/react/``.
"""

from pathlib import Path

from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from comedores.models import Comedor
from comedores.web_preview_catalogos import (
    BUILD_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)
from core.decorators import permissions_any_required
from intervenciones.models.intervenciones import Intervencion
from intervenciones.views import (
    IntervencionCreateView,
    IntervencionDeleteView,
    IntervencionDetailIndividualView,
    IntervencionDetailView,
    IntervencionUpdateView,
)

PUBLIC_ASSETS = "/comedores/react/assets/"
VER = ["intervenciones.view_intervencion"]
ALTA = ["intervenciones.add_intervencion"]
EDICION = ["intervenciones.change_intervencion"]
BAJA = ["comedores.delete_nomina"]


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ListadoEntry(IntervencionDetailView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        # An unknown comedor is a 404 here (a 500 in the native page).
        get_object_or_404(Comedor, pk=self.kwargs["pk"])
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DetalleEntry(IntervencionDetailIndividualView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        get_object_or_404(Intervencion, id=self.kwargs["pk"])
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CrearEntry(IntervencionCreateView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        get_object_or_404(Comedor, pk=self.kwargs["pk"])
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EditarEntry(IntervencionUpdateView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        get_object_or_404(Intervencion, pk=self.kwargs["pk"])
        get_object_or_404(Comedor, pk=self.kwargs["pk2"])
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class BajaEntry(IntervencionDeleteView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.get_object()
        return _index(request, self.index_bytes)


def intervenciones_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Intervenciones preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )

    def entry(vista, permisos=None):
        return permissions_any_required(permisos or VER)(
            vista.as_view(index_bytes=index_bytes)
        )

    return [
        path("comedores/intervencion/ver/<int:pk>", entry(ListadoEntry)),
        path("intervencion/detalle/<int:pk>/", entry(DetalleEntry)),
        path("comedores/intervencion/crear/<int:pk>", entry(CrearEntry, ALTA)),
        path(
            "comedores/intervencion/editar/<int:pk>/<int:pk2>",
            entry(EditarEntry, EDICION),
        ),
        path(
            "comedores/intervencion/borrar/<int:comedor_id>/<int:intervencion_id>/",
            entry(BajaEntry, BAJA),
        ),
        path(
            "comedores/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
