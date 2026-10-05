from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from config.urls_dev import dev_urlpatterns
from core.backend_proxy import backend_proxy_urlpatterns
from core.legacy_redirects import redirecciones_legacy
from core.url_registry import stub_urlpatterns
from core.v2_frontend import frontend_v2
from usuarios.views import (
    PasswordResetConfirmCustomView,
    SisocPasswordResetCompleteView,
    SisocPasswordResetDoneView,
    SisocPasswordResetView,
    UsuariosLoginView,
)

urlpatterns = [
    # Verticales que corren en su propio backend (src/backends/config/backends.json).
    *backend_proxy_urlpatterns(),
    # SOLO compatibilidad: URLs de Centro de Familia anteriores a su prefijo
    # propio. El código nuevo usa {% url %}/reverse() (ver core.legacy_redirects).
    *redirecciones_legacy(
        "centrodefamilia/",
        [
            "centros/",
            "actividades/",
            "ajax/actividades/",
            "informecabal/",
            "beneficiarios/",
        ],
    ),
    re_path(
        r"^v2/(?P<module>[a-z0-9_-]+)(?:/(?P<asset_path>.*))?$",
        frontend_v2,
        name="frontend_v2",
    ),
    path("login/", UsuariosLoginView.as_view(), name="login"),
    path("password_reset/", SisocPasswordResetView.as_view(), name="password_reset"),
    path(
        "password_reset/done/",
        SisocPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        PasswordResetConfirmCustomView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        SisocPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path("admin/doc/", include("django.contrib.admindocs.urls")),
    path("admin/", admin.site.urls),
    path("", include("usuarios.urls")),
    path("", include("django.contrib.auth.urls")),
    path("", include("core.urls")),
    path("", include("dashboard.urls")),
    path("", include("comedores.urls")),
    path("", include("gestion_organizaciones.urls")),
    path("", include("duplas.urls")),
    path("", include("audittrail.urls")),
    path("", include("ciudadanos.urls")),
    path("", include("admisiones.urls")),
    path("", include("healthcheck.urls")),
    path("acompanamientos/", include("acompanamientos.urls")),
    path("expedientespagos/", include("expedientespagos.urls")),
    path("", include("rendicioncuentasfinal.urls")),
    path("", include("relevamientos.urls")),
    path("", include("insumos.urls")),
    path("rendicioncuentasmensual/", include("rendicioncuentasmensual.urls")),
    # API URLs
    path("api/users/", include("usuarios.api_urls")),
    path("api/comedores/", include("comedores.api_urls")),
    path("api/territorial/", include("comedores.api_urls_territorial")),
    path("api/comunicados/", include("comunicados.api_urls")),
    path("api/renaper/", include("core.api_urls")),
    path("api/pwa/", include("pwa.api_urls")),
    path("", include("importarexpediente.urls")),
    path("", include("comunicados.urls")),
    path("ocr/", include("ocr.urls")),
    path("", include("encuestas.urls")),
]

urlpatterns += dev_urlpatterns()

if getattr(settings, "ENABLE_API_DOCS", False):
    urlpatterns += [
        # Swagger/OpenAPI
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/docs/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
        path(
            "api/redoc/",
            SpectacularRedocView.as_view(url_name="schema"),
            name="redoc",
        ),
    ]

# Patrones propios del core. Los nombres de los backends se agregan como stubs
# solo-reverse (core/url_registry.py); src/backends/config/urls_all.py usa los propios.
core_urlpatterns = urlpatterns
urlpatterns = core_urlpatterns + stub_urlpatterns(core_urlpatterns)

handler404 = "config.views.page_not_found"
handler500 = "config.views.server_error"
