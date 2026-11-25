"""Session JSON transport over the native encuestas management views (G1 v1, #2785).

Each API view runs the native view (``setup`` + ``dispatch``) on the same request, so
forms, services, scope and flash messages stay the native ones. Order of checks:

1. ``WebGatePermission`` (401/403 JSON) and session CSRF on writes.
2. The same permission codes as the URL decorator in ``encuestas/urls.py``.
3. The native dispatch.

A native redirect becomes ``{"ok": true, "redirect": <Location>, "messages": [...]}``;
the queued Django messages are consumed in the same response, as the native page
would show them after the redirect. Responses are ``private, no-store``.
"""

from django.contrib import messages
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.views import View
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound, PermissionDenied, UnsupportedMediaType
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.decorators import permissions_any_required
from core.web_gate import WebGatePermission

SIN_PERMISO = "No tiene permisos para esta acción."
LEVELS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}
FORM_TYPES = ("application/x-www-form-urlencoded", "multipart/form-data")


def pending_messages(request):
    """Consume the queued flash messages as the native page does."""
    return [
        {"message": str(message), "level": LEVELS.get(message.level, "info")}
        for message in messages.get_messages(request)
    ]


class EncuestaNativeWebView(APIView):
    """Base of the encuestas management endpoints: guards, then the native view."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission]
    renderer_classes = [JSONRenderer]
    parser_classes = [FormParser, MultiPartParser]
    permission_codes = ()
    native_view = View

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        guarded = permissions_any_required(list(self.permission_codes))
        try:
            # pylint: disable-next=protected-access
            guarded(lambda req: None)(request._request)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(SIN_PERMISO) from exc

    def run_native(self, request, **kwargs):
        """Run the native view on the Django request and return its response."""
        # pylint: disable-next=protected-access
        django_request = request._request
        has_body = int(django_request.META.get("CONTENT_LENGTH") or 0) > 0
        if (
            request.method == "POST"
            and has_body
            and not any(
                (request.content_type or "").startswith(kind) for kind in FORM_TYPES
            )
        ):
            raise UnsupportedMediaType(request.content_type)
        view = self.native_view()
        view.setup(django_request, **kwargs)
        try:
            return view.dispatch(django_request, **kwargs)
        except Http404 as exc:
            raise NotFound() from exc

    def redirect_result(self, request, response, *, consume=True):
        """Native redirect as JSON, with the messages the redirected page would show.

        With ``consume=False`` the flash message stays queued for the page the client
        navigates to (a full reload, as the native form does), so it is shown there once.
        """
        if isinstance(response, HttpResponseRedirect):
            return Response(
                {
                    "ok": True,
                    "redirect": response["Location"],
                    # pylint: disable-next=protected-access
                    "messages": pending_messages(request._request) if consume else [],
                }
            )
        return None
