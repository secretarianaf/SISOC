from django.apps import AppConfig


class DashboardConfig(AppConfig):
    name = "dashboard"

    def ready(self):
        from core.services.fixture_post_load import (  # pylint: disable=import-outside-toplevel
            registrar_fixture_post_load_handler,
        )
        from core.services.sidebar_items import (  # pylint: disable=import-outside-toplevel
            registrar_proveedor_tableros,
        )
        from dashboard.templatetags.dashboard_tags import (  # pylint: disable=import-outside-toplevel
            tableros_para_sidebar,
        )
        from dashboard.services.catalogo import (  # pylint: disable=import-outside-toplevel
            sincronizar_catalogo_post_fixture,
        )

        registrar_proveedor_tableros(tableros_para_sidebar)
        registrar_fixture_post_load_handler(
            "dashboard.catalogo", sincronizar_catalogo_post_fixture
        )
