"""Canonical React entry for Expediente alta (``nuevo``) and edición (``editar``).

Both the JSON projection and the JSON submit drive the native class-based
views themselves (``setup``, ``get_object``, ``get_form``, ``form_valid``), so
validation, object lookup, service calls and success URLs stay identical to the
HTML form. Non-JSON requests keep reaching the native view unchanged.
"""

from django.http import JsonResponse
from django.urls import reverse

from celiaquia.canonical_shell import canonical_screen
from celiaquia.views.expediente import ExpedienteCreateView, ExpedienteUpdateView

# Mirrors celiaquia.forms.validate_file_size and the preview cap in
# views.expediente._parse_limit; the server remains authoritative.
EXCEL_MAX_BYTES = 5 * 1024 * 1024
PREVIEW_MAX_LIMIT = 5000


def _native(view_class, request, *args, **kwargs):
    """Return a native view instance bound to ``request`` and its object."""
    view = view_class()
    view.setup(request, *args, **kwargs)
    # Same lookup as the native ProcessFormView (Http404 when missing).
    view.object = view.get_object() if view_class is ExpedienteUpdateView else None
    return view


def _excel_current(bound_field):
    value = bound_field.value()
    if not value or not getattr(value, "url", None):
        return None
    # Same link ClearableFileInput renders in the native template.
    return {"name": value.name, "url": value.url}


def _projection(view_class, mode, title):
    def projection(request, *args, **kwargs):
        view = _native(view_class, request, *args, **kwargs)
        form = view.get_form()
        context = view.get_context_data(form=form)
        numero = form["numero_expediente"]
        observaciones = form["observaciones"]
        excel = form["excel_masivo"]
        expediente = view.object
        return JsonResponse(
            {
                "version": 1,
                "mode": mode,
                "title": title,
                "expediente": (
                    {"id": expediente.pk, "numero": expediente.numero_expediente or ""}
                    if expediente
                    else None
                ),
                "fields": {
                    "numero_expediente": {
                        "label": str(numero.label),
                        "required": numero.field.required,
                        "max_length": numero.field.max_length,
                        "value": numero.value() or "",
                    },
                    "observaciones": {
                        "label": str(observaciones.label),
                        "required": observaciones.field.required,
                        "value": observaciones.value() or "",
                    },
                    "excel_masivo": {
                        "label": str(excel.label),
                        "required": excel.field.required,
                        "accept": excel.field.widget.attrs.get("accept", ".xlsx"),
                        "max_bytes": EXCEL_MAX_BYTES,
                        "current": _excel_current(excel),
                    },
                },
                "urls": {
                    "preview": reverse("expediente_preview_excel"),
                    "plantilla": reverse("expediente_plantilla_excel"),
                    "localidades": reverse("expediente_localidades_lookup"),
                    "cancel": reverse("expediente_list"),
                },
                "preview_max_limit": PREVIEW_MAX_LIMIT,
                # The native edit template has no ``provincias`` in context.
                "provincias": [
                    {"id": p.pk, "nombre": p.nombre}
                    for p in context.get("provincias", [])
                ],
            }
        )

    return projection


def _errors(form):
    return {
        field: [error["message"] for error in errors]
        for field, errors in form.errors.get_json_data().items()
    }


def _submit(view_class):
    def submit(request, *args, **kwargs):
        view = _native(view_class, request, *args, **kwargs)
        form = view.get_form()
        if not form.is_valid():
            return JsonResponse({"ok": False, "errors": _errors(form)}, status=400)
        response = view.form_valid(form)
        return JsonResponse({"ok": True, "redirect": response["Location"]})

    return submit


expediente_nuevo = canonical_screen(
    ExpedienteCreateView.as_view(),
    "expediente-nuevo",
    _projection(ExpedienteCreateView, "create", "Crear Expediente"),
    _submit(ExpedienteCreateView),
)
expediente_editar = canonical_screen(
    ExpedienteUpdateView.as_view(),
    "expediente-editar",
    _projection(ExpedienteUpdateView, "edit", "Editar Expediente"),
    _submit(ExpedienteUpdateView),
)
