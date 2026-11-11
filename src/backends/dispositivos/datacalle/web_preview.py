"""Explicit local React preview of the DataCalle operativos; never mounted by a production URLconf.

Each entry keeps the native URL and the native guards: the same
``permissions_any_required`` decorator as ``datacalle/urls.py`` and the native
view's own rules (provincial scope 404, invalid page 404). Only the GET is
replaced by the frozen React ``index.html``, which loads its data from
``/api/web/dispositivos/datacalle/``; any other method stays the native one.
Assets stay under the backend's own prefix (``/datacalle/react/``), so the
core forwards them like any other route.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from core.decorators import permissions_any_required
from datacalle.views import (
    RelevamientoCreateView,
    RelevamientoDeleteView,
    RelevamientoDetailView,
    RelevamientoListView,
    RelevamientoUpdateView,
)
from dispositivos.web_preview import (
    BUILD_ASSETS,
    ReactAssetView,
    _frozen_assets,
    index_response,
)

PUBLIC_ASSETS = "/datacalle/react/assets/"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class RelevamientoListEntry(RelevamientoListView):
    """Native scope and pagination (invalid page 404), then the frozen index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.paginate_queryset(self.get_queryset(), self.paginate_by)
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class RelevamientoCreateEntry(RelevamientoCreateView):
    """Native create guard; the POST stays native."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return index_response(request, self.index_bytes)


class _ObjectEntryMixin:
    """The native object rule (404 out of scope or missing), then the index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class RelevamientoDetailEntry(_ObjectEntryMixin, RelevamientoDetailView):
    pass


@method_decorator(ensure_csrf_cookie, name="dispatch")
class RelevamientoUpdateEntry(_ObjectEntryMixin, RelevamientoUpdateView):
    pass


@method_decorator(ensure_csrf_cookie, name="dispatch")
class RelevamientoDeleteEntry(_ObjectEntryMixin, RelevamientoDeleteView):
    pass


def datacalle_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("DataCalle preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )

    def entry(codename, view_class):
        guard = permissions_any_required([f"datacalle.{codename}"])
        return guard(view_class.as_view(index_bytes=index_bytes))

    base = "datacalle/relevamientos/"
    return [
        path(base, entry("view_relevamiento", RelevamientoListEntry)),
        path(f"{base}crear/", entry("add_relevamiento", RelevamientoCreateEntry)),
        path(f"{base}<uuid:pk>/", entry("view_relevamiento", RelevamientoDetailEntry)),
        path(
            f"{base}<uuid:pk>/editar/",
            entry("change_relevamiento", RelevamientoUpdateEntry),
        ),
        path(
            f"{base}<uuid:pk>/eliminar/",
            entry("delete_relevamiento", RelevamientoDeleteEntry),
        ),
        path(
            "datacalle/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
