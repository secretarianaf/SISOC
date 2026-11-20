"""Routes of ``/api/web/dashboard/`` (G1 v1): dashboards and embedded boards in the core."""

from django.urls import path

from dashboard.web_api_dashboard import DashboardWebView, TableroWebView

urlpatterns = [
    path(
        "centro-de-familia/",
        DashboardWebView.as_view(),
        name="dashboard_web_centro_de_familia",
    ),
    path("<slug:slug>/", TableroWebView.as_view(), name="dashboard_web_tablero"),
]
