"""URLs del backend de Celiaquía (ver config/backend_urls.py)."""

from django.urls import include, path

from config.backend_urls import urlpatterns_de_backend

backend_urlpatterns = [
    path("", include("celiaquia.global_urls")),
    path("celiaquia/", include("celiaquia.urls")),
]

urlpatterns = urlpatterns_de_backend(backend_urlpatterns)

handler404 = "config.views.page_not_found"
handler500 = "config.views.server_error"
