"""Explicit local React preview of the VAT inscripciones pages (V03.02, U3); never mounted by a production URLconf.

Each entry keeps the native URL and the native guards: the same
``permissions_any_required`` decorator as ``VAT/urls.py`` and the native view's own
dispatch (login redirect, queryset 404, invalid ``page`` 404). Only then the GET returns
the frozen React ``index.html``, which loads its data from ``/api/web/vat/``. The writes
are sent by React to the web API; the buscador keeps the native POST for its CSV/XLSX
downloads.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from VAT.views.buscador_ciudadano import BuscadorCiudadanoView
from VAT.views.persona import (
    InscripcionCreateView,
    InscripcionDeleteView,
    InscripcionDetailView,
    InscripcionListView,
    InscripcionUpdateView,
)
from VAT.web_preview_vat import (
    BUILD_ASSETS,
    PUBLIC_ASSETS,
    ReactAssetView,
    _detail_get,
    _entry,
    _entry_any,
    _frozen_assets,
    _list_get,
    index_response,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class InscripcionListEntry(InscripcionListView):
    index_bytes = b""
    get = _list_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class InscripcionDetailEntry(InscripcionDetailView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class InscripcionCreateEntry(InscripcionCreateView):
    """GET the React index; POST goes to the web API."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = None
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class InscripcionUpdateEntry(InscripcionUpdateView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class InscripcionDeleteEntry(InscripcionDeleteView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class BuscadorCiudadanoEntry(BuscadorCiudadanoView):
    """GET the React index; the POST stays the native one (CSV/XLSX downloads)."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return index_response(request, self.index_bytes)


def inscripcion_persona_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf."""
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("VAT preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path(
            "vat/inscripciones/",
            _entry(InscripcionListEntry, "VAT.view_inscripcion", index_bytes),
        ),
        path(
            "vat/inscripciones/nueva/",
            _entry(InscripcionCreateEntry, "VAT.add_inscripcion", index_bytes),
        ),
        path(
            "vat/inscripciones/<int:pk>/",
            _entry(InscripcionDetailEntry, "VAT.view_inscripcion", index_bytes),
        ),
        path(
            "vat/inscripciones/<int:pk>/editar/",
            _entry(InscripcionUpdateEntry, "VAT.change_inscripcion", index_bytes),
        ),
        path(
            "vat/inscripciones/<int:pk>/eliminar/",
            _entry(InscripcionDeleteEntry, "VAT.delete_inscripcion", index_bytes),
        ),
        path(
            "vat/buscador-ciudadano/",
            _entry_any(
                BuscadorCiudadanoEntry,
                ["VAT.view_inscripcion", "VAT.view_centro"],
                index_bytes,
            ),
        ),
        path(
            "vat/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
