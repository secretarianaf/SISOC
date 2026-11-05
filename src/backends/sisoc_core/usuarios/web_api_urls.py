"""Session-authenticated web routes owned by the core."""

from django.urls import path

from usuarios.web_api_views import WebSessionView
from usuarios.web_login import WebLoginView
from usuarios.web_required_password import RequiredPasswordChangeWebView

urlpatterns = [
    path("session/", WebSessionView.as_view(), name="web_session"),
    path("login/", WebLoginView.as_view(), name="web_login"),
    path(
        "password/first-change/",
        RequiredPasswordChangeWebView.as_view(),
        name="web_required_password",
    ),
]
