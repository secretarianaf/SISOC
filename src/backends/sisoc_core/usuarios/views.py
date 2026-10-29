from django.contrib import messages
from django.contrib.auth.models import Group, User

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import CreateView, DeleteView, FormView, ListView, UpdateView

from core.services.column_preferences import build_columns_context
from core.internal_services import reenviar_operacion_usuario

from users.admin_operations import operacion_requiere_espacios
from users.secciones_usuario import SECCIONES_COMEDORES, secciones_habilitadas
from users.view_mixins import AdminRequiredMixin
from users.services import BULK_CREDENTIALS_PERMISSION_CODE, UsuariosService
from users.services_bulk_credentials import (
    generate_bulk_credentials_template,
    get_bulk_credentials_send_type_config,
    get_bulk_credentials_send_type_contexts,
    get_bulk_credentials_template_filename,
)

from usuarios.auth_views import (
    ConfirmacionDatosView,
    FirstLoginPasswordChangeView,
    MiCuentaView,
    PasswordResetConfirmCustomView,
    SisocPasswordResetCompleteView,
    SisocPasswordResetDoneView,
    SisocPasswordResetView,
    UsuariosLoginView,
)

from .forms import (
    BulkCredentialsUploadForm,
    CustomUserChangeForm,
    GroupForm,
    UserCreationForm,
)
from .grupos_column_config import GRUPOS_COLUMNS, GRUPOS_LIST_KEY
from .services_bulk_credentials_jobs import (
    can_resume_bulk_credentials_job,
    create_bulk_credentials_job,
    get_bulk_credentials_job_or_404,
    get_recent_bulk_credentials_jobs,
    request_resume_bulk_credentials_job,
)
from .temporary_passwords import clear_temporary_password, get_temporary_password


@method_decorator(ensure_csrf_cookie, name="dispatch")
class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = "user/user_list.html"
    context_object_name = "users"
    paginate_by = 25
    required_permissions = ("auth.view_user",)

    def get_queryset(self):
        return UsuariosService.get_filtered_usuarios(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Configuracion para el componente data_table
        context.update(UsuariosService.get_usuarios_list_context(self.request))
        context["user_table_items"] = UsuariosService.build_user_table_items(
            context["users"],
            context["table_fields"],
        )
        return context


class UserDomainOperationMixin:
    """Conserva la entrada pública; dirige operaciones completas a su dueño."""

    def get(self, request, *args, **kwargs):
        if set(SECCIONES_COMEDORES).intersection(secciones_habilitadas(request.user)):
            # Obtener el objeto antes de reenviar conserva el alcance en portal;
            # el backend vuelve a comprobarlo, nunca confía en este filtro.
            if kwargs.get("pk") is not None:
                self.get_object()
            response = reenviar_operacion_usuario(request, user_id=kwargs.get("pk"))
            if response.status_code < 500:
                return response
            response.close()
            messages.warning(
                request,
                "Espacios comunitarios no está disponible. "
                "Podés realizar las operaciones independientes; sus accesos se conservan.",
            )
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # Conservar el body ANTES de leer multipart/POST, para reenviar la misma
        # operación sin reconstruir campos, archivos, sesiones ni CSRF.
        body = request.body
        instance = self.get_object() if kwargs.get("pk") is not None else None
        if operacion_requiere_espacios(request.POST, instance):
            return reenviar_operacion_usuario(
                request, user_id=kwargs.get("pk"), body=body
            )
        return super().post(request, *args, **kwargs)


class UserCreateView(AdminRequiredMixin, UserDomainOperationMixin, CreateView):
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
        try:
            self.object = form.save()
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
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


class UserUpdateView(AdminRequiredMixin, UserDomainOperationMixin, UpdateView):
    model = User
    form_class = CustomUserChangeForm
    template_name = "user/user_form.html"
    success_url = reverse_lazy("usuarios")
    required_permissions = ("auth.change_user",)

    def get_queryset(self):
        # Solo se pueden editar usuarios dentro del alcance del actor.
        return UsuariosService.get_usuarios_en_alcance(self.request)

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
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        if form.cleaned_data.get("password"):
            clear_temporary_password(self.request.session, user_id=self.object.pk)
        return response


class UserDeleteView(AdminRequiredMixin, DeleteView):
    model = User
    template_name = "user/user_confirm_delete.html"
    success_url = reverse_lazy("usuarios")
    required_permissions = ("auth.delete_user",)

    def get_queryset(self):
        return UsuariosService.get_usuarios_en_alcance(self.request)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.is_active = False
        self.object.save(update_fields=["is_active"])
        messages.success(request, "Usuario desactivado correctamente.")
        return HttpResponseRedirect(self.success_url)


class UserActiveView(AdminRequiredMixin, UpdateView):
    model = User
    template_name = "user/user_confirm_active.html"
    success_url = reverse_lazy("usuarios")
    required_permissions = ("auth.delete_user",)
    fields = []

    def get_queryset(self):
        return UsuariosService.get_usuarios_en_alcance(self.request)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.is_active = True
        self.object.save(update_fields=["is_active"])
        messages.success(request, "Usuario activado correctamente.")
        return HttpResponseRedirect(self.success_url)


class BulkCredentialsTemplateView(AdminRequiredMixin, View):
    required_permissions = (
        "auth.change_user",
        BULK_CREDENTIALS_PERMISSION_CODE,
    )
    require_all_permissions = True

    def get(self, request, *args, **kwargs):
        send_type = request.GET.get("tipo_envio")
        send_type_config = get_bulk_credentials_send_type_config(send_type)
        content = generate_bulk_credentials_template(send_type_config.key)
        response = HttpResponse(
            content,
            content_type=(
                "application/vnd.openxmlformats-officedocument." "spreadsheetml.sheet"
            ),
        )
        response["Content-Disposition"] = (
            "attachment; filename="
            f'"{get_bulk_credentials_template_filename(send_type_config.key)}"'
        )
        return response


class BulkCredentialsUploadView(AdminRequiredMixin, FormView):
    template_name = "user/bulk_credentials_form.html"
    form_class = BulkCredentialsUploadForm
    required_permissions = (
        "auth.change_user",
        BULK_CREDENTIALS_PERMISSION_CODE,
    )
    require_all_permissions = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_title"] = "Enviar credenciales masivas"
        context["template_download_url"] = reverse("usuarios_credenciales_plantilla")
        context["send_type_options"] = get_bulk_credentials_send_type_contexts()
        context["recent_jobs"] = get_recent_bulk_credentials_jobs(
            requested_by=self.request.user,
        )
        return context

    def form_valid(self, form):
        send_type = form.cleaned_data["tipo_envio"]
        send_type_config = get_bulk_credentials_send_type_config(send_type)
        try:
            job = create_bulk_credentials_job(
                uploaded_file=form.cleaned_data["archivo"],
                send_type=send_type,
                requested_by=self.request.user,
            )
        except ValidationError as exc:
            form.add_error("archivo", " ".join(exc.messages))
            return self.form_invalid(form)

        messages.success(
            self.request,
            (
                f"Lote creado para {send_type_config.label}. "
                "El procesamiento continuara en background. "
                "Puede seguir el estado desde el detalle del lote."
            ),
        )
        return HttpResponseRedirect(
            reverse(
                "usuarios_credenciales_masivas_detalle",
                kwargs={"pk": job.pk},
            )
        )


class BulkCredentialsJobDetailView(AdminRequiredMixin, View):
    required_permissions = (
        "auth.change_user",
        BULK_CREDENTIALS_PERMISSION_CODE,
    )
    require_all_permissions = True
    template_name = "user/bulk_credentials_job_detail.html"
    paginate_by = 50

    def get(self, request, *args, **kwargs):
        job = get_bulk_credentials_job_or_404(job_id=kwargs["pk"])
        rows_qs = job.rows.order_by("fila", "id")
        paginator = Paginator(rows_qs, self.paginate_by)
        page_obj = paginator.get_page(request.GET.get("page"))
        return self.render_to_response(
            {
                "job": job,
                "page_obj": page_obj,
                "is_resume_available": can_resume_bulk_credentials_job(job),
                "upload_url": reverse("usuarios_credenciales_masivas"),
                "volver_url": reverse("usuarios_credenciales_masivas"),
            }
        )

    def render_to_response(self, context):
        return render(self.request, self.template_name, context)


class BulkCredentialsJobResumeView(AdminRequiredMixin, View):
    required_permissions = (
        "auth.change_user",
        BULK_CREDENTIALS_PERMISSION_CODE,
    )
    require_all_permissions = True

    def post(self, request, *args, **kwargs):
        job = get_bulk_credentials_job_or_404(job_id=kwargs["pk"])
        try:
            request_resume_bulk_credentials_job(job=job)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            messages.success(
                request,
                (
                    "El lote quedo pendiente para reanudarse desde "
                    "la ultima fila fallida."
                ),
            )
        return HttpResponseRedirect(
            reverse(
                "usuarios_credenciales_masivas_detalle",
                kwargs={"pk": job.pk},
            )
        )


@method_decorator(ensure_csrf_cookie, name="dispatch")
class GroupListView(AdminRequiredMixin, ListView):
    model = Group
    template_name = "group/group_list.html"
    context_object_name = "groups"
    required_permissions = ("auth.view_group",)

    def get_queryset(self):
        queryset = Group.objects.annotate(
            permissions_count=Count("permissions", distinct=True)
        ).order_by("name")
        query = (self.request.GET.get("busqueda") or "").strip()
        if query:
            queryset = queryset.filter(name__icontains=query)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Configuracion para el componente data_table
        context.update(
            build_columns_context(
                self.request,
                GRUPOS_LIST_KEY,
                GRUPOS_COLUMNS,
            )
        )
        context["table_actions"] = [
            {
                "label": "Editar",
                "url_name": "grupo_editar",
                "type": "editar",
                "icon": "edit",
            }
        ]
        context["query"] = (self.request.GET.get("busqueda") or "").strip()

        return context


class GroupCreateView(AdminRequiredMixin, CreateView):
    model = Group
    form_class = GroupForm
    template_name = "group/group_form.html"
    success_url = reverse_lazy("grupos")
    required_permissions = ("auth.add_group",)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Grupo creado correctamente.")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_title"] = "Crear grupo"
        context["submit_text"] = "Crear grupo"
        return context


class GroupUpdateView(AdminRequiredMixin, UpdateView):
    model = Group
    form_class = GroupForm
    template_name = "group/group_form.html"
    success_url = reverse_lazy("grupos")
    required_permissions = ("auth.change_group",)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Grupo actualizado correctamente.")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_title"] = "Editar grupo"
        context["submit_text"] = "Guardar cambios"
        return context


__all__ = [
    "UserListView",
    "UserDomainOperationMixin",
    "UserCreateView",
    "UserUpdateView",
    "UserDeleteView",
    "UserActiveView",
    "BulkCredentialsTemplateView",
    "BulkCredentialsUploadView",
    "BulkCredentialsJobDetailView",
    "BulkCredentialsJobResumeView",
    "GroupListView",
    "GroupCreateView",
    "GroupUpdateView",
    "AdminRequiredMixin",
    "ConfirmacionDatosView",
    "FirstLoginPasswordChangeView",
    "MiCuentaView",
    "PasswordResetConfirmCustomView",
    "SisocPasswordResetCompleteView",
    "SisocPasswordResetDoneView",
    "SisocPasswordResetView",
    "UsuariosLoginView",
]
