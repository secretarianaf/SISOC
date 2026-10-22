from django.apps import AppConfig


class DashboardConfig(AppConfig):
    name = "dashboard"

    def ready(self):
        from core.services.sidebar_items import (  # pylint: disable=import-outside-toplevel
            registrar_proveedor_tableros,
        )
        from dashboard.templatetags.dashboard_tags import (  # pylint: disable=import-outside-toplevel
            tableros_para_sidebar,
        )

        registrar_proveedor_tableros(tableros_para_sidebar)
