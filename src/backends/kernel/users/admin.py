from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError

from users.models import Profile
from users.profile_utils import get_profile_or_none


class WebAdminAuthenticationForm(AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not getattr(get_profile_or_none(user), "acceso_web", False):
            raise ValidationError("Este usuario no tiene acceso SISOC web habilitado.")


admin.site.login_form = WebAdminAuthenticationForm


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "source",
        "acceso_web",
        "acceso_siis",
        "must_change_password",
        "initial_password_expires_at",
    )
    list_filter = ("must_change_password", "source", "acceso_web", "acceso_siis")
    search_fields = ("user__username", "user__email")
    raw_id_fields = ("user",)
    readonly_fields = ("fecha_creacion",)
