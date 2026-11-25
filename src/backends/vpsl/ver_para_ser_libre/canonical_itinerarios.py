"""Represent the native authorized itinerary list without duplicating its rules."""

from django.http import JsonResponse
from django.utils.cache import patch_vary_headers

from .canonical_entry import react_enabled

from .api_views import _itinerario
from .views import ItinerarioListView

ITINERARIOS_BUILD_MARKER = b'<meta name="sisoc-vpsl-itinerarios" content="v1"'


class CanonicalItinerariosListView(ItinerarioListView):
    """Keep native territorial scope before search, advanced filters and paging."""

    def render_to_response(self, context, **response_kwargs):
        if not react_enabled():
            # Flag off: the native response stays unchanged.
            return super().render_to_response(context, **response_kwargs)
        if self.request.headers.get("Accept") == "application/json":
            page = context["page_obj"]
            restricted = context["provincia_restringida"]
            response = JsonResponse(
                {
                    "count": page.paginator.count,
                    "page": page.number,
                    "pages": page.paginator.num_pages,
                    "page_size": page.paginator.per_page,
                    "results": [_itinerario(item) for item in context["itinerarios"]],
                    "filters_config": context["filters_config"],
                    "estados": [
                        {"value": value, "label": label}
                        for value, label in context["estado_choices"]
                    ],
                    "provincias": [
                        {"id": province.pk, "nombre": province.nombre}
                        for province in context["provincias"]
                    ],
                    "provincia_restringida": (
                        {"id": restricted.pk, "nombre": restricted.nombre}
                        if restricted
                        else None
                    ),
                }
            )
        else:
            response = super().render_to_response(context, **response_kwargs)
        response["Cache-Control"] = "private, no-store"
        patch_vary_headers(response, ("Accept", "Cookie"))
        return response
