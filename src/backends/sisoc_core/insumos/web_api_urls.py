"""Session-authenticated INS-A read routes owned by Insumos."""

from django.urls import path

from insumos.web_api_views import InsumosWebListView, InsumosWebOptionsView

urlpatterns = [
    path("", InsumosWebListView.as_view(), name="web_insumos_list"),
    path("options/", InsumosWebOptionsView.as_view(), name="web_insumos_options"),
]
