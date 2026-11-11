"""Rutas de ``/api/web/comedores/`` (G1 v1) de las pantallas React de Comedores.

Cada app del backend suma acá su propio ``include``; el prefijo se publica en
``src/backends/config/backends.json`` (``url_prefixes`` de ``comedores``).
"""

from django.urls import include, path

urlpatterns = [
    path("duplas/", include("duplas.web_api_urls")),
    path("", include("comedores.web_api_montos_urls")),
    path("", include("comedores.web_api_pnud_urls")),
    path(
        "admisiones/plantillas-informe/",
        include("admisiones.web_api_templates_urls"),
    ),
    path("acompanamientos/", include("acompanamientos.web_api_urls")),
    path("expedientespagos/", include("expedientespagos.web_api_urls")),
    path("rendicioncuentasmensual/", include("rendicioncuentasmensual.web_api_urls")),
]
