from django.urls import include, path
from rest_framework.routers import DefaultRouter

from comedores.dashboard_metrics import MetricasDashboardView
from comedores.api_views import ComedorDetailViewSet, NominaViewSet

router = DefaultRouter()
router.register(r"nomina", NominaViewSet, basename="api-nomina")
router.register(r"", ComedorDetailViewSet, basename="api-comedor")

urlpatterns = [
    path(
        "metricas-dashboard/",
        MetricasDashboardView.as_view(),
        name="comedores-metricas-dashboard",
    ),
    path("", include(router.urls)),
]
