"""Keep admindocs metadata from replacing the new session-only web APIs."""

import re

from django.contrib.admindocs.middleware import XViewMiddleware


_OWNED_PATTERNS = (
    r"/api/web/insumos/(?:categorias/)?[0-9]+/(?:editar|eliminar)/",
    r"/api/web/groups/[0-9]+/edit/",
    r"/api/web/surveys/[0-9]+/(?:answer|postpone|dismiss)/",
    r"/api/web/password/reset/[^/]+/",
    r"/api/web/users/import/jobs/[0-9]+/(?:resume/)?",
    r"/api/web/users/bulk-credentials/jobs/[0-9]+/(?:resume/)?",
    r"/api/web/inspecciones/(?:actas|inspectores)/",
    r"/api/web/inspecciones/actas/[^/]+/(?:anular/|prueba/)?",
    r"/api/web/inspecciones/(?:localidades/|escuelas/(?:nueva/|[0-9]+/editar/)?)",
    r"/api/web/cdi/(?:reportes/|centros/[0-9]+/observaciones/crear/"
    r"|observaciones/[0-9]+/(?:editar/|eliminar/)?)",
    r"/api/web/comedores/duplas/(?:crear/|[0-9]+/(?:(?:editar|eliminar)/)?)?",
    r"/api/web/comedores/montos/(?:crear/|[0-9]+/(?:editar/|eliminar/)?)?",
    r"/api/web/comedores/actividades-pnud/(?:crear/|[0-9]+/(?:editar|baja)/)?",
    r"/api/web/pas/(?:areas/(?:formacion|mesa-ayuda|liquidacion)/|formacion/personas/"
    r"|personas/(?:[0-9]+/cambiar-estado/)?|panel/(?:[0-9]+/)?)",
    r"/api/web/cdf/centros/(?:[0-9]+/(?:usuarios/)?)?",
    r"/api/web/cdf/centros/(?:options/|crear/|[0-9]+/(?:editar|eliminar)/)",
    r"/api/web/cdf/centros/[0-9]+/generar-usuario/",
    r"/api/web/cdf/(?:beneficiarios/(?:preinscripcion/(?:options/)?|buscar-cuil/"
    r"|buscar-responsable/|exportar/disponible/|[0-9]+/)?|responsables/(?:[0-9]+/)?)",
    r"/api/web/comedores/admisiones/plantillas-informe/"
    r"(?:variables/|incidencias/(?:[0-9]+/)?|[0-9]+/)?",
    r"/api/web/comedores/acompanamientos/(?:[0-9]+/(?:hitos/restaurar/)?)?",
    r"/api/web/comedores/expedientespagos/(?:comedores/[0-9]+/(?:crear/)?|[0-9]+/(?:editar/|eliminar/)?)",
    r"/api/web/dispositivos/(?:listado/|options/|mapa/|[0-9]+/(?:ubicacion/)?)",
)


class WebSessionXViewMiddleware(XViewMiddleware):
    """Preserve upstream behavior outside the explicitly owned new API paths."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method == "HEAD" and (
            request.path_info
            in {
                "/api/web/session/",
                "/api/web/login/",
                "/api/web/surveys/pending/",
                "/api/web/groups/",
                "/api/web/groups/create/",
                "/api/web/account/",
                "/api/web/account/confirm/",
                "/api/web/password/first-change/",
                "/api/web/password/change/",
                "/api/web/password/reset/",
                "/api/web/users/import/",
                "/api/web/users/bulk-credentials/",
                "/api/web/insumos/",
                "/api/web/insumos/options/",
                "/api/web/insumos/crear/",
                "/api/web/insumos/categorias/",
                "/api/web/insumos/categorias/crear/",
            }
            or any(
                re.fullmatch(pattern, request.path_info) for pattern in _OWNED_PATTERNS
            )
        ):
            return None
        return super().process_view(request, view_func, view_args, view_kwargs)
