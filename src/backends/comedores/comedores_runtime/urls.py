"""URLs de Comedores; el admin real se monta solamente en su runtime."""

from django.contrib import admin
from django.urls import include, path

from config.backend_urls import urlpatterns_de_backend

backend_urlpatterns = [
    path("", include("comedores.urls")),
    path("", include("gestion_organizaciones.urls")),
    path("", include("duplas.urls")),
    path("", include("admisiones.urls")),
    path("acompanamientos/", include("acompanamientos.urls")),
    path("expedientespagos/", include("expedientespagos.urls")),
    path("", include("rendicioncuentasfinal.urls")),
    path("", include("relevamientos.urls")),
    path("rendicioncuentasmensual/", include("rendicioncuentasmensual.urls")),
    path("interno/usuarios/", include("pwa.user_admin_urls")),
    path("interno/espacios/", include("pwa.identity_urls")),
    path("api/comedores/", include("comedores.api_urls")),
    path("api/territorial/", include("comedores.api_urls_territorial")),
    path("api/comunicados/", include("comunicados.api_urls")),
    path("api/pwa/", include("pwa.api_urls")),
    path("", include("importarexpediente.urls")),
    path("", include("comunicados.urls")),
]

# settings_all ya monta el admin completo desde config.urls. Evitar duplicar
# su namespace al componer las rutas, sin sustituir ModelAdmins por stubs.
urlpatterns = urlpatterns_de_backend(
    [*backend_urlpatterns, path("admin/", admin.site.urls)]
)

handler404 = "config.views.page_not_found"
handler500 = "config.views.server_error"
