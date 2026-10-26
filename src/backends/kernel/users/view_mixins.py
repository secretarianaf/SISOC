"""Controles comunes de las pantallas administrativas de identidad."""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    required_permissions: tuple[str, ...] = tuple()
    require_all_permissions = False

    def get_required_permissions(self):
        return tuple(self.required_permissions)

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True

        required_permissions = self.get_required_permissions()
        if not required_permissions:
            return False

        if self.require_all_permissions:
            return all(user.has_perm(code) for code in required_permissions)
        return any(user.has_perm(code) for code in required_permissions)
