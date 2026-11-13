"""Session-authenticated web routes owned by the core."""

from django.urls import include, path

from encuestas.web_answer import (
    WebAnswerSurveyView,
    WebDismissSurveyView,
    WebPendingSurveyView,
    WebPostponeSurveyView,
)

from usuarios.web_account import WebAccountConfirmationView, WebAccountView
from usuarios.web_api_views import WebSessionView
from usuarios.web_groups import (
    WebGroupCreateView,
    WebGroupListView,
    WebGroupUpdateView,
)
from usuarios.web_login import WebLoginView
from usuarios.web_password_change import WebPasswordChangeView
from usuarios.web_password_reset import (
    WebPasswordResetConfirmView,
    WebPasswordResetView,
)
from usuarios.web_required_password import RequiredPasswordChangeWebView
from usuarios.web_users import (
    WebUserActivateView,
    WebUserDeactivateView,
    WebUserListView,
)

urlpatterns = [
    path("surveys/pending/", WebPendingSurveyView.as_view(), name="web_survey_pending"),
    path(
        "surveys/<int:pk>/answer/",
        WebAnswerSurveyView.as_view(),
        name="web_survey_answer",
    ),
    path(
        "surveys/<int:pk>/postpone/",
        WebPostponeSurveyView.as_view(),
        name="web_survey_postpone",
    ),
    path(
        "surveys/<int:pk>/dismiss/",
        WebDismissSurveyView.as_view(),
        name="web_survey_dismiss",
    ),
    path("users/import/", include("usuarios.web_user_import_urls")),
    path("users/bulk-credentials/", include("usuarios.web_bulk_credentials_urls")),
    path("users/list/", WebUserListView.as_view(), name="web_users"),
    path(
        "users/<int:pk>/deactivate/",
        WebUserDeactivateView.as_view(),
        name="web_user_deactivate",
    ),
    path(
        "users/<int:pk>/activate/",
        WebUserActivateView.as_view(),
        name="web_user_activate",
    ),
    path("groups/", WebGroupListView.as_view(), name="web_groups"),
    path("groups/create/", WebGroupCreateView.as_view(), name="web_group_create"),
    path("groups/<int:pk>/edit/", WebGroupUpdateView.as_view(), name="web_group_edit"),
    path("account/", WebAccountView.as_view(), name="web_account"),
    path(
        "account/confirm/",
        WebAccountConfirmationView.as_view(),
        name="web_account_confirm",
    ),
    path("session/", WebSessionView.as_view(), name="web_session"),
    path("login/", WebLoginView.as_view(), name="web_login"),
    path(
        "password/change/",
        WebPasswordChangeView.as_view(),
        name="web_password_change",
    ),
    path(
        "password/reset/",
        WebPasswordResetView.as_view(),
        name="web_password_reset",
    ),
    path(
        "password/reset/<uidb64>/",
        WebPasswordResetConfirmView.as_view(),
        name="web_password_reset_confirm",
    ),
    path(
        "password/first-change/",
        RequiredPasswordChangeWebView.as_view(),
        name="web_required_password",
    ),
]
