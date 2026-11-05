"""Keep admindocs metadata from replacing the new session-only web APIs."""

import re

from django.contrib.admindocs.middleware import XViewMiddleware


class WebSessionXViewMiddleware(XViewMiddleware):
    """Preserve upstream behavior outside the explicitly owned new API paths."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method == "HEAD" and (
            request.path_info
            in {
                "/api/web/session/",
                "/api/web/insumos/",
                "/api/web/insumos/options/",
                "/api/web/insumos/crear/",
            }
            or re.fullmatch(
                r"/api/web/insumos/[0-9]+/(?:editar|eliminar)/", request.path_info
            )
        ):
            return None
        return super().process_view(request, view_func, view_args, view_kwargs)
