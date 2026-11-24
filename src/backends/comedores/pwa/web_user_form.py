"""JSON projection of the composite user form for the portal's React screen.

The owner views (``pwa.user_admin_views``), the composite forms
(``pwa.user_forms``), their section restrictions, delegation checks and atomic
save stay the only owners of validation and persistence: this module runs them
and projects the bound form. It answers the same authorization (``AdminRequired``
permissions, in-scope object) as the HTML operation; the core relays the
request after its own web-access checks and adds the presentation.

Credential rule (U-CR1): the generated password never travels in a flash
message. The operation that creates it receives it once in a private
``credential`` result; later reads only expose what the native edit page shows.
"""

import json

from django import forms
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.utils.cache import patch_cache_control, patch_vary_headers

from users.secciones_usuario import SECCIONES_COMEDORES
from pwa.user_admin_views import UserCreateView, UserUpdateView

_LEVELS = {
    messages.ERROR: "error",
    messages.WARNING: "warning",
    messages.SUCCESS: "success",
}
USERS_URL = "/usuarios/"
# Fields of each native card, in template order; the flag gates the card.
SECTIONS = (
    ("personal", None, ("first_name", "last_name", "dni", "cuil", "tipo_usuario")),
    ("access", None, ("username", "email", "password")),
    (
        "mobile",
        "can_manage_mobile_access",
        (
            "es_representante_pwa",
            "es_coordinador_equipo_tecnico_pwa",
            "duplas_coordinador_pwa",
            "comedores_adicionales_coordinador_pwa",
            "puede_gestionar_rendiciones_mobile",
            "puede_gestionar_colaboradores_pwa",
            "puede_gestionar_usuarios_pwa",
            "puede_gestionar_nomina_pwa",
            "puede_gestionar_prestaciones_mensuales_pwa",
            "tipo_asociacion_pwa",
            "organizaciones_pwa",
            "comedores_pwa",
        ),
    ),
    (
        "territorial_comedor",
        "can_manage_territorial_comedor",
        ("es_territorial_comedor", "provincias_territorial"),
    ),
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
        "teams",
        "can_manage_technical_teams",
        ("es_coordinador", "duplas_asignadas"),
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


def _choices(bound):
    """Options as the widget renders them, with the ``data-*`` the native script reads."""
    rendered = []
    for group in bound.field.widget.optgroups(bound.name, [], {}):
        for option in group[1]:
            attrs = option.get("attrs", {})
            item = {"value": str(option["value"]), "label": str(option["label"])}
            if "data-organizacion-id" in attrs:
                item["organizacion_id"] = attrs["data-organizacion-id"]
                item["organizacion_nombre"] = attrs.get("data-organizacion-nombre", "")
            rendered.append(item)
    return rendered


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
        spec["choices"] = _choices(bound)
    return spec


def project_form(form):
    """Fields exactly as the native cards render them, with their bound value."""
    sections = []
    present = []
    for key, flag, names in SECTIONS:
        if flag is not None and not getattr(form, flag, False):
            continue
        fields = [_spec(form, name) for name in names if name in form.fields]
        sections.append({"key": key, "fields": fields})
        present.extend(
            item["name"]
            for item in fields
            if item["name"] in IDENTITY_PRESENT and not item["disabled"]
        )
    return sections, present


def pending_messages(request):
    return [
        {"message": str(message), "level": _LEVELS.get(message.level, "info")}
        for message in messages.get_messages(request)
    ]


def _operator(context):
    operator = context.get("pwa_operator_context")
    if not operator:
        return None
    return {
        "created_by": (
            operator["created_by"].username if operator["created_by"] else ""
        ),
        "accesses": [
            {
                "space": access.comedor.nombre,
                "created_by": (access.creado_por.username if access.creado_por else ""),
            }
            for access in operator["accesses"]
        ],
        "permission_labels": list(operator["permission_labels"]),
    }


def _created_users(context):
    return [
        {
            "username": item["user"].username,
            "email": item["user"].email or "",
            "active": bool(item["activo"]),
            "spaces": [comedor.nombre for comedor in item["comedores"]],
            "permission_labels": list(item["permission_labels"]),
        }
        for item in context.get("pwa_created_users", [])
    ]


class _WebFormMixin:
    """Same view, JSON out; the credential of a creation never rides a message."""

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form), status=400)

    def render_to_response(self, context, **response_kwargs):
        form = context["form"]
        sections, present = project_form(form)
        editing = self.object is not None
        payload = {
            "mode": "edit" if editing else "create",
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
                "runtime_required": False,
                "operator": _operator(context),
                "created_users": (
                    _created_users(context) if form.can_manage_mobile_access else []
                ),
            },
            "territorial": {"initial": form.initial_territorial_scopes},
            "credential": None,
            "messages": pending_messages(self.request),
        }
        if editing and context.get("temporary_password_visible"):
            payload["credential"] = {
                "temporary_password": context["temporary_password_plaintext"]
            }
        return JsonResponse(payload, status=response_kwargs.get("status", 200))


class WebUserCreateView(_WebFormMixin, UserCreateView):
    """Composite create; the redirect is data, the secret is a private result."""

    def form_valid(self, form):
        self.object = form.save()
        secret = getattr(form, "generated_password", None)
        if secret:
            messages.success(self.request, "Usuario mobile creado correctamente.")
            credential = {"temporary_password": secret}
            redirect = f"{USERS_URL}editar/{self.object.pk}/"
        else:
            messages.success(self.request, "Usuario creado correctamente.")
            credential, redirect = None, USERS_URL
        return JsonResponse(
            {"ok": True, "redirect": redirect, "credential": credential}
        )


class WebUserUpdateView(_WebFormMixin, UserUpdateView):
    """Composite edit inside the actor scope."""

    def form_valid(self, form):
        super().form_valid(form)
        return JsonResponse({"ok": True, "redirect": USERS_URL, "credential": None})


def operacion_usuario_web(request, data):
    """One transaction and one owner for the whole composite operation, as JSON."""
    user_id = data.get("user_id")
    view = WebUserUpdateView if user_id is not None else WebUserCreateView
    kwargs = {"pk": user_id} if user_id is not None else {}
    with transaction.atomic():
        response = view.as_view()(request, **kwargs)
    if response.status_code in (301, 302):
        location = response["Location"]
        if location.startswith(USERS_URL):
            response = JsonResponse({"ok": True, "redirect": location})
        else:
            # The permission check redirects to the login: that is a rejection, never a save.
            response = JsonResponse(
                {
                    "detail": "Debe iniciar sesión para realizar esta operación.",
                    "state": "unauthenticated",
                },
                status=401,
            )
    patch_cache_control(response, private=True, no_store=True)
    patch_vary_headers(response, ("Cookie",))
    return response


def operacion_usuario_web_http(request):
    """The owner validates session, CSRF, permissions and object scope again."""
    from django.http import (
        HttpResponseBadRequest,
    )  # pylint: disable=import-outside-toplevel

    raw_id = request.GET.get("user_id")
    try:
        user_id = int(raw_id) if raw_id is not None else None
    except (ValueError, TypeError):
        return HttpResponseBadRequest(json.dumps({"detail": "Usuario inválido."}))
    return operacion_usuario_web(request, {"user_id": user_id})
