"""Serve the VPSL React shell after the existing canonical view accepts the GET."""

from copy import copy
from functools import wraps

from django.conf import settings
from django.http import Http404
from django.utils.cache import patch_vary_headers

from core import v2_frontend
from core.react_activation import TODAS

CANONICAL_BUILD_MARKER = b'<meta name="sisoc-vpsl-canonical" content="v1"'


def react_enabled():
    # Same semantics as core.react_activation: "todas" (the default) or the key.
    active = getattr(settings, "REACT_VERTICALES_ACTIVAS", ()) or ()
    return "vpsl" in active or TODAS in active


def _serves_react(request, native, native_list_query):
    """Only successful native HTML GET/HEAD pages can switch to the shell."""
    if request.method not in {"GET", "HEAD"} or not react_enabled():
        return False
    # The canonical lists already have bookmarkable filters and pagination
    # that the standalone app does not implement yet.
    if native_list_query and bool(request.GET) and set(request.GET) != {"sede"}:
        return False
    return native.status_code == 200 and native.headers.get(
        "Content-Type", ""
    ).startswith("text/html")


def canonical_entry(
    view, *, native_list_query=False, build_marker=CANONICAL_BUILD_MARKER
):
    """Keep the decorated native view, including its dispatch and object scope."""

    @wraps(view)
    def entry(request, *args, **kwargs):
        native = view(request, *args, **kwargs)
        if not _serves_react(request, native, native_list_query):
            return native

        # Fetch only the static shell. The browser retains its original query
        # and the static service does not receive application parameters.
        upstream_request = copy(request)
        upstream_request.method = "GET"  # Verify the same build on GET and HEAD.
        upstream_request.META = {**request.META, "QUERY_STRING": ""}
        try:
            shell = v2_frontend.frontend_v2(upstream_request, "vpsl")
        except Http404:
            return native
        if (
            shell.status_code != 200
            or not shell.headers.get("Content-Type", "").startswith("text/html")
            or build_marker not in shell.content
        ):
            return native
        if request.method == "HEAD":
            shell["Content-Length"] = str(len(shell.content))
            shell.content = b""
        shell["Cache-Control"] = "private, no-store"
        patch_vary_headers(shell, ("Cookie", "Accept"))
        return shell

    return entry
