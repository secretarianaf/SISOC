"""Explicit local React preview of the VAT commission schedule forms (V04.02, U5); never mounted by a production URLconf.

Each entry keeps the native URL and the native guards: the same ``permissions_any_required`` decorator as
``VAT/urls.py`` and the native view's own scoped queryset (404 outside the user's scope). Only then the GET returns the
frozen React ``index.html``, which loads its data from ``/api/web/vat/``. The writes are sent by React to the web API.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from VAT.views.curso import (
    ComisionCursoHorarioCreateView,
    ComisionCursoHorarioDeleteView,
    ComisionCursoHorarioUpdateView,
)
from VAT.views.oferta_institucional import (
    ComisionHorarioCreateView,
    ComisionHorarioDeleteView,
    ComisionHorarioUpdateView,
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
class HorarioOfertaCreateEntry(_CreateEntry, ComisionHorarioCreateView):
    pass


@method_decorator(ensure_csrf_cookie, name="dispatch")
class HorarioOfertaUpdateEntry(ComisionHorarioUpdateView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class HorarioOfertaDeleteEntry(ComisionHorarioDeleteView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class HorarioCursoCreateEntry(_CreateEntry, ComisionCursoHorarioCreateView):
    pass


@method_decorator(ensure_csrf_cookie, name="dispatch")
class HorarioCursoUpdateEntry(ComisionCursoHorarioUpdateView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class HorarioCursoDeleteEntry(ComisionCursoHorarioDeleteView):
    index_bytes = b""
    get = _detail_get


def comision_horario_preview_patterns(build_directory):
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
        "VAT.add_comisionhorario",
        "VAT.change_comisionhorario",
        "VAT.delete_comisionhorario",
    )
    return [
        path(
            "vat/comisiones/horarios/nuevo/",
            _entry(HorarioOfertaCreateEntry, add, index_bytes),
        ),
        path(
            "vat/comisiones/horarios/<int:pk>/editar/",
            _entry(HorarioOfertaUpdateEntry, change, index_bytes),
        ),
        path(
            "vat/comisiones/horarios/<int:pk>/eliminar/",
            _entry(HorarioOfertaDeleteEntry, delete, index_bytes),
        ),
        path(
            "vat/cursos/comisiones/horarios/nuevo/",
            _entry(HorarioCursoCreateEntry, add, index_bytes),
        ),
        path(
            "vat/cursos/comisiones/horarios/<int:pk>/editar/",
            _entry(HorarioCursoUpdateEntry, change, index_bytes),
        ),
        path(
            "vat/cursos/comisiones/horarios/<int:pk>/eliminar/",
            _entry(HorarioCursoDeleteEntry, delete, index_bytes),
        ),
        path(
            "vat/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
