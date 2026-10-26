"""Vistas de identidad; no importan el ABM ni los modelos de Espacios."""

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    INTERNAL_RESET_SESSION_TOKEN,
    LoginView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import FormView, UpdateView
from rest_framework.authtoken.models import Token

from users.profile_utils import needs_profile_confirmation
from usuarios.auth_forms import (
    BackofficeAuthenticationForm,
    MiCuentaForm,
    UsernameEmailPasswordResetForm,
)


class UsuariosLoginView(LoginView):
    template_name = "user/login.html"
    authentication_form = BackofficeAuthenticationForm
    redirect_authenticated_user = True


class FirstLoginPasswordChangeView(LoginRequiredMixin, FormView):
    template_name = "user/force_password_change.html"
    form_class = SetPasswordForm
    success_url = reverse_lazy("inicio")

    def dispatch(self, request, *args, **kwargs):
        profile = getattr(request.user, "profile", None)
        if not getattr(profile, "must_change_password", False):
            return HttpResponseRedirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = form.save()
        profile = getattr(user, "profile", None)
        if profile:
            profile.must_change_password = False
            profile.password_changed_at = timezone.now()
            profile.initial_password_expires_at = None
            profile.password_reset_requested_at = None
            profile.temporary_password_plaintext = None
            profile.save(
                update_fields=[
                    "must_change_password",
                    "password_changed_at",
                    "initial_password_expires_at",
                    "password_reset_requested_at",
                    "temporary_password_plaintext",
                ]
            )
        update_session_auth_hash(self.request, user)
        messages.success(self.request, "Contraseña actualizada correctamente.")
        return super().form_valid(form)


class MiCuentaView(LoginRequiredMixin, UpdateView):
    """Vista persistente para que el usuario edite sus propios datos."""

    template_name = "user/mi_cuenta.html"
    form_class = MiCuentaForm
    success_url = reverse_lazy("mi_cuenta")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Datos personales actualizados correctamente.")
        return response


class ConfirmacionDatosView(MiCuentaView):
    """Confirmación obligatoria de datos personales en el primer ingreso.

    Es una vista dedicada y no un modal embebido en el layout: el modal se
    puede saltear navegando por URL, y el requisito es bloquear la navegación
    hasta que el usuario guarde datos válidos. El bloqueo real lo hace
    ``ProfileConfirmationMiddleware``; esta vista se presenta con estética de
    modal y sin opción de cerrar.
    """

    template_name = "user/confirmar_datos.html"
    success_url = reverse_lazy("inicio")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not needs_profile_confirmation(
            request.user
        ):
            return HttpResponseRedirect(str(self.success_url))
        return super().dispatch(request, *args, **kwargs)


class PasswordResetConfirmCustomView(PasswordResetConfirmView):
    template_name = "user/password_reset_confirm.html"
    success_url = reverse_lazy("password_reset_complete")

    def dispatch(self, *args, **kwargs):
        """Permite POST directo con token sin requerir paso intermedio set-password."""
        request = args[0]
        token = kwargs.get("token")
        uidb64 = kwargs.get("uidb64")

        if (
            request.method == "POST"
            and token
            and token != self.reset_url_token
            and uidb64
        ):
            self.user = self.get_user(uidb64)
            if self.user and self.token_generator.check_token(self.user, token):
                self.request.session[INTERNAL_RESET_SESSION_TOKEN] = token
                self.validlink = True
                return FormView.dispatch(self, *args, **kwargs)

        return super().dispatch(*args, **kwargs)

    @transaction.atomic
    def form_valid(self, form):
        user = form.user
        response = super().form_valid(form)
        Token.objects.filter(user=user).delete()

        profile = getattr(user, "profile", None)
        if profile:
            profile.must_change_password = False
            profile.password_changed_at = timezone.now()
            profile.initial_password_expires_at = None
            profile.password_reset_requested_at = None
            profile.temporary_password_plaintext = None
            profile.save(
                update_fields=[
                    "must_change_password",
                    "password_changed_at",
                    "initial_password_expires_at",
                    "password_reset_requested_at",
                    "temporary_password_plaintext",
                ]
            )

        return response


class SisocPasswordResetView(PasswordResetView):
    form_class = UsernameEmailPasswordResetForm
    template_name = "user/password_reset_form.html"
    email_template_name = "user/password_reset_email.txt"
    subject_template_name = "user/password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")


class SisocPasswordResetDoneView(PasswordResetDoneView):
    template_name = "user/password_reset_done.html"


class SisocPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "user/password_reset_complete.html"
