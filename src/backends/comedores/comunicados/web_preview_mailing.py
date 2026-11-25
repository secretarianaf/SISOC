"""Explicit local React preview of the mass mailing (CM01); never mounted by a production URLconf.

The entries keep the native URLs and the native views' ``dispatch``: anonymous
users get the login redirect, users that are not ``is_admin`` the native 403 and
a missing batch the native 404. Only then a GET returns the frozen React
``index.html``, which loads its data from ``/api/web/comedores/comunicados/mailing/``.
Other methods reach the native views unchanged (the native resume POST included);
the XLSX template stays the native view. Assets are served under
``/comunicados/mailing-react/``.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from comedores.web_preview_catalogos import (
    BUILD_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)
from comunicados.services_mailing_jobs import get_mailing_job_or_404
from comunicados.views import MailingJobDetailView, MailingUploadView

PUBLIC_ASSETS = "/comunicados/mailing-react/assets/"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class FormEntry(MailingUploadView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class JobEntry(MailingJobDetailView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        # Same Http404 as the native detail for a missing batch.
        get_mailing_job_or_404(job_id=kwargs["pk"])
        return _index(request, self.index_bytes)


def mailing_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Mailing preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path("comunicados/mailing/", FormEntry.as_view(index_bytes=index_bytes)),
        path(
            "comunicados/mailing/lotes/<int:pk>/",
            JobEntry.as_view(index_bytes=index_bytes),
        ),
        path(
            "comunicados/mailing-react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
