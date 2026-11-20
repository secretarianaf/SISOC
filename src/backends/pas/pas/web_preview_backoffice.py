"""Explicit local React preview of the PAS back office; never mounted by a production URLconf.

Each entry keeps the native URL, its route decorator and the native view's
dispatch: users the decorator rejects (anonymous included) get the native 403
and an unknown titular the native 404. Only then a GET returns the frozen
``apps/sisoc`` ``index.html``, which loads its data from ``/api/web/pas/``.
Other methods reach the native view unchanged. Assets stay under the backend's
own prefix (``/pas/react/``), so the core forwards them like any other route.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from core.decorators import permissions_any_required
from pas.ddjj_preview import PasDDJJAssetView, _frozen_assets, _index_response
from pas.views import (
    PasAreaView,
    PasPersonaCreateView,
    PasPersonaDetailView,
    PasPersonaListView,
    PasPersonaUpdateView,
)

BUILD_ASSETS = "/v2/sisoc/assets/"
PUBLIC_ASSETS = "/pas/react/assets/"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PasPersonaListEntry(PasPersonaListView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PasPanelEntry(PasPersonaDetailView):
    """Native lookup first: an unknown ``pk`` is the native 404."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return _index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PasAreaEntry(PasAreaView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PasPersonaCreateEntry(PasPersonaCreateView):
    """Only the GET is replaced; a POST reaches the native view unchanged."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PasPersonaUpdateEntry(PasPersonaUpdateView):
    """Native lookup first: an unknown ``pk`` is the native 404."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return _index_response(request, self.index_bytes)


def _patterns(index_bytes):
    def entry(vista, **kwargs):
        return permissions_any_required(["pas.view_paspersona"])(
            vista.as_view(index_bytes=index_bytes, **kwargs)
        )

    return [
        path("pas/listar", entry(PasPersonaListEntry)),
        path("pas/panel-control", entry(PasPanelEntry)),
        path("pas/panel-control/<int:pk>", entry(PasPanelEntry)),
        path("pas/<int:pk>", entry(PasPanelEntry)),
        path("pas/formacion", entry(PasAreaEntry, area_key="formacion")),
        path("pas/mesa-ayuda", entry(PasAreaEntry, area_key="mesa-ayuda")),
        path("pas/liquidacion", entry(PasAreaEntry, area_key="liquidacion")),
        path(
            "pas/crear",
            permissions_any_required(["pas.add_paspersona"])(
                PasPersonaCreateEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "pas/<int:pk>/editar",
            permissions_any_required(["pas.change_paspersona"])(
                PasPersonaUpdateEntry.as_view(index_bytes=index_bytes)
            ),
        ),
    ]


def backoffice_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("PAS preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        *_patterns(index_bytes),
        path(
            "pas/react/<path:asset_path>",
            PasDDJJAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
