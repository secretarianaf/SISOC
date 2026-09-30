"""Authenticated, allowlisted router for static Front v2 applications."""

import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseNotAllowed


@login_required
def frontend_v2(request, module, asset_path=""):
    upstream = settings.FRONTEND_V2_UPSTREAMS.get(module)
    if upstream is None:
        raise Http404
    if request.method not in ("GET", "HEAD"):
        return HttpResponseNotAllowed(["GET", "HEAD"])
    segments = asset_path.split("/")
    if any(part in (".", "..") or "\\" in part for part in segments):
        raise Http404

    encoded_path = "/".join(quote(part, safe="-._~") for part in segments)
    path = f"/v2/{module}/{encoded_path}"
    if request.META.get("QUERY_STRING"):
        path += "?" + request.META["QUERY_STRING"]
    outbound = Request(
        upstream.rstrip("/") + path,
        method=request.method,
        headers={"Accept-Encoding": "identity"},
    )
    try:
        with urlopen(outbound, timeout=3) as source:
            body = source.read() if request.method == "GET" else b""
            status = source.status
            content_type = source.headers.get(
                "Content-Type", "application/octet-stream"
            )
    except HTTPError as exc:
        if exc.code == 404:
            raise Http404 from exc
        return HttpResponse(status=503)
    except (URLError, TimeoutError, OSError):
        return HttpResponse(status=503)

    response = HttpResponse(body, status=status, content_type=content_type)
    filename = asset_path.rsplit("/", 1)[-1]
    if asset_path.startswith("assets/") and re.search(
        r"-[A-Za-z0-9_-]{6,}\.[A-Za-z0-9]+$", filename
    ):
        response["Cache-Control"] = "public, max-age=31536000, immutable"
    else:
        response["Cache-Control"] = "no-cache"
    return response


def schema_endpoints(endpoints):
    """Limit the versioned Front v2 contract to its consumed HTTP API."""
    return [entry for entry in endpoints if entry[0].startswith("/api/vpsl/")]
