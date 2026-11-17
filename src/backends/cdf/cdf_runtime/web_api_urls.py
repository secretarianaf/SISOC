"""API web del backend CDF (``/api/web/cdf/``, G1 v1): rutas de cada app del backend."""

from django.urls import include, path

from ciudadanos.web_aportes import AporteCiudadanoWebView

urlpatterns = [
    path("", include("centrodefamilia.web_api_urls")),
    path("", include("centrodefamilia.web_api_beneficiarios_urls")),
    path("", include("centrodefamilia.web_api_actividades_urls")),
    path("", include("centrodefamilia.web_api_informecabal_urls")),
    # Aporte de Centro de Familia a Ciudadano 360 (C04).
    path(
        "ciudadanos/<int:pk>/aportes/<str:aporte>/",
        AporteCiudadanoWebView.as_view(backend="cdf"),
        name="cdf_web_ciudadano_aporte",
    ),
]
