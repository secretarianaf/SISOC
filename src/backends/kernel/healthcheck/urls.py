from django.urls import path

from .views import HealthUrlsView, health_check

urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("health/urls/", HealthUrlsView.as_view(), name="health_urls"),
]
