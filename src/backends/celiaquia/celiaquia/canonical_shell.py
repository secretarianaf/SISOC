"""Serve the compatible Celiaquía React shell on guarded canonical URLs.

Each canonical screen keeps its Django URL, permission decorator and native
view. When the ``celiaquia`` vertical is active, GET/HEAD returns the React
shell only if the build declares the screen marker; otherwise, or when the
static build is missing, the native view answers. A screen may also expose a
private JSON projection on the same URL through ``Accept: application/json``.
"""

from copy import copy
from functools import wraps

from django.conf import settings
from django.http import Http404
from django.utils.cache import patch_vary_headers
from django.views.decorators.csrf import ensure_csrf_cookie

from core import v2_frontend


def marker(screen):
    return f'<meta name="sisoc-celiaquia-{screen}" content="v1"'.encode()


def react_enabled():
    return "celiaquia" in settings.REACT_VERTICALES_ACTIVAS


def wants_json(request):
    return "application/json" in request.headers.get("Accept", "")


def compatible_shell(request, build_marker):
    """Return the static shell when it declares ``build_marker``, else None."""
    upstream = copy(request)
    # HEAD checks the same artifact; the query never reaches the static server.
    upstream.method = "GET"
    upstream.META = {**request.META, "QUERY_STRING": ""}
    try:
        shell = v2_frontend.frontend_v2(upstream, "celiaquia")
    except Http404:
        return None
    if (
        shell.status_code != 200
        or not shell.headers.get("Content-Type", "").startswith("text/html")
        or build_marker not in shell.content
    ):
        return None
    if request.method == "HEAD":
        shell["Content-Length"] = str(len(shell.content))
        shell.content = b""
    return shell


def canonical_screen(native_view, screen, projection=None, submit=None):
    """Wrap ``native_view`` so its URL can serve the React screen ``screen``.

    ``projection(request, *args, **kwargs)`` builds the JSON representation.
    It must reuse the native scope and rules; the outer URL decorator still
    authorizes the request before this wrapper runs. ``submit`` optionally
    answers JSON POSTs (``Accept: application/json``) with the native form
    rules; any other POST keeps reaching the native view unchanged.
    """
    build_marker = marker(screen)

    @ensure_csrf_cookie
    def react_view(request, *args, **kwargs):
        response = None
        if request.method in {"GET", "HEAD"}:
            if projection is not None and wants_json(request):
                response = projection(request, *args, **kwargs)
            else:
                response = compatible_shell(request, build_marker)
        elif submit is not None and request.method == "POST":
            if wants_json(request):
                response = submit(request, *args, **kwargs)
        if response is None:
            response = native_view(request, *args, **kwargs)
        if response.status_code == 200:
            response["Cache-Control"] = "private, no-store"
            patch_vary_headers(response, ("Accept", "Cookie"))
        return response

    @wraps(native_view)
    def view(request, *args, **kwargs):
        if not react_enabled():
            # Flag off: the native response stays byte-for-byte unchanged.
            return native_view(request, *args, **kwargs)
        return react_view(request, *args, **kwargs)

    return view
