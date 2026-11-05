"""Keep admindocs metadata from replacing the new session-only web APIs."""

from django.contrib.admindocs.middleware import XViewMiddleware


class WebSessionXViewMiddleware(XViewMiddleware):
    """Preserve upstream behavior outside the explicitly owned new API paths."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method == "HEAD" and request.path_info in {
            "/api/web/session/",
            "/api/web/insumos/",
            "/api/web/insumos/options/",
        }:
            return None
        return super().process_view(request, view_func, view_args, view_kwargs)
