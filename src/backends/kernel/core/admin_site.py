"""Sitio del Django admin de SISOC (issue #2789).

El admin es la herramienta de autoservicio de desarrollo y soporte: solo entran
superusuarios que además sean staff. Ser ``is_staff`` ya no alcanza. Se
instala como sitio por defecto con ``core.admin_apps.SisocAdminConfig``
(mecanismo oficial de Django para reemplazar ``admin.site``), así cada runtime
usa el mismo sitio.
"""

from django.contrib.admindocs import urls as admindocs_urls
from django.contrib.auth.decorators import user_passes_test
from django.urls import URLPattern, reverse_lazy
from unfold.sites import UnfoldAdminSite

from core.admin_dashboard import secciones_de_app


def puede_usar_admin(user) -> bool:
    """Única regla de acceso al admin, a ``admin/doc/`` y a sus accesos.

    Se conserva ``is_staff`` (lo exige el login del admin de Django) y se suma
    ``is_superuser``: la regla queda más estricta que la anterior, nunca más amplia.
    """
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and user.is_staff
        and user.is_superuser
    )


class SisocAdminSite(UnfoldAdminSite):
    """Admin con Unfold restringido a superusuarios activos."""

    site_header = "SISOC"
    site_title = "SISOC admin"
    index_title = "Panel de administración"

    def has_permission(self, request):
        return puede_usar_admin(request.user)

    def app_index(self, request, app_label, extra_context=None):
        # Cada vertical muestra sus métricas en su índice (/admin/<app>/), que
        # sirve su propio runtime (#2789, Fase 3).
        extra_context = {
            **(extra_context or {}),
            "sisoc_secciones": secciones_de_app(app_label),
        }
        return super().app_index(request, app_label, extra_context)


def admindocs_urlpatterns() -> list[URLPattern]:
    """URLs de ``django.contrib.admindocs`` con la misma regla que el admin.

    Las vistas de admindocs solo piden ``staff_member_required``; se envuelven
    sin copiar sus vistas para que un staff sin superusuario vuelva al login.
    """
    requiere_superusuario = user_passes_test(
        puede_usar_admin, login_url=reverse_lazy("admin:login")
    )
    return [
        URLPattern(
            patron.pattern,
            requiere_superusuario(patron.callback),
            patron.default_args,
            patron.name,
        )
        for patron in admindocs_urls.urlpatterns
    ]
