"""Explicit local React preview of the ciudadanos bulk import (C01); never mounted by a production URLconf.

Every entry keeps the native URL and guards (login redirect, ``ciudadanos.add_ciudadano``, the
native 404 of a missing batch) and only then returns the frozen React ``index.html``:

- ``ciudadanos/importacion-masiva/``: the upload form and the recent batches.
- ``ciudadanos/importacion-masiva/lotes/<pk>/``: one batch with its rows.

The template and the Excel results stay native downloads. Assets are shared with the ficha preview
under ``/ciudadanos/react/``.
"""

from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from ciudadanos.services_importacion_masiva_jobs import (
    get_ciudadanos_import_job_or_404,
)
from ciudadanos.views_importacion_masiva import (
    CiudadanosImportJobDetailView,
    CiudadanosImportUploadView,
)
from ciudadanos.web_preview import (
    BUILD_ASSETS,
    PUBLIC_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ImportacionEntry(CiudadanosImportUploadView):
    """Native login and permission first, then the frozen React index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class LoteEntry(CiudadanosImportJobDetailView):
    """Native login, permission and 404 of the batch first, then the frozen React index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        get_ciudadanos_import_job_or_404(job_id=kwargs["pk"])
        return _index(request, self.index_bytes)


def importacion_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf."""
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Importacion preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path(
            "ciudadanos/importacion-masiva/",
            login_required(ImportacionEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "ciudadanos/importacion-masiva/lotes/<int:pk>/",
            login_required(LoteEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "ciudadanos/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
