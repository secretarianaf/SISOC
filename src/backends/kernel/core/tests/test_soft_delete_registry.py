from django.conf import settings
from django.test import override_settings

from core.soft_delete.registry import (
    get_soft_delete_model_choices,
    iter_soft_delete_models,
)


def _core_only_apps():
    # Deployed core process: backend apps live in their own services
    # (config/backends.json), so they are not installed here.
    return settings.SHARED_APPS + settings.KERNEL_APPS + settings.CORE_APPS


def test_iter_soft_delete_models_skips_apps_not_installed():
    with override_settings(INSTALLED_APPS=_core_only_apps()):
        labels = {model._meta.app_label for model in iter_soft_delete_models()}
        choices = get_soft_delete_model_choices()

    assert "admisiones" not in labels
    assert "comedores" not in labels
    assert {"ciudadanos", "organizaciones"} <= labels
    assert choices


def test_iter_soft_delete_models_keeps_all_models_when_every_app_is_installed():
    labels = {model._meta.app_label for model in iter_soft_delete_models()}

    assert {"admisiones", "comedores", "ciudadanos", "celiaquia"} <= labels
