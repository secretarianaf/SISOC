"""Keep admindocs HEAD metadata from replacing the new session contract."""

from django.contrib.admindocs.middleware import XViewMiddleware


class WebSessionXViewMiddleware(XViewMiddleware):
    """Preserve upstream behavior except for the exact new session HEAD path."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method == "HEAD" and request.path_info == "/api/web/session/":
            return None
        return super().process_view(request, view_func, view_args, view_kwargs)
