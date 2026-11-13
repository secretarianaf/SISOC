"""Session transport over the native user create/edit form (U08, core fields).

The native views, ``UserCreationForm``/``CustomUserChangeForm`` and their
section, delegation and scope rules stay the only owners of validation and
persistence: this module runs their ``get_form()``/``post()`` and projects the
bound form. Nothing here widens who can create or edit a user, what groups or
permissions they can assign, or which credential is visible.

Comedores sections (mobile access, territorial, technical teams) belong to the
Comedores owner (``pwa.web_user_form``): the same relay the native views use
sends the request there and the owner's JSON is returned with the portal's
presentation. When the owner is unavailable a read falls back to the core form
with the native warning and a write is refused without any mutation.
"""

import json
from urllib.parse import urlencode

from django import forms
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import CreateView, UpdateView
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from core.backend_proxy import backend_de_app, reenviar_a_backend
from core.internal_services import RespuestaInterna, pedir_json_interno
from users.admin_operations import operacion_requiere_espacios
from users.secciones_usuario import SECCIONES_COMEDORES, secciones_habilitadas
from usuarios.views import (
    UserCreateView,
    UserUpdateView,
)
from usuarios.web_context import build_legacy_presentation
from usuarios.web_users import _UserTransportMixin, pending_messages

# Fields of each native card, in template order. ``None`` means always rendered;
# otherwise the form flag that gates the card.
SECTIONS = (
    ("personal", None, ("first_name", "last_name", "dni", "cuil", "tipo_usuario")),
    ("access", None, ("username", "email", "password")),
    (
        "datacalle",
        "can_manage_datacalle",
        ("es_relevador_calle", "datacalle_rol", "provincias_datacalle"),
    ),
    (
        "inspecciones",
        "can_manage_inspecciones_escolares",
        ("es_inspector_escolar", "inspecciones_rol"),
    ),
    ("permissions", None, ("groups", "rol")),
    (
        "territorial",
        None,
        ("es_usuario_provincial", "provincia", "territorial_scopes"),
    ),
    (
        "delegation",
        "can_manage_delegation",
        (
            "user_permissions",
            "acceso_web",
            "acceso_siis",
            "grupos_asignables",
            "roles_asignables",
        ),
    ),
)
# Controls for which the native template emits ``_identity_present`` (only when
# the field is rendered and not disabled), so an emptied control is a change.
IDENTITY_PRESENT = (
    "es_relevador_calle",
    "provincias_datacalle",
    "es_inspector_escolar",
    "groups",
    "es_usuario_provincial",
    "user_permissions",
    "acceso_web",
    "acceso_siis",
    "grupos_asignables",
    "roles_asignables",
)
REQUIRES_RUNTIME = {
    "detail": (
        "La operación requiere validar Espacios comunitarios y no puede "
        "completarse desde esta pantalla."
    ),
    "state": "comedores_runtime_required",
}
OWNER_PATH = "interno/usuarios/operacion-web/"
UNAVAILABLE_WARNING = (
    "Espacios comunitarios no está disponible. "
    "Podés realizar las operaciones independientes; sus accesos se conservan."
)


def relay_to_owner(request, user_id, body=None):
    """Send this operation to the Comedores owner: its backend, or the local handler."""
    backend = backend_de_app("pwa")
    if backend is not None:
        return reenviar_a_backend(
            request,
            backend,
            path=OWNER_PATH,
            query_string=urlencode({"user_id": user_id}) if user_id is not None else "",
            body=body,
            uncertain_on_failure=request.method == "POST",
        )
    answer = pedir_json_interno(
        request, "pwa", "/" + OWNER_PATH, data={"user_id": user_id}
    )
    if isinstance(answer, RespuestaInterna):
        missing = JsonResponse({"detail": UNAVAILABLE_WARNING}, status=503)
        missing.owner_missing = True  # nothing ran: a write changed nothing
        return missing
    return answer


def owner_payload(response):
    """The owner answered JSON, or the relay itself failed."""
    # The backend proxy answers a stream; the local owner an ordinary response.
    raw = (
        b"".join(response.streaming_content)
        if getattr(response, "streaming", False)
        else response.content
    )
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _kind(field):
    widget = field.widget
    checks = (
        (isinstance(widget, forms.PasswordInput), "password"),
        (isinstance(widget, forms.HiddenInput), "hidden"),
        (isinstance(field, forms.BooleanField), "boolean"),
        (isinstance(widget, forms.RadioSelect), "radio"),
        (isinstance(widget, forms.SelectMultiple), "multiselect"),
        (isinstance(field, forms.ChoiceField), "select"),
        (isinstance(field, forms.EmailField), "email"),
    )
    return next((kind for matches, kind in checks if matches), "text")


def _value(bound, kind):
    if kind == "password":
        return ""
    value = bound.value()
    if kind == "boolean":
        return bool(value)
    if kind == "multiselect":
        return [str(item) for item in (value or [])]
    return "" if value is None else str(value)


def _spec(form, name):
    bound = form[name]
    field = bound.field
    kind = _kind(field)
    spec = {
        "name": name,
        "kind": kind,
        "label": str(field.label or ""),
        "required": field.required,
        "disabled": bool(field.disabled),
        "help_text": str(field.help_text or ""),
        "max_length": getattr(field, "max_length", None),
        "value": _value(bound, kind),
    }
    if kind in ("radio", "select", "multiselect"):
        spec["choices"] = [
            {"value": str(value), "label": str(label)} for value, label in field.choices
        ]
    return spec


def project_form(form):
    """Fields exactly as the native cards render them, with their bound value."""
    sections = []
    present = []
    for key, flag, names in SECTIONS:
        if flag is not None and not getattr(form, flag, False):
            continue
        fields = [_spec(form, name) for name in names]
        sections.append({"key": key, "fields": fields})
        present.extend(
            item["name"]
            for item in fields
            if item["name"] in IDENTITY_PRESENT and not item["disabled"]
        )
    return sections, present


class _UserFormTransportMixin(_UserTransportMixin):
    """Form payload and the single refusal for operations owned by Comedores."""

    generic_view = None  # the Django view that follows the native forward hook

    def _owner_wanted(self, request):
        return bool(set(SECCIONES_COMEDORES) & set(secciones_habilitadas(request.user)))

    def _owner_response(self, request, response):
        """Owner JSON plus the portal's own frame, URLs and pending messages."""
        if response.status_code in (301, 302):
            # A redirect from the owner (login or permission flow) is never a saved result.
            return JsonResponse(
                {"detail": "No se pudo completar la operación.", "state": "rejected"},
                status=401,
            )
        data = owner_payload(response)
        if data is None:
            return JsonResponse(
                {"detail": "No se pudo completar la operación."},
                status=response.status_code if response.status_code >= 400 else 502,
            )
        if "sections" in data:
            data.update(
                {
                    "title": "Usuarios",
                    "submit_text": "Confirmar",
                    "urls": {"cancel": reverse("usuarios")},
                    "presentation": build_legacy_presentation(request),
                }
            )
            data["territorial"].update(
                {
                    "municipios_url": reverse("ajax_load_municipios"),
                    "localidades_url": reverse("ajax_load_localidades"),
                }
            )
            data["messages"] = pending_messages(request) + data["messages"]
        return JsonResponse(data, status=response.status_code)

    def get(self, request, *args, **kwargs):
        if self._owner_wanted(request):
            # The object is resolved first so the portal scope applies (404).
            if kwargs.get("pk") is not None:
                self.get_object()
            response = relay_to_owner(request, kwargs.get("pk"))
            if response.status_code < 500:
                return self._owner_response(request, response)
            messages.warning(request, UNAVAILABLE_WARNING)
        return self.generic_view.get(self, request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        body = request.body
        instance = self.get_object() if kwargs.get("pk") is not None else None
        if operacion_requiere_espacios(request.POST, instance):
            response = relay_to_owner(request, kwargs.get("pk"), body=body)
            if getattr(response, "owner_missing", False):
                return JsonResponse(REQUIRES_RUNTIME, status=409)
            return self._owner_response(request, response)
        return self.generic_view.post(self, request, *args, **kwargs)

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form), status=400)

    def render_to_response(self, context, **response_kwargs):
        form = context["form"]
        sections, present = project_form(form)
        editing = self.object is not None
        payload = {
            "mode": "edit" if editing else "create",
            "title": "Usuarios",
            "object": (
                {"id": self.object.pk, "username": self.object.username}
                if editing
                else None
            ),
            "sections": sections,
            "identity_present": present,
            "errors": form.errors.get_json_data() if form.is_bound else {},
            "comedores": {
                "sections": sorted(
                    set(SECCIONES_COMEDORES) & set(form.secciones_habilitadas)
                ),
                "runtime_required": True,
            },
            "territorial": {
                "initial": form.initial_territorial_scopes,
                "municipios_url": reverse("ajax_load_municipios"),
                "localidades_url": reverse("ajax_load_localidades"),
            },
            "urls": {"cancel": reverse("usuarios")},
            "submit_text": "Confirmar",
            "credential": None,
            "messages": pending_messages(self.request),
            "presentation": build_legacy_presentation(self.request),
        }
        if editing and context.get("temporary_password_visible"):
            payload["credential"] = {
                "temporary_password": context["temporary_password_plaintext"]
            }
        return JsonResponse(payload, status=response_kwargs.get("status", 200))


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class WebUserCreateView(_UserFormTransportMixin, UserCreateView):
    """Native create: ``auth.add_user`` and the actor's own section rules."""

    generic_view = CreateView


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class WebUserUpdateView(_UserFormTransportMixin, UserUpdateView):
    """Native edit inside the actor scope (404 outside it)."""

    generic_view = UpdateView
