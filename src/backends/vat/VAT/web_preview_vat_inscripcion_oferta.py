"""Explicit local React preview of the VAT offer enrolment screens (V03.01); never mounted by a production URLconf.

Each entry keeps the native URL and the native guard (the same ``permissions_any_required`` decorator as
``VAT/urls.py``) and the native view's own dispatch (login redirect, queryset 404, invalid ``page`` 404). Only then the
GET returns the frozen React ``index.html``, which loads its data from ``/api/web/vat/``. POSTs go to the web API.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from VAT.views.oferta import (
    InscripcionOfertaCreateView,
    InscripcionOfertaDeleteView,
    InscripcionOfertaDetailView,
    InscripcionOfertaListView,
    InscripcionOfertaUpdateView,
)
from VAT.web_preview_vat import (
    BUILD_ASSETS,
    PUBLIC_ASSETS,
    ReactAssetView,
    _detail_get,
    _entry,
    _frozen_assets,
    _list_get,
    index_response,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class InscripcionOfertaListEntry(InscripcionOfertaListView):
    index_bytes = b""
    get = _list_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class InscripcionOfertaDetailEntry(InscripcionOfertaDetailView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class InscripcionOfertaCreateEntry(InscripcionOfertaCreateView):
    """GET the React index; POST goes to the web API."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = None
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class InscripcionOfertaUpdateEntry(InscripcionOfertaUpdateView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class InscripcionOfertaDeleteEntry(InscripcionOfertaDeleteView):
    index_bytes = b""
    get = _detail_get


def inscripcion_oferta_preview_patterns(build_directory):
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
            "vat/inscripciones-oferta/",
            _entry(
                InscripcionOfertaListEntry, "VAT.view_inscripcionoferta", index_bytes
            ),
        ),
        path(
            "vat/inscripciones-oferta/nueva/",
            _entry(
                InscripcionOfertaCreateEntry, "VAT.add_inscripcionoferta", index_bytes
            ),
        ),
        path(
            "vat/inscripciones-oferta/<int:pk>/",
            _entry(
                InscripcionOfertaDetailEntry, "VAT.view_inscripcionoferta", index_bytes
            ),
        ),
        path(
            "vat/inscripciones-oferta/<int:pk>/editar/",
            _entry(
                InscripcionOfertaUpdateEntry,
                "VAT.change_inscripcionoferta",
                index_bytes,
            ),
        ),
        path(
            "vat/inscripciones-oferta/<int:pk>/eliminar/",
            _entry(
                InscripcionOfertaDeleteEntry,
                "VAT.delete_inscripcionoferta",
                index_bytes,
            ),
        ),
        path(
            "vat/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
