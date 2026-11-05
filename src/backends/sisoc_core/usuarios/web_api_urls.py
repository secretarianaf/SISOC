"""Session-authenticated web routes owned by the core."""

from django.urls import path

from usuarios.web_account import WebAccountConfirmationView, WebAccountView
from usuarios.web_api_views import WebSessionView
from usuarios.web_login import WebLoginView
from usuarios.web_required_password import RequiredPasswordChangeWebView

urlpatterns = [
    path("account/", WebAccountView.as_view(), name="web_account"),
    path(
        "account/confirm/",
        WebAccountConfirmationView.as_view(),
        name="web_account_confirm",
    ),
    path("session/", WebSessionView.as_view(), name="web_session"),
    path("login/", WebLoginView.as_view(), name="web_login"),
    path(
        "password/first-change/",
        RequiredPasswordChangeWebView.as_view(),
        name="web_required_password",
    ),
]
