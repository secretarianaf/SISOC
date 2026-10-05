from django.http import HttpResponseServerError
from django.template import loader
from django.views import defaults
from drf_spectacular.views import SpectacularAPIView

from config.api_errors import es_ruta_api, respuesta_json_404, respuesta_json_500


def server_error(request, template_name="500.html"):
    """Return a static 500 error response without invoking context processors.

    Bajo ``/api/`` responde ``{"detail": ...}`` en JSON: la app y GESTIONAR no
    pueden leer la página HTML.
    """
    if es_ruta_api(request):
        return respuesta_json_500()
    template = loader.get_template(template_name)
    return HttpResponseServerError(template.render())


def page_not_found(request, exception, template_name="404.html"):
    """404 de ruteo: JSON bajo ``/api/`` (p. ej. un pk no numérico), la página
    de siempre en el resto del sitio."""
    if es_ruta_api(request):
        return respuesta_json_404()
    return defaults.page_not_found(request, exception, template_name=template_name)


class VatSpectacularAPIView(SpectacularAPIView):
    """Expone un schema OpenAPI filtrado solo a endpoints `/api/vat/`."""

    VAT_PATH_PREFIX = "/api/vat/"

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        schema = getattr(response, "data", None)
        if not isinstance(schema, dict):
            return response

        schema = dict(schema)

        paths = schema.get("paths") or {}
        schema["paths"] = {
            path: value
            for path, value in paths.items()
            if str(path).startswith(self.VAT_PATH_PREFIX)
        }

        info = schema.get("info")
        if isinstance(info, dict):
            info = dict(info)
            title = info.get("title") or "API"
            info["title"] = f"{title} - VAT"
            schema["info"] = info

        response.data = schema
        return response
