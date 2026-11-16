"""Explicit local React preview of the dashboards; never mounted by a production URLconf.

Each entry keeps the native URL and the native ``login_required`` guard and view dispatch (the board's
403, 404 and its own-screen redirect). Only then a plain GET returns the frozen React ``index.html``, which
loads its data from ``/api/web/dashboard/``. The assets are served by the ``ciudadanos.web_preview`` entry
under ``/ciudadanos/react/`` and must be listed with it, as the audittrail preview does.
"""

from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from ciudadanos.web_preview import BUILD_ASSETS, PUBLIC_ASSETS, _index
from dashboard.views import DashboardView, TableroEmbedView


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DashboardEntry(DashboardView):
    """Native login first, then the frozen React index (the remote metrics call is the API's)."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class TableroEntry(TableroEmbedView):
    """Native login, permission, 404 and own-screen redirect first, then the frozen React index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if isinstance(response, HttpResponseRedirect):
            return response
        return _index(request, self.index_bytes)


def dashboard_preview_patterns(build_directory):
    """Freeze the index of an explicit local ``apps/sisoc`` build for a disposable URLconf."""
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Dashboard preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path(
            "dashboard/centro-de-familia",
            login_required(DashboardEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "dashboard/<slug:slug>/",
            login_required(TableroEntry.as_view(index_bytes=index_bytes)),
        ),
    ]
