"""Rutas de ``/api/web/comedores/`` (G1 v1) de las pantallas React de Comedores.

Cada app del backend suma acá su propio ``include``; el prefijo se publica en
``src/backends/config/backends.json`` (``url_prefixes`` de ``comedores``).
"""

from django.urls import include, path

from ciudadanos.web_aportes import AporteCiudadanoWebView

urlpatterns = [
    path("duplas/", include("duplas.web_api_urls")),
    path("", include("comedores.web_api_montos_urls")),
    path("", include("comedores.web_api_pnud_urls")),
    path(
        "admisiones/plantillas-informe/",
        include("admisiones.web_api_templates_urls"),
    ),
    path("admisiones/informes/", include("admisiones.web_api_informes_urls")),
    path("admisiones/", include("admisiones.web_api_seguimiento_urls")),
    path("acompanamientos/", include("acompanamientos.web_api_urls")),
    path("expedientespagos/", include("expedientespagos.web_api_urls")),
    path("rendicioncuentasmensual/", include("rendicioncuentasmensual.web_api_urls")),
    path("comunicados/", include("comunicados.web_api_urls")),
    path(
        "rendicion_cuentas_final/",
        include("rendicioncuentasfinal.web_api_urls"),
    ),
    path("organizaciones/", include("gestion_organizaciones.web_api_urls")),
    path("relevamientos/", include("relevamientos.web_api_urls")),
    # Aportes de Comedores y PWA a Ciudadano 360 (C04).
    path(
        "ciudadanos/<int:pk>/aportes/<str:aporte>/",
        AporteCiudadanoWebView.as_view(backend="comedores"),
        name="comedores_web_ciudadano_aporte",
    ),
]
