"""Explicit local React preview of the VAT course commission wizard (V04.02, U5); never mounted by a production URLconf.

The entry keeps the native URL, the native ``permissions_any_required`` guard and the native ``dispatch`` of the wizard
(the course lookup and the scope of its center). Only then the GET returns the frozen React ``index.html``, which loads each
step from ``/api/web/vat/comisiones-asistente/``; the steps are posted by React to the web API.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from VAT.views.comision_curso_wizard import ComisionCursoWizardView
from VAT.web_preview_vat import (
    BUILD_ASSETS,
    PUBLIC_ASSETS,
    ReactAssetView,
    _entry,
    _frozen_assets,
    index_response,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ComisionCursoWizardEntry(ComisionCursoWizardView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return index_response(request, self.index_bytes)


def comision_wizard_preview_patterns(build_directory):
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
            "vat/cursos/<int:curso_id>/comision/nueva/",
            _entry(ComisionCursoWizardEntry, "VAT.add_comisioncurso", index_bytes),
        ),
        path(
            "vat/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
