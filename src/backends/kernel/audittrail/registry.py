from auditlog.registry import auditlog

from audittrail.constants import get_tracked_model_definitions


def register_tracked_models():
    """
    Registra en django-auditlog los modelos de negocio críticos que se deben auditar.
    """
    for definition in get_tracked_model_definitions():
        # Cada proceso registra solo los modelos de sus apps; los de otros
        # backends los registra el backend dueño.
        if not definition.is_installed():
            continue
        model = definition.get_model()
        registry = getattr(auditlog, "_registry", {})
        try:
            already_registered = model in registry
        except TypeError:
            already_registered = False

        if already_registered:
            continue
        included_fields = getattr(definition, "included_fields", ())
        if included_fields:
            auditlog.register(model, include_fields=list(included_fields))
            continue
        auditlog.register(model, exclude_fields=definition.get_excluded_fields())
