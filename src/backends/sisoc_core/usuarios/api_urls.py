from django.urls import include, path
from rest_framework.routers import DefaultRouter
from usuarios.siis_api_views import SIISAdminTokenView, SIISUserCreateView

from usuarios.api_views import (
    PasswordChangeRequiredViewSet,
    PasswordResetConfirmViewSet,
    PasswordResetRequestViewSet,
    UserContextViewSet,
    UserLoginViewSet,
    UserLogoutViewSet,
)

router = DefaultRouter()
router.register(r"login", UserLoginViewSet, basename="api-user-login")
router.register(r"logout", UserLogoutViewSet, basename="api-user-logout")
router.register(r"me", UserContextViewSet, basename="api-user-context")
router.register(
    r"password-change-required",
    PasswordChangeRequiredViewSet,
    basename="api-user-password-change-required",
)
router.register(
    r"password-reset/request",
    PasswordResetRequestViewSet,
    basename="api-user-password-reset-request",
)
router.register(
    r"password-reset/confirm",
    PasswordResetConfirmViewSet,
    basename="api-user-password-reset-confirm",
)

urlpatterns = [
    path(
        "siis/admin-token/", SIISAdminTokenView.as_view(), name="api-siis-admin-token"
    ),
    path("siis/", SIISUserCreateView.as_view(), name="api-siis-user-create"),
    path("", include(router.urls)),
]
