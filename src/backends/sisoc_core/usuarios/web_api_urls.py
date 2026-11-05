"""Session-authenticated web routes owned by the core."""

from django.urls import path

from usuarios.web_api_views import WebSessionView
from usuarios.web_login import WebLoginView

urlpatterns = [
    path("session/", WebSessionView.as_view(), name="web_session"),
    path("login/", WebLoginView.as_view(), name="web_login"),
]
