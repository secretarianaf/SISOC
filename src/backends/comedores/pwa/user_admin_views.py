"""ABM compuesto: identidad y Espacios se validan y guardan juntos."""

from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from iam.services import get_effective_permission_codes
from pwa.models import AccesoComedorPWA
from pwa.user_forms import CustomUserChangeForm, UserCreationForm
from users.services import UsuariosService
from users.temporary_passwords import clear_temporary_password, get_temporary_password
from users.view_mixins import AdminRequiredMixin


PWA_PERMISSION_LABELS = {
    "rendicioncuentasmensual.manage_mobile_rendicion": "Gestionar rendiciones mobile",
    "pwa.manage_colaboradores_pwa": "Gestionar colaboradores mobile",
    "pwa.manage_usuarios_pwa": "Crear y gestionar usuarios mobile",
    "pwa.manage_nomina_pwa": "Gestionar nomina mobile",
    "pwa.manage_prestaciones_mensuales_pwa": "Gestionar prestaciones mensuales mobile",
}


def _get_pwa_permission_labels(user):
    permission_codes = (
        code
        for code in get_effective_permission_codes(user)
        if code.startswith("pwa.") or code.startswith("rendicioncuentasmensual.")
    )
    return [PWA_PERMISSION_LABELS.get(code, code) for code in sorted(permission_codes)]


class UserCreateView(AdminRequiredMixin, CreateView):
    model = User
    form_class = UserCreationForm
    template_name = "user/user_form.html"
    success_url = reverse_lazy("usuarios")
    required_permissions = ("auth.add_user",)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["actor"] = self.request.user
        return kwargs

    def form_valid(self, form):
        self.object = form.save()
        generated_password = getattr(form, "generated_password", None)
        if generated_password:
            messages.success(
                self.request,
                (
                    "Usuario mobile creado correctamente. "
                    f"Contraseña inicial generada: {generated_password}"
                ),
            )
            self._redirect_to_user_edit = True
            return HttpResponseRedirect(self.get_success_url())
        messages.success(self.request, "Usuario creado correctamente.")
        self._redirect_to_user_edit = False
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        if getattr(self, "_redirect_to_user_edit", False):
            return reverse_lazy("usuario_editar", kwargs={"pk": self.object.pk})
        return super().get_success_url()


class UserUpdateView(AdminRequiredMixin, UpdateView):
    model = User
    form_class = CustomUserChangeForm
    template_name = "user/user_form.html"
    success_url = reverse_lazy("usuarios")
    required_permissions = ("auth.change_user",)

    def get_queryset(self):
        # Solo se pueden editar usuarios dentro del alcance del actor.
        return (
            UsuariosService.get_usuarios_en_alcance(self.request).select_for_update()
            if self.request.method == "POST"
            else UsuariosService.get_usuarios_en_alcance(self.request)
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["actor"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = getattr(self.object, "profile", None)
        context["password_reset_requested_at"] = (
            getattr(profile, "password_reset_requested_at", None) if profile else None
        )
        temporary_password_plaintext = get_temporary_password(
            self.request.session,
            user_id=self.object.pk,
        )
        if not temporary_password_plaintext:
            temporary_password_plaintext = getattr(
                profile,
                "temporary_password_plaintext",
                None,
            )
        context["temporary_password_plaintext"] = temporary_password_plaintext
        context["temporary_password_visible"] = bool(temporary_password_plaintext)
        operator_accesses = (
            AccesoComedorPWA.objects.filter(
                user=self.object,
                rol=AccesoComedorPWA.ROL_OPERADOR,
                activo=True,
            )
            .select_related("comedor", "creado_por")
            .order_by("comedor__nombre", "id")
        )
        operator_access_list = list(operator_accesses)
        if operator_access_list:
            context["pwa_operator_context"] = {
                "accesses": operator_access_list,
                "created_by": operator_access_list[0].creado_por,
                "permission_labels": _get_pwa_permission_labels(self.object),
            }
        operadores = (
            AccesoComedorPWA.objects.filter(
                creado_por=self.object,
                rol=AccesoComedorPWA.ROL_OPERADOR,
            )
            .select_related("user", "comedor")
            .order_by("user__username", "comedor__nombre", "id")
        )
        created_users = {}
        for acceso in operadores:
            item = created_users.setdefault(
                acceso.user_id,
                {
                    "user": acceso.user,
                    "comedores": [],
                    "activo": False,
                    "permission_labels": _get_pwa_permission_labels(acceso.user),
                },
            )
            item["comedores"].append(acceso.comedor)
            item["activo"] = item["activo"] or (
                acceso.activo and getattr(acceso.user, "is_active", False)
            )
        context["pwa_created_users"] = list(created_users.values())
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        if form.cleaned_data.get("password"):
            clear_temporary_password(self.request.session, user_id=self.object.pk)
        return response


def operacion_usuario(request, data):
    """Una transacción y un dueño para la operación compuesta completa."""
    user_id = data.get("user_id")
    view = UserUpdateView if user_id is not None else UserCreateView
    kwargs = {"pk": user_id} if user_id is not None else {}
    with transaction.atomic():
        return view.as_view()(request, **kwargs)


def operacion_usuario_http(request):
    """El backend vuelve a validar sesión, CSRF, permisos y alcance del objeto."""
    from django.http import (
        HttpResponseBadRequest,
    )  # pylint: disable=import-outside-toplevel

    raw_id = request.GET.get("user_id")
    try:
        user_id = int(raw_id) if raw_id is not None else None
    except (ValueError, TypeError):
        return HttpResponseBadRequest("Usuario inválido.")
    return operacion_usuario(request, {"user_id": user_id})


def registrar_operacion_usuario():
    from core.internal_services import (
        registrar_servicio_interno,
    )  # pylint: disable=import-outside-toplevel

    registrar_servicio_interno("/interno/usuarios/operacion/", operacion_usuario)
