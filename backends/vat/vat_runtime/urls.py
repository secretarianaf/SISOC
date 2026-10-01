"""URLs del backend de VAT (ver config/backend_urls.py)."""

from django.urls import include, path
from drf_spectacular.views import SpectacularRedocView, SpectacularSwaggerView

from config.backend_urls import urlpatterns_de_backend
from config.views import VatSpectacularAPIView

backend_urlpatterns = [
    path("", include("VAT.urls")),
    path("api/vat/", include("VAT.api_urls")),
    # Schema y docs OpenAPI de la API de VAT (antes en config/urls.py).
    path("api/schema/VAT/", VatSpectacularAPIView.as_view(), name="schema-vat"),
    path(
        "api/docs/VAT/",
        SpectacularSwaggerView.as_view(url_name="schema-vat"),
        name="swagger-ui-vat",
    ),
    path(
        "api/redoc/VAT/",
        SpectacularRedocView.as_view(url_name="schema-vat"),
        name="redoc-vat",
    ),
]

urlpatterns = urlpatterns_de_backend(backend_urlpatterns)

handler404 = "config.views.page_not_found"
handler500 = "config.views.server_error"
