"""Explicit local React preview of the VAT session attendance pages (V02.01); never mounted by a production URLconf.

Each entry keeps the native URL and the native guards: the same
``permissions_any_required`` decorator as ``VAT/urls.py`` and the native view's own
scoped session lookup (404 outside the user's scope). Only then the GET returns the
frozen React ``index.html``, which loads its data from ``/api/web/vat/``. The POST is
sent by React to the web API, which runs the native ``post``.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from VAT.views.curso import AsistenciaSesionCursoView
from VAT.views.oferta_institucional import AsistenciaSesionView
from VAT.web_preview_vat import (
    PUBLIC_ASSETS,
    BUILD_ASSETS,
    ReactAssetView,
    _entry_any,
    _frozen_assets,
    index_response,
)

PERMISSIONS = ["VAT.add_asistenciasesion", "VAT.change_asistenciasesion"]


@method_decorator(ensure_csrf_cookie, name="dispatch")
class AsistenciaCursoEntry(AsistenciaSesionCursoView):
    """GET the React index after the native scoped lookup; POST goes to the web API."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.get_sesion(self.kwargs["sesion_pk"])
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class AsistenciaOfertaEntry(AsistenciaSesionView):
    """GET the React index after the native scoped lookup; POST goes to the web API."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.get_sesion(self.kwargs["sesion_pk"])
        return index_response(request, self.index_bytes)


def asistencia_preview_patterns(build_directory):
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
            "vat/cursos/comisiones/sesiones/<int:sesion_pk>/asistencia/",
            _entry_any(AsistenciaCursoEntry, PERMISSIONS, index_bytes),
        ),
        path(
            "vat/comisiones/sesiones/<int:sesion_pk>/asistencia/",
            _entry_any(AsistenciaOfertaEntry, PERMISSIONS, index_bytes),
        ),
        path(
            "vat/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
