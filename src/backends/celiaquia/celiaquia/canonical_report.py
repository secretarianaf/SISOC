"""Serve the compatible Celiaquía shell on the guarded provincial report URL."""

from copy import copy
from functools import wraps

from django.conf import settings
from django.http import Http404
from django.utils.cache import patch_vary_headers

from celiaquia.views.reporter_provincias import ReporterProvinciasView
from core import v2_frontend

BUILD_MARKER = b'<meta name="sisoc-celiaquia-report" content="v1"'
_native_report = ReporterProvinciasView.as_view()


@wraps(_native_report)
def canonical_report(request, *args, **kwargs):
    # The exact URL still applies its original report permission first.
    if (
        request.method not in {"GET", "HEAD"}
        or "celiaquia" not in settings.REACT_VERTICALES_ACTIVAS
    ):
        return _native_report(request, *args, **kwargs)

    upstream_request = copy(request)
    upstream_request.method = (
        "GET"  # HEAD checks the same artifact without emitting its body.
    )
    upstream_request.META = {**request.META, "QUERY_STRING": ""}
    try:
        shell = v2_frontend.frontend_v2(upstream_request, "celiaquia")
    except Http404:
        return _native_report(request, *args, **kwargs)

    if (
        shell.status_code != 200
        or not shell.headers.get("Content-Type", "").startswith("text/html")
        or BUILD_MARKER not in shell.content
    ):
        return _native_report(request, *args, **kwargs)

    if request.method == "HEAD":
        shell["Content-Length"] = str(len(shell.content))
        shell.content = b""
    shell["Cache-Control"] = "private, no-store"
    patch_vary_headers(shell, ("Cookie",))
    return shell
