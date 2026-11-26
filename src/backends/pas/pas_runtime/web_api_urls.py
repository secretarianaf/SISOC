"""Routes of ``/api/web/pas/`` (G1 v1) of the PAS React back-office screens.

The prefix is published in ``src/backends/config/backends.json`` (``url_prefixes``
of ``pas``); each delivery adds its routes to ``pas.web_api_urls``. The public
DDJJ JSON routes stay under ``/pas/ddjj/`` (``pas.web_ddjj_urls``).
"""

from django.urls import include, path

urlpatterns = [
    path("", include("pas.web_api_urls")),
]
