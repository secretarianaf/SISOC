"""Explicit local React preview of the instance history (C05); never mounted by a production URLconf.

The entry keeps the native URL ``auditoria/<app_label>/<model_name>/<object_pk>/`` and its
guards: anonymous users get the login redirect, users without ``auditlog.view_logentry`` the
native 403, and an out-of-range page the native 404 (the native ``get`` runs for that). Only
then a plain GET returns the frozen React ``index.html``; a request with ``?export=`` (the
CSV/JSON buttons of the page) is answered by the native view itself. The assets are served by
the ``ciudadanos.web_preview`` entry under ``/ciudadanos/react/`` and must be listed with it.
"""

from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from audittrail.views import (
    AuditLogDetailView,
    AuditLogInstanceView,
    AuditLogListView,
)
from ciudadanos.web_preview import BUILD_ASSETS, PUBLIC_ASSETS, _index


@method_decorator(ensure_csrf_cookie, name="dispatch")
class HistorialEntry(AuditLogInstanceView):
    """Native login, permission and 404 first, then the frozen React index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        respuesta = super().get(request, *args, **kwargs)
        if (request.GET.get("export") or "").strip().lower() in {"csv", "json"}:
            return respuesta
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ListadoEntry(AuditLogListView):
    """Native guards of the global list first, then the frozen React index (export stays native)."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        respuesta = super().get(request, *args, **kwargs)
        if (request.GET.get("export") or "").strip().lower() in {"csv", "json"}:
            return respuesta
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EventoEntry(AuditLogDetailView):
    """Native login, permission and 404 of the event detail first, then the frozen React index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        super().get(request, *args, **kwargs)
        return _index(request, self.index_bytes)


def audittrail_preview_patterns(build_directory):
    """Freeze the index of an explicit local ``apps/sisoc`` build for a disposable URLconf."""
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Audittrail preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path(
            "auditoria/", login_required(ListadoEntry.as_view(index_bytes=index_bytes))
        ),
        path(
            "auditoria/evento/<int:pk>/",
            login_required(EventoEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "auditoria/<str:app_label>/<str:model_name>/<str:object_pk>/",
            login_required(HistorialEntry.as_view(index_bytes=index_bytes)),
        ),
    ]
