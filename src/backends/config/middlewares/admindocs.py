"""Keep admindocs metadata from replacing the new session-only web APIs."""

import re

from django.contrib.admindocs.middleware import XViewMiddleware

_OWNED_PATTERNS = (
    r"/api/web/vat/catalogos/(?:sectores|subsectores|modalidades-cursado|titulos-referencia)/"
    r"(?:nuevo/|nueva/|[0-9]+/(?:editar/|eliminar/)?)?",
    r"/api/web/insumos/(?:categorias/)?[0-9]+/(?:editar|eliminar)/",
    r"/api/web/groups/[0-9]+/edit/",
    r"/api/web/dashboard/(?:centro-de-familia/|[-a-zA-Z0-9_]+/)",
    r"/api/web/encuestas/(?:lista/|importar/|crear/|rondas/[0-9]+/cerrar/"
    r"|[0-9]+/(?:resultados/|publicar/|editar/|revision/|aprobar/|rechazar/|segmentacion/(?:(?:tipo|agregar)/|[0-9]+/quitar/)?))",
    r"/api/web/users/[0-9]+/(?:deactivate|activate|edit)/",
    r"/api/web/surveys/[0-9]+/(?:answer|postpone|dismiss)/",
    r"/api/web/password/reset/[^/]+/",
    r"/api/web/users/import/jobs/[0-9]+/(?:resume/)?",
    r"/api/web/users/bulk-credentials/jobs/[0-9]+/(?:resume/)?",
    r"/api/web/inspecciones/(?:actas|inspectores)/",
    r"/api/web/inspecciones/actas/[^/]+/(?:anular/|prueba/)?",
    r"/api/web/inspecciones/(?:localidades/|escuelas/(?:nueva/|[0-9]+/editar/)?)",
    r"/api/web/inspecciones/(?:escuelas/buscar/|asignaciones/(?:nueva/|verificar/|[0-9]+/quitar/)?)",
    r"/api/web/inspecciones/tablero/(?:datos/|exportar\.csv|descargar-actas/)?",
    r"/api/web/cdi/(?:reportes/|centros/[0-9]+/observaciones/crear/"
    r"|observaciones/[0-9]+/(?:editar/|eliminar/)?"
    r"|intervenciones/[0-9]+/(?:documentacion/(?:eliminar/)?)?)",
    r"/api/web/cdi/centros/(?:[0-9]+/(?:nomina/(?:[0-9]+/)?"
    r"|usuarios/[0-9]+/estado/|trabajadores/[0-9]+/eliminar/)?)?",
    r"/api/web/cdi/nomina/[0-9]+/derivar/",
    r"/api/web/cdi/nomina/[0-9]+/formulario/",
    r"/api/web/cdi/centros/[0-9]+/nomina/asistencia/",
    r"/api/web/cdi/centros/[0-9]+/intervenciones/(?:crear/|[0-9]+/editar/)",
    r"/api/web/cdi/centros/[0-9]+/trabajadores/(?:crear/|[0-9]+/(?:editar/)?)",
    r"/api/web/cdi/centros/[0-9]+/nomina/(?:crear/|[0-9]+/editar/)",
    r"/api/web/cdi/centros/[0-9]+/formularios/(?:crear/|[0-9]+/(?:editar/)?)?",
    r"/api/web/cdi/centros/[0-9]+/calidad/(?:cargar/|[0-9]+/)?",
    r"/api/web/cdi/centros/(?:crear/|[0-9]+/editar/)",
    r"/api/web/cdi/(?:centros/[0-9]+/usuarios/generar/|renaper/[a-z0-9_]+/)",
    r"/api/web/cdi/centros/[0-9]+/nomina/(?:crear/|[0-9]+/editar/)",
    r"/api/web/cdi/centros/(?:[0-9]+/nomina/[0-9]+/(?:(?:publicar|archivar|destacado|eliminar)/)?)?",
    r"/api/web/comedores/duplas/(?:crear/|[0-9]+/(?:(?:editar|eliminar)/)?)?",
    r"/api/web/comedores/asignar-dupla/[0-9]+/",
    r"/api/web/comedores/nomina-crear/[0-9]+/(?:admision/[0-9]+/)?",
    r"/api/web/comedores/montos/(?:crear/|[0-9]+/(?:editar/|eliminar/)?)?",
    r"/api/web/comedores/actividades-pnud/(?:crear/|[0-9]+/(?:editar|baja)/)?",
    r"/api/web/comedores/colaboradores/comedor/[0-9]+/(?:crear/|[0-9]+/(?:editar|eliminar)/)",
    r"/api/web/comedores/actividades-espacio/comedor/[0-9]+/(?:crear/|[0-9]+/editar/)",
    r"/api/web/comedores/cursos-app-mobile/(?:crear/|[0-9]+/(?:editar|eliminar)/)?",
    r"/api/web/pas/(?:areas/(?:formacion|mesa-ayuda|liquidacion)/|formacion/personas/"
    r"|personas/(?:[0-9]+/cambiar-estado/)?|panel/(?:[0-9]+/)?)",
    r"/api/web/pas/cruces/(?:exportar-sintys/|importar-sintys/|actualizar-renaper/)?",
    r"/api/web/pas/informes/(?:[0-9]+/|opciones/|previsualizar/|generar/)?",
    r"/api/web/pas/titulares/importar/",
    r"/api/web/pas/personas/(?:opciones/|crear/|[0-9]+/(?:editar/)?)",
    r"/api/web/cdf/centros/(?:[0-9]+/(?:usuarios/)?)?",
    r"/api/web/cdf/centros/(?:options/|crear/|[0-9]+/(?:editar|eliminar)/)",
    r"/api/web/cdf/centros/[0-9]+/generar-usuario/",
    r"/api/web/cdf/informecabal/(?:registro/[0-9]+/|[0-9]+/)?",
    r"/api/web/cdf/centros/[0-9]+/informecabal/[0-9]+/",
    r"/api/web/dispositivos/(?:crear/|[0-9]+/editar/)",
    r"/api/web/cdf/actividades/(?:nueva/|[0-9]+/(?:asistencia/|editar/)?)?",
    r"/api/web/cdf/centros/[0-9]+/actividades/nueva/",
    r"/api/web/cdf/centros/[0-9]+/actividades/[0-9]+/"
    r"(?:participantes/(?:[0-9]+/eliminar/)?|lista-espera/[0-9]+/promover/)",
    r"/api/web/cdf/(?:beneficiarios/(?:preinscripcion/(?:options/)?|buscar-cuil/"
    r"|buscar-responsable/|exportar/disponible/|[0-9]+/)?|responsables/(?:[0-9]+/)?)",
    r"/api/web/comedores/admisiones/plantillas-informe/"
    r"(?:variables/|incidencias/(?:[0-9]+/)?|[0-9]+/(?:(?:publicar|archivar|destacado|eliminar)/)?)?",
    r"/api/web/comedores/admisiones/informes/[a-z]+/(?:admision/)?[0-9]+/(?:formulario/|guardar/)?",
    r"/api/web/comedores/admisiones/informes/(?:complementario/)?[a-z]+/[0-9]+/(?:docx-editado/|revision/)?",
    r"/api/web/comedores/admisiones/[0-9]+/documentacion/(?:[0-9]+/(?:subir|eliminar)/|personalizada/agregar/)",
    r"/api/web/comedores/admisiones/(?:tecnicos/|legales/|[0-9]+/[0-9]+/detalle/"
    r"|[0-9]+/(?:acciones/[a-z-]+/)?"
    r"|legales/[0-9]+/(?:acciones/[a-z-]+/|complementario/revision/)?)",
    r"/api/web/comedores/acompanamientos/(?:[0-9]+/(?:hitos/restaurar/)?)?",
    r"/api/web/comedores/expedientespagos/(?:comedores/[0-9]+/(?:crear/)?|[0-9]+/(?:editar/|eliminar/)?)",
    r"/api/web/comedores/comunicados/mailing/(?:jobs/[0-9]+/(?:resume/)?)?",
    r"/api/web/comedores/importarexpedientes/(?:subir/|[0-9]+/(?:importar/|borrar-datos/|fechas-acreditacion/)?)?",
    r"/api/web/dispositivos/(?:listado/|options/|mapa/|[0-9]+/(?:ubicacion/)?)",
    r"/api/web/comedores/rendicioncuentasmensual/listado/",
    r"/api/web/comedores/rendicioncuentasmensual/por-comedor/[0-9]+/",
    r"/api/web/comedores/rendicioncuentasmensual/[0-9]+/",
    r"/api/web/comedores/rendicioncuentasmensual/(?:nuevo|editar|eliminar)/[0-9]+/",
    r"/api/web/comedores/rendicioncuentasmensual/auditoria/(?:[0-9]+/)?",
    r"/api/web/comedores/rendicion_cuentas_final/(?:comedor/[0-9]+/|documentos/(?:adjuntar/|[0-9]+/(?:validar|subsanar|eliminar)/)?"
    r"|[0-9]+/(?:crear|fisicamente_presentada)/)",
    r"/api/web/dispositivos/datacalle/(?:opciones/(?:dispositivos|relevadores)/|relevamientos/"
    r"(?:formulario/|crear/|[0-9a-f-]{36}/(?:formulario/|editar/|cerrar/|eliminar/)?)?)",
    r"/api/web/comedores/observaciones/(?:comedor/[0-9]+/crear/|[0-9]+/(?:editar/|eliminar/)?)",
    r"/api/web/comedores/intervenciones/(?:comedor/[0-9]+/(?:crear/|baja/[0-9]+/)?|subestados/"
    r"|[0-9]+/(?:documentacion/eliminar/|editar/[0-9]+/)?)",
    r"/api/web/comedores/comunicados/(?:gestion/|crear/|destinatarios/[^/]+/(?:buscar|todos)/"
    r"|[0-9]+/(?:(?:publicar|archivar|destacado|eliminar|editar)/)?)?",
    r"/api/web/comedores/relevamientos/[0-9]+/(?:relevamiento/(?:numero-if/|[0-9]+/(?:(?:eliminar|revision)/|seguimientos/(?:(?:[0-9]+|primero)/(?:(?:editar|eliminar|revision)/)?)?)?)|pnud/[0-9]+/(?:revision/)?|actas/(?:crear/|[0-9]+/(?:(?:editar|revision|eliminar)/)?))?",
    r"/api/web/dispositivos/datacalle/casos/[0-9a-f-]{36}/",
    r"/api/web/ocr/(?:carga/|lotes/(?:[0-9]+/)?)",
    r"/api/web/comedores/organizaciones/(?:listado/|formulario/|crear/|subtipos/|cuil/|[0-9]+/(?:formulario/|editar/|baja/)?)",
    r"/api/web/comedores/organizaciones/(?:proyectos/[0-9]+/convenio/"
    r"|[0-9]+/(?:documentacion/(?:[0-9]+/(?:historial/|subir/)|personalizada/)"
    r"|(?:firmantes|avales)/(?:formulario/)?|rendiciones/[0-9]+/)"
    r"|documentacion/[0-9]+/(?:estado/|vencimiento/|numero-gde/)"
    r"|(?:firmantes|avales)/[0-9]+/(?:formulario/|baja/)?)",
    r"/api/web/ciudadanos/[0-9]+/",
    r"/api/web/vat/(?:vouchers/(?:parametrias/|[0-9]+/)?|evaluaciones/(?:[0-9]+/)?)",
    r"/api/web/ciudadanos/[0-9]+/marcar-revisado/",
    r"/api/web/ciudadanos/[0-9]+/baja/",
    r"/api/web/ciudadanos/[0-9]+/familiares/nuevo/",
    r"/api/web/ciudadanos/(?:crear/|[0-9]+/editar/)",
    r"/api/web/ciudadanos/importacion-masiva/(?:lotes/[0-9]+/(?:reanudar/)?)?",
    r"/api/web/ciudadanos/(?:revision/|[0-9]+/descartar-revision/)",
    r"/api/web/ciudadanos/familiares/[0-9]+/eliminar/",
    r"/api/web/ciudadanos/listar/",
    r"/api/web/vat/(?:vouchers/(?:parametrias/(?:nueva/|[0-9]+/(?:asignar/|asignar-masivo/)?)?|asignar/|asignar-masivo/|[0-9]+/)?"
    r"|evaluaciones/(?:nueva/|[0-9]+/(?:editar/|eliminar/)?)?"
    r"|resultados-evaluacion/(?:nuevo/|[0-9]+/(?:editar/|eliminar/)?)?"
    r"|reportes/inscripciones-asistencias/)",
    r"/api/web/vat/(?:cursos/)?comisiones/sesiones/[0-9]+/asistencia/",
    r"/api/web/vat/comisiones-detalle/(?:[0-9]+/|cursos/[0-9]+/(?:resultados/|profesores/(?:buscar|nuevo)/)?)",
    r"/api/web/vat/comisiones-horarios/(?:cursos/)?(?:nuevo/|[0-9]+/(?:editar/|eliminar/))",
    r"/api/web/vat/comisiones-formularios/(?:cursos/)?(?:nueva/|[0-9]+/(?:editar/|eliminar/))",
    r"/api/web/vat/comisiones-asistente/cursos/[0-9]+/",
    r"/api/web/vat/(?:inscripciones-persona/(?:nueva/|rapida-comision/|[0-9]+/(?:editar/|eliminar/|cambiar-estado/)?"
    r"|cursos/(?:rapida-comision/|[0-9]+/cambiar-estado/|comisiones/[0-9]+/cambiar-estado-lote/))?"
    r"|buscador-ciudadano/)",
    r"/api/web/vat/inscripciones-oferta/(?:nueva/|[0-9]+/(?:editar/|eliminar/)?)?",
    r"/api/web/vat/modalidades-institucionales/(?:nueva/|[0-9]+/(?:editar/|eliminar/)?)?",
    r"/api/web/vat/institucion/contactos/(?:nuevo/|[0-9]+/(?:editar/|eliminar/)?)?",
    r"/api/web/vat/institucion/ubicaciones/(?:nuevo/|[0-9]+/(?:editar/|eliminar/)?)?",
    r"/api/web/vat/institucion/identificadores/(?:nuevo/|[0-9]+/(?:editar/|eliminar/)?)?",
    r"/api/web/vat/centros-usuarios/[0-9]+/generar/",
    r"/api/web/vat/centros-lista/(?:[0-9]+/eliminar/)?",
    r"/api/web/vat/ofertas-institucionales/(?:nueva/|[0-9]+/(?:editar/|eliminar/)?)?",
    r"/api/web/vat/cursos-(?:detalle/[0-9]+/|formularios/(?:nuevo/|[0-9]+/(?:editar/|eliminar/)))",
    r"/api/web/vat/centros-detalle/[0-9]+/(?:cursos/)?",
    r"/api/web/vat/centros-acciones/(?:contactos/[0-9]+/editar/|ubicaciones/[0-9]+/editar/|cursos/(?:nuevo/|[0-9]+/editar/))",
    r"/api/web/vat/centros-formulario/(?:nuevo/|[0-9]+/editar/)",
    r"/api/web/vat/catalogos/planes-curriculares/(?:nuevo/|[0-9]+/(?:editar/)?)?",
    r"/api/web/vat/comisiones-horarios/(?:[0-9]+/)?",
    r"/api/web/vat/comisiones-lista/",
    r"/api/web/auditoria/(?:listado/|evento/[0-9]+/|[a-z_]+/[a-z_]+/[^/]+/)",
    r"/api/web/auditoria/[a-z_]+/[a-z_]+/[^/]+/",
    r"/api/web/comedores/comedores/(?:formulario/|crear/|[0-9]+/(?:baja/|formulario/|editar/|admision/|capacitaciones/[0-9]+/estado/)?)?",
    r"/api/web/comedores/comedores/",
    r"/api/web/comedores/comedores/[0-9]+/(?:validacion|validar|convenio-pnud|responsable-tarjeta)/",
    r"/api/web/comedores/comedores/(?:[0-9]+/(?:admision/[0-9]+/)?nomina/|nomina/[0-9]+/(?:cambiar-estado|derivar)/)",
    r"/api/web/comedores/comedores/[0-9]+/admision/[0-9]+/nomina/asistencia/",
    r"/api/web/comedores/comedores/[0-9]+/certificaciones-prestaciones/",
    r"/api/web/comedores/comedores/[0-9]+/transacciones/",
    r"/api/web/(?:comedores|cdf|celiaquia|vat)/ciudadanos/[0-9]+/aportes/[a-z]+/",
    r"/api/web/core/(?:novedades/|arquitectura/|programas/(?:crear/|[0-9]+/(?:editar/|eliminar/)?)?"
    r"|papelera/(?:restaurar/[a-z_]+/[a-z_]+/[0-9]+/)?)",
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
                "/api/web/users/list/",
                "/api/web/users/create/",
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
