from django.apps import AppConfig


class GestionOrganizacionesConfig(AppConfig):
    """Gestión de organizaciones del SISOC core.

    Pantallas, formularios, exportaciones y firmantes (ligados a programas de
    comedores). Los datos maestros de organizaciones, que comparten todos los
    servicios, viven en ``src/backends/kernel/organizaciones``.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "gestion_organizaciones"

    def ready(self):
        import gestion_organizaciones.audit_signals  # noqa: F401  pylint: disable=import-outside-toplevel,unused-import
