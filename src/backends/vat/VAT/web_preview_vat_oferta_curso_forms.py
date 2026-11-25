"""Explicit local React preview of the VAT offer and course forms (V05.02, U7); never mounted by a production URLconf.

Each entry keeps the native URL and the native guards: the same ``permissions_any_required`` decorator as ``VAT/urls.py``, the
native ``dispatch`` (the ``?centro=`` guard of the course create) and the native view's own scoped queryset (404 outside the
user's scope). Only then the GET returns the frozen React ``index.html``, which loads its data from ``/api/web/vat/``; the
writes are sent by React to the web API.

The course create and edit pages also exist embedded (``?modal=1``): the native centers panel loads them in a modal iframe, so
that variant stays the native page (its GET and its POST), never the React one.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from VAT.views.curso import CursoCreateView, CursoDeleteView, CursoUpdateView
from VAT.views.oferta_institucional import (
    OfertaInstitucionalCreateView,
    OfertaInstitucionalDeleteView,
    OfertaInstitucionalUpdateView,
)
from VAT.web_preview_vat import (
    BUILD_ASSETS,
    PUBLIC_ASSETS,
    ReactAssetView,
    _detail_get,
    _entry,
    _frozen_assets,
    index_response,
)


def _embedded(request):
    return request.GET.get("modal") == "1"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class OfertaCreateEntry(OfertaInstitucionalCreateView):
    """GET the React index; POST goes to the web API."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = None
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class OfertaUpdateEntry(OfertaInstitucionalUpdateView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class OfertaDeleteEntry(OfertaInstitucionalDeleteView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CursoCreateEntry(CursoCreateView):
    """The native ``dispatch`` (``?centro=`` guard) runs first; ``?modal=1`` stays the native embedded page."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        if _embedded(request):
            return super().get(request, *args, **kwargs)
        self.object = None
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CursoUpdateEntry(CursoUpdateView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        if _embedded(request):
            return super().get(request, *args, **kwargs)
        return _detail_get(self, request, *args, **kwargs)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CursoDeleteEntry(CursoDeleteView):
    index_bytes = b""
    get = _detail_get


def oferta_curso_forms_preview_patterns(build_directory):
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
            "vat/ofertas-institucionales/nueva/",
            _entry(OfertaCreateEntry, "VAT.add_ofertainstitucional", index_bytes),
        ),
        path(
            "vat/ofertas-institucionales/<int:pk>/editar/",
            _entry(OfertaUpdateEntry, "VAT.change_ofertainstitucional", index_bytes),
        ),
        path(
            "vat/ofertas-institucionales/<int:pk>/eliminar/",
            _entry(OfertaDeleteEntry, "VAT.delete_ofertainstitucional", index_bytes),
        ),
        path(
            "vat/cursos/nuevo/",
            _entry(CursoCreateEntry, "VAT.add_curso", index_bytes),
        ),
        path(
            "vat/cursos/<int:pk>/editar/",
            _entry(CursoUpdateEntry, "VAT.change_curso", index_bytes),
        ),
        path(
            "vat/cursos/<int:pk>/eliminar/",
            _entry(CursoDeleteEntry, "VAT.delete_curso", index_bytes),
        ),
        path(
            "vat/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
