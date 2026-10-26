from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from unfold.forms import (
    AdminPasswordChangeForm,
    AuthenticationForm,
    UserChangeForm,
    UserCreationForm,
)

from core.admin_base import SisocModelAdmin
from users.models import Profile
from users.profile_utils import get_profile_or_none


# AuthenticationForm de Unfold hereda de AdminAuthenticationForm: conserva el
# chequeo de usuario activo y staff, y suma el acceso web.
class WebAdminAuthenticationForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not getattr(get_profile_or_none(user), "acceso_web", False):
            raise ValidationError("Este usuario no tiene acceso SISOC web habilitado.")


admin.site.login_form = WebAdminAuthenticationForm

# User y Group los registra django.contrib.auth con el admin clásico; se
# re-registran con Unfold sin cambiar su comportamiento (#2789).
admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, SisocModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, SisocModelAdmin):
    pass


@admin.register(Profile)
class ProfileAdmin(SisocModelAdmin):
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
