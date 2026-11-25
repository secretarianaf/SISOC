"""A session-protected representation of the existing canonical Sedes list."""

from django.http import JsonResponse
from django.utils.cache import patch_vary_headers

from .canonical_entry import react_enabled

from .api_views import _sede
from .filter_config import get_sede_filters_ui_config
from .views import SedeListView

SEDES_BUILD_MARKER = b'<meta name="sisoc-vpsl-sedes" content="v1"'


class CanonicalSedesListView(SedeListView):
    """Share native queryset, object scope, ordering and invalid-page behavior."""

    def render_to_response(self, context, **response_kwargs):
        if not react_enabled():
            # Flag off: the native response stays unchanged.
            return super().render_to_response(context, **response_kwargs)
        if self.request.headers.get("Accept") == "application/json":
            page = context["page_obj"]
            response = JsonResponse(
                {
                    "count": page.paginator.count,
                    "page": page.number,
                    "pages": page.paginator.num_pages,
                    "page_size": page.paginator.per_page,
                    "results": [_sede(item) for item in context["sedes"]],
                    "filters_config": get_sede_filters_ui_config(),
                }
            )
        else:
            response = super().render_to_response(context, **response_kwargs)
        response["Cache-Control"] = "private, no-store"
        patch_vary_headers(response, ("Accept", "Cookie"))
        return response
