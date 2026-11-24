"""Explicit local React preview of the VAT commission forms (V04.02, U5); never mounted by a production URLconf.

Each entry keeps the native URL and the native guards: the same ``permissions_any_required`` decorator as
``VAT/urls.py``, the native ``dispatch`` (the ``?curso=`` guard of the course create) and the native view's own scoped
queryset (404 outside the user's scope). Only then the GET returns the frozen React ``index.html``, which loads its data
from ``/api/web/vat/``. The writes are sent by React to the web API.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from VAT.views.curso import (
    ComisionCursoCreateView,
    ComisionCursoDeleteView,
    ComisionCursoUpdateView,
)
from VAT.views.oferta_institucional import (
    ComisionCreateView,
    ComisionDeleteView,
    ComisionUpdateView,
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


class _CreateEntry:
    """GET the React index; POST goes to the web API."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = None
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ComisionOfertaCreateEntry(_CreateEntry, ComisionCreateView):
    pass


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ComisionOfertaUpdateEntry(ComisionUpdateView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ComisionOfertaDeleteEntry(ComisionDeleteView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ComisionCursoCreateEntry(_CreateEntry, ComisionCursoCreateView):
    pass


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ComisionCursoUpdateEntry(ComisionCursoUpdateView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ComisionCursoDeleteEntry(ComisionCursoDeleteView):
    index_bytes = b""
    get = _detail_get


def comision_forms_preview_patterns(build_directory):
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
    add, change, delete = (
        "VAT.add_comision",
        "VAT.change_comision",
        "VAT.delete_comision",
    )
    add_c, change_c, delete_c = (
        "VAT.add_comisioncurso",
        "VAT.change_comisioncurso",
        "VAT.delete_comisioncurso",
    )
    return [
        path(
            "vat/comisiones/nueva/",
            _entry(ComisionOfertaCreateEntry, add, index_bytes),
        ),
        path(
            "vat/comisiones/<int:pk>/editar/",
            _entry(ComisionOfertaUpdateEntry, change, index_bytes),
        ),
        path(
            "vat/comisiones/<int:pk>/eliminar/",
            _entry(ComisionOfertaDeleteEntry, delete, index_bytes),
        ),
        path(
            "vat/cursos/comisiones/nueva/",
            _entry(ComisionCursoCreateEntry, add_c, index_bytes),
        ),
        path(
            "vat/cursos/comisiones/<int:pk>/editar/",
            _entry(ComisionCursoUpdateEntry, change_c, index_bytes),
        ),
        path(
            "vat/cursos/comisiones/<int:pk>/eliminar/",
            _entry(ComisionCursoDeleteEntry, delete_c, index_bytes),
        ),
        path(
            "vat/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
