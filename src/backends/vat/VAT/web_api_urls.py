"""Rutas same-origin del frontend INET bajo ``/api/web/vat/`` (G1 v1).

Ver ``docs/plans/2026-T4/2026-11-10-2785-vat-api-web-m2.md``.
"""

from django.urls import path
from ciudadanos.web_aportes import AporteCiudadanoWebView
from VAT import api_inet_views as views
from VAT.services.inet_forms import FORM_CLASSES
from VAT.services.inet_queries import RESOURCES
from VAT.web_api_inscripcion_oferta import (
    InscripcionOfertaCreateWebView,
    InscripcionOfertaDeleteWebView,
    InscripcionOfertaDetailWebView,
    InscripcionOfertaListWebView,
    InscripcionOfertaUpdateWebView,
)
from VAT.web_api_buscador_ciudadano import BuscadorCiudadanoWebView
from VAT.web_api_comision_horario_forms import (
    ComisionCursoHorarioCreateWebView,
    ComisionCursoHorarioDeleteWebView,
    ComisionCursoHorarioUpdateWebView,
    ComisionHorarioCreateWebView,
    ComisionHorarioDeleteWebView,
    ComisionHorarioUpdateWebView,
)
from VAT.web_api_comision_forms import (
    ComisionCreateWebView,
    ComisionCursoCreateWebView,
    ComisionCursoDeleteWebView,
    ComisionCursoUpdateWebView,
    ComisionDeleteWebView,
    ComisionUpdateWebView,
)
from VAT.web_api_comision_wizard import ComisionCursoAsistenteWebView
from VAT.web_api_oferta_curso_forms import (
    CursoCreateWebView,
    CursoDeleteWebView,
    CursoUpdateWebView,
    OfertaInstitucionalCreateWebView,
    OfertaInstitucionalDeleteWebView,
    OfertaInstitucionalUpdateWebView,
)
from VAT.web_api_oferta_curso import (
    CursoDetailWebView,
    OfertaInstitucionalDetailWebView,
    OfertaInstitucionalListWebView,
)
from VAT.web_api_comision_detalle import (
    ComisionCursoResultadosWebView,
    ComisionDetalleCursoWebView,
    ComisionDetalleOfertaWebView,
    ProfesorCentroBuscarWebView,
    ProfesorCentroCrearWebView,
)
from VAT.web_api_inscripcion_acciones import (
    InscripcionCambiarEstadoWebView,
    InscripcionCursoCambiarEstadoLoteWebView,
    InscripcionCursoCambiarEstadoWebView,
    InscripcionRapidaComisionCursoWebView,
    InscripcionRapidaComisionWebView,
)
from VAT.web_api_inscripcion_persona import (
    InscripcionCreateWebView,
    InscripcionDeleteWebView,
    InscripcionDetailWebView,
    InscripcionListWebView,
    InscripcionUpdateWebView,
)
from VAT.web_api_asistencia import (
    AsistenciaSesionCursoWebView,
    AsistenciaSesionOfertaWebView,
)
from VAT.web_api_catalogos import (
    ModalidadCursadaDetailWebView,
    ModalidadCursadaListWebView,
    SectorDetailWebView,
    SectorListWebView,
    SubsectorDetailWebView,
    SubsectorListWebView,
    TituloReferenciaDetailWebView,
    TituloReferenciaListWebView,
)
from VAT.web_api_catalogos_forms import (
    ModalidadCursadaCreateWebView,
    ModalidadCursadaDeleteWebView,
    ModalidadCursadaUpdateWebView,
    SectorCreateWebView,
    SectorDeleteWebView,
    SectorUpdateWebView,
    SubsectorCreateWebView,
    SubsectorDeleteWebView,
    SubsectorUpdateWebView,
    TituloReferenciaCreateWebView,
    TituloReferenciaDeleteWebView,
    TituloReferenciaUpdateWebView,
)
from VAT.web_api_evaluaciones_forms import (
    EvaluacionCreateWebView,
    EvaluacionDeleteWebView,
    EvaluacionUpdateWebView,
)
from VAT.web_api_parametria_detail import (
    ParametriaAsignarMasivoWebView,
    ParametriaAsignarWebView,
    ParametriaDetailWebView,
)
from VAT.web_api_voucher_forms import (
    ParametriaCreateWebView,
    VoucherCreateWebView,
    VoucherMasivoWebView,
)
from VAT.web_api_vat_contactos import (
    ContactoCreateWebView,
    ContactoDeleteWebView,
    ContactoDetailWebView,
    ContactoListWebView,
    ContactoUpdateWebView,
)
from VAT.web_api_vat_ubicaciones import (
    UbicacionCreateWebView,
    UbicacionDeleteWebView,
    UbicacionDetailWebView,
    UbicacionListWebView,
    UbicacionUpdateWebView,
)
from VAT.web_api_vat_identificadores import (
    IdentificadorCreateWebView,
    IdentificadorDeleteWebView,
    IdentificadorDetailWebView,
    IdentificadorListWebView,
    IdentificadorUpdateWebView,
)
from VAT.web_api_vat_modalidad_institucional import (
    ModalidadCreateWebView,
    ModalidadDeleteWebView,
    ModalidadDetailWebView,
    ModalidadListWebView,
    ModalidadUpdateWebView,
)
from VAT.web_api_vat_centro_acciones import (
    ContactoEdicionModalWebView,
    CursoCreateModalWebView,
    CursoUpdateModalWebView,
    UbicacionEdicionModalWebView,
)
from VAT.web_api_vat_centro_detalle import (
    CentroCursosPanelWebView,
    CentroDetalleWebView,
)
from VAT.web_api_vat_centro_usuario import (
    CentroGenerarUsuarioWebView,
)
from VAT.web_api_vat_centros import (
    CentroDeleteWebView,
    CentroListWebView,
)
from VAT.web_api_reportes import ReporteInscripcionesAsistenciasWebView
from VAT.web_api_resultados import (
    ResultadoCreateWebView,
    ResultadoDeleteWebView,
    ResultadoDetailWebView,
    ResultadoListWebView,
    ResultadoUpdateWebView,
)
from VAT.web_api_evaluaciones import EvaluacionDetailWebView, EvaluacionListWebView
from VAT.web_api_vouchers import (
    VoucherDetailWebView,
    VoucherListWebView,
    VoucherParametriaListWebView,
)

app_name = "vat_web_api"
urlpatterns = [
    path("session/", views.InetSessionView.as_view(), name="session"),
    path("horario-form/", views.InetHorarioFormView.as_view(), name="horario-form"),
    path(
        "ciudadano-form/", views.InetCiudadanoFormView.as_view(), name="ciudadano-form"
    ),
    path(
        "comisiones/<int:pk>/horarios/",
        views.InetHorariosView.as_view(),
        name="horarios",
    ),
    path(
        "comisiones/<int:pk>/ciudadanos/",
        views.InetCiudadanosView.as_view(),
        name="ciudadanos",
    ),
    path(
        "comisiones/<int:pk>/inscribir/",
        views.InetInscribirView.as_view(),
        name="inscribir",
    ),
    path(
        "inscripciones/<int:pk>/estado/", views.InetEstadoView.as_view(), name="estado"
    ),
    path(
        "sesiones/<int:pk>/asistencia/",
        views.InetAsistenciaView.as_view(),
        name="asistencia",
    ),
]
for resource in RESOURCES:
    if resource in ("centros", "planes"):
        urlpatterns.append(
            path(
                f"{resource}/filter-form/",
                views.InetFilterFormView.as_view(resource=resource),
                name=f"{resource}-filter-form",
            )
        )
    urlpatterns += [
        path(
            f"{resource}/",
            views.InetCollectionView.as_view(resource=resource),
            name=f"{resource}-list",
        ),
        path(
            f"{resource}/<int:pk>/",
            views.InetDetailView.as_view(resource=resource),
            name=f"{resource}-detail",
        ),
    ]
    if resource in FORM_CLASSES:
        urlpatterns += [
            path(
                f"{resource}/<int:pk>/delete-preview/",
                views.InetDeletePreviewView.as_view(resource=resource),
                name=f"{resource}-delete-preview",
            ),
            path(
                f"{resource}/form/",
                views.InetFormView.as_view(resource=resource),
                name=f"{resource}-form",
            ),
            path(
                f"{resource}/<int:pk>/form/",
                views.InetFormView.as_view(resource=resource),
                name=f"{resource}-edit-form",
            ),
            path(
                f"{resource}/options/<str:field>/",
                views.InetOptionsView.as_view(resource=resource),
                name=f"{resource}-options",
            ),
            path(
                f"{resource}/<int:pk>/options/<str:field>/",
                views.InetOptionsView.as_view(resource=resource),
                name=f"{resource}-edit-options",
            ),
        ]

# Aporte de VAT a Ciudadano 360 (C04).
urlpatterns += [
    path(
        "ciudadanos/<int:pk>/aportes/<str:aporte>/",
        AporteCiudadanoWebView.as_view(backend="vat"),
        name="ciudadano-aporte",
    ),
]

# V01.01 vouchers y parametrías, V08.01 evaluaciones: lectura de las vistas nativas.
urlpatterns += [
    path("vouchers/", VoucherListWebView.as_view(), name="vouchers-list"),
    path(
        "vouchers/parametrias/",
        VoucherParametriaListWebView.as_view(),
        name="vouchers-parametrias-list",
    ),
    path("vouchers/<int:pk>/", VoucherDetailWebView.as_view(), name="vouchers-detail"),
    path(
        "evaluaciones/nueva/",
        EvaluacionCreateWebView.as_view(),
        name="evaluaciones-create",
    ),
    path(
        "evaluaciones/<int:pk>/editar/",
        EvaluacionUpdateWebView.as_view(),
        name="evaluaciones-update",
    ),
    path(
        "evaluaciones/<int:pk>/eliminar/",
        EvaluacionDeleteWebView.as_view(),
        name="evaluaciones-delete",
    ),
    path("evaluaciones/", EvaluacionListWebView.as_view(), name="evaluaciones-list"),
    path(
        "evaluaciones/<int:pk>/",
        EvaluacionDetailWebView.as_view(),
        name="evaluaciones-detail",
    ),
]

# V08.01/V08.02 resultados de evaluación (vistas nativas).
urlpatterns += [
    path(
        "resultados-evaluacion/nuevo/",
        ResultadoCreateWebView.as_view(),
        name="resultados-create",
    ),
    path(
        "resultados-evaluacion/<int:pk>/editar/",
        ResultadoUpdateWebView.as_view(),
        name="resultados-update",
    ),
    path(
        "resultados-evaluacion/<int:pk>/eliminar/",
        ResultadoDeleteWebView.as_view(),
        name="resultados-delete",
    ),
    path(
        "resultados-evaluacion/", ResultadoListWebView.as_view(), name="resultados-list"
    ),
    path(
        "resultados-evaluacion/<int:pk>/",
        ResultadoDetailWebView.as_view(),
        name="resultados-detail",
    ),
]

# V08.01 reporte de inscriptos y asistencias (las exportaciones siguen nativas).
urlpatterns += [
    path(
        "reportes/inscripciones-asistencias/",
        ReporteInscripcionesAsistenciasWebView.as_view(),
        name="reportes-inscripciones-asistencias",
    ),
]

# V01.02 alta de voucher, alta masiva y alta de parametría (vistas nativas).
urlpatterns += [
    path("vouchers/asignar/", VoucherCreateWebView.as_view(), name="vouchers-asignar"),
    path(
        "vouchers/asignar-masivo/",
        VoucherMasivoWebView.as_view(),
        name="vouchers-asignar-masivo",
    ),
    path(
        "vouchers/parametrias/nueva/",
        ParametriaCreateWebView.as_view(),
        name="vouchers-parametrias-create",
    ),
]

# V01.01/V01.03 detalle de parametría y asignaciones (vistas nativas).
urlpatterns += [
    path(
        "vouchers/parametrias/<int:pk>/",
        ParametriaDetailWebView.as_view(),
        name="vouchers-parametrias-detail",
    ),
    path(
        "vouchers/parametrias/<int:pk>/asignar/",
        ParametriaAsignarWebView.as_view(),
        name="vouchers-parametrias-asignar",
    ),
    path(
        "vouchers/parametrias/<int:pk>/asignar-masivo/",
        ParametriaAsignarMasivoWebView.as_view(),
        name="vouchers-parametrias-asignar-masivo",
    ),
]

# V02.01 asistencia por sesión (vistas nativas).
urlpatterns += [
    path(
        "cursos/comisiones/sesiones/<int:pk>/asistencia/",
        AsistenciaSesionCursoWebView.as_view(),
        name="asistencia-sesion-curso",
    ),
    path(
        "comisiones/sesiones/<int:pk>/asistencia/",
        AsistenciaSesionOfertaWebView.as_view(),
        name="asistencia-sesion-oferta",
    ),
]

# V03.01 inscripciones a comisiones de oferta (vistas nativas).
urlpatterns += [
    path(
        "inscripciones-oferta/nueva/",
        InscripcionOfertaCreateWebView.as_view(),
        name="inscripciones-oferta-create",
    ),
    path(
        "inscripciones-oferta/<int:pk>/editar/",
        InscripcionOfertaUpdateWebView.as_view(),
        name="inscripciones-oferta-update",
    ),
    path(
        "inscripciones-oferta/<int:pk>/eliminar/",
        InscripcionOfertaDeleteWebView.as_view(),
        name="inscripciones-oferta-delete",
    ),
    path(
        "inscripciones-oferta/",
        InscripcionOfertaListWebView.as_view(),
        name="inscripciones-oferta-list",
    ),
    path(
        "inscripciones-oferta/<int:pk>/",
        InscripcionOfertaDetailWebView.as_view(),
        name="inscripciones-oferta-detail",
    ),
]

# V07.01 y V07.02 catálogos: sectores, subsectores, modalidades de cursado y títulos de referencia (vistas nativas).
urlpatterns += [
    path(
        "catalogos/sectores/nuevo/",
        SectorCreateWebView.as_view(),
        name="catalogos-sector-create",
    ),
    path(
        "catalogos/sectores/<int:pk>/editar/",
        SectorUpdateWebView.as_view(),
        name="catalogos-sector-update",
    ),
    path(
        "catalogos/sectores/<int:pk>/eliminar/",
        SectorDeleteWebView.as_view(),
        name="catalogos-sector-delete",
    ),
    path(
        "catalogos/sectores/",
        SectorListWebView.as_view(),
        name="catalogos-sector-list",
    ),
    path(
        "catalogos/sectores/<int:pk>/",
        SectorDetailWebView.as_view(),
        name="catalogos-sector-detail",
    ),
    path(
        "catalogos/subsectores/nuevo/",
        SubsectorCreateWebView.as_view(),
        name="catalogos-subsector-create",
    ),
    path(
        "catalogos/subsectores/<int:pk>/editar/",
        SubsectorUpdateWebView.as_view(),
        name="catalogos-subsector-update",
    ),
    path(
        "catalogos/subsectores/<int:pk>/eliminar/",
        SubsectorDeleteWebView.as_view(),
        name="catalogos-subsector-delete",
    ),
    path(
        "catalogos/subsectores/",
        SubsectorListWebView.as_view(),
        name="catalogos-subsector-list",
    ),
    path(
        "catalogos/subsectores/<int:pk>/",
        SubsectorDetailWebView.as_view(),
        name="catalogos-subsector-detail",
    ),
    path(
        "catalogos/modalidades-cursado/nueva/",
        ModalidadCursadaCreateWebView.as_view(),
        name="catalogos-modalidadcursada-create",
    ),
    path(
        "catalogos/modalidades-cursado/<int:pk>/editar/",
        ModalidadCursadaUpdateWebView.as_view(),
        name="catalogos-modalidadcursada-update",
    ),
    path(
        "catalogos/modalidades-cursado/<int:pk>/eliminar/",
        ModalidadCursadaDeleteWebView.as_view(),
        name="catalogos-modalidadcursada-delete",
    ),
    path(
        "catalogos/modalidades-cursado/",
        ModalidadCursadaListWebView.as_view(),
        name="catalogos-modalidadcursada-list",
    ),
    path(
        "catalogos/modalidades-cursado/<int:pk>/",
        ModalidadCursadaDetailWebView.as_view(),
        name="catalogos-modalidadcursada-detail",
    ),
    path(
        "catalogos/titulos-referencia/nuevo/",
        TituloReferenciaCreateWebView.as_view(),
        name="catalogos-titulorreferencia-create",
    ),
    path(
        "catalogos/titulos-referencia/<int:pk>/editar/",
        TituloReferenciaUpdateWebView.as_view(),
        name="catalogos-titulorreferencia-update",
    ),
    path(
        "catalogos/titulos-referencia/<int:pk>/eliminar/",
        TituloReferenciaDeleteWebView.as_view(),
        name="catalogos-titulorreferencia-delete",
    ),
    path(
        "catalogos/titulos-referencia/",
        TituloReferenciaListWebView.as_view(),
        name="catalogos-titulorreferencia-list",
    ),
    path(
        "catalogos/titulos-referencia/<int:pk>/",
        TituloReferenciaDetailWebView.as_view(),
        name="catalogos-titulorreferencia-detail",
    ),
]

# V03.02 inscripciones (U3): vistas nativas de ``views/persona.py`` y sus acciones. Prefijo
# propio: ``inscripciones/`` es el recurso del front INET.
urlpatterns += [
    path(
        "inscripciones-persona/",
        InscripcionListWebView.as_view(),
        name="inscripciones-persona-list",
    ),
    path(
        "inscripciones-persona/nueva/",
        InscripcionCreateWebView.as_view(),
        name="inscripciones-persona-create",
    ),
    path(
        "inscripciones-persona/rapida-comision/",
        InscripcionRapidaComisionWebView.as_view(),
        name="inscripciones-persona-rapida-comision",
    ),
    path(
        "inscripciones-persona/cursos/rapida-comision/",
        InscripcionRapidaComisionCursoWebView.as_view(),
        name="inscripciones-persona-rapida-comision-curso",
    ),
    path(
        "inscripciones-persona/cursos/<int:pk>/cambiar-estado/",
        InscripcionCursoCambiarEstadoWebView.as_view(),
        name="inscripciones-persona-curso-cambiar-estado",
    ),
    path(
        "inscripciones-persona/cursos/comisiones/<int:pk>/cambiar-estado-lote/",
        InscripcionCursoCambiarEstadoLoteWebView.as_view(),
        name="inscripciones-persona-curso-cambiar-estado-lote",
    ),
    path(
        "inscripciones-persona/<int:pk>/",
        InscripcionDetailWebView.as_view(),
        name="inscripciones-persona-detail",
    ),
    path(
        "inscripciones-persona/<int:pk>/editar/",
        InscripcionUpdateWebView.as_view(),
        name="inscripciones-persona-update",
    ),
    path(
        "inscripciones-persona/<int:pk>/eliminar/",
        InscripcionDeleteWebView.as_view(),
        name="inscripciones-persona-delete",
    ),
    path(
        "inscripciones-persona/<int:pk>/cambiar-estado/",
        InscripcionCambiarEstadoWebView.as_view(),
        name="inscripciones-persona-cambiar-estado",
    ),
    path(
        "buscador-ciudadano/",
        BuscadorCiudadanoWebView.as_view(),
        name="buscador-ciudadano",
    ),
]

# V06.01 modalidades institucionales (vistas nativas).
urlpatterns += [
    path(
        "modalidades-institucionales/nueva/",
        ModalidadCreateWebView.as_view(),
        name="modalidades-institucionales-create",
    ),
    path(
        "modalidades-institucionales/<int:pk>/editar/",
        ModalidadUpdateWebView.as_view(),
        name="modalidades-institucionales-update",
    ),
    path(
        "modalidades-institucionales/<int:pk>/eliminar/",
        ModalidadDeleteWebView.as_view(),
        name="modalidades-institucionales-delete",
    ),
    path(
        "modalidades-institucionales/",
        ModalidadListWebView.as_view(),
        name="modalidades-institucionales-list",
    ),
    path(
        "modalidades-institucionales/<int:pk>/",
        ModalidadDetailWebView.as_view(),
        name="modalidades-institucionales-detail",
    ),
]

# V06.01 contactos de institución (vistas nativas).
urlpatterns += [
    path(
        "institucion/contactos/nuevo/",
        ContactoCreateWebView.as_view(),
        name="institucion-contactos-create",
    ),
    path(
        "institucion/contactos/<int:pk>/editar/",
        ContactoUpdateWebView.as_view(),
        name="institucion-contactos-update",
    ),
    path(
        "institucion/contactos/<int:pk>/eliminar/",
        ContactoDeleteWebView.as_view(),
        name="institucion-contactos-delete",
    ),
    path(
        "institucion/contactos/",
        ContactoListWebView.as_view(),
        name="institucion-contactos-list",
    ),
    path(
        "institucion/contactos/<int:pk>/",
        ContactoDetailWebView.as_view(),
        name="institucion-contactos-detail",
    ),
]

# V04.01 detalle de comisión (U4): vistas nativas ``ComisionDetailView`` y ``ComisionCursoDetailView``.
urlpatterns += [
    path(
        "comisiones-detalle/cursos/<int:pk>/resultados/",
        ComisionCursoResultadosWebView.as_view(),
        name="comisiones-detalle-curso-resultados",
    ),
    path(
        "comisiones-detalle/cursos/<int:pk>/profesores/buscar/",
        ProfesorCentroBuscarWebView.as_view(),
        name="comisiones-detalle-curso-profesores-buscar",
    ),
    path(
        "comisiones-detalle/cursos/<int:pk>/profesores/nuevo/",
        ProfesorCentroCrearWebView.as_view(),
        name="comisiones-detalle-curso-profesores-nuevo",
    ),
    path(
        "comisiones-detalle/cursos/<int:pk>/",
        ComisionDetalleCursoWebView.as_view(),
        name="comisiones-detalle-curso",
    ),
    path(
        "comisiones-detalle/<int:pk>/",
        ComisionDetalleOfertaWebView.as_view(),
        name="comisiones-detalle-oferta",
    ),
]

# V04.02 horarios de comisión: alta, edición y baja (vistas nativas).
urlpatterns += [
    path(
        "comisiones-horarios/nuevo/",
        ComisionHorarioCreateWebView.as_view(),
        name="comisiones-horarios-create",
    ),
    path(
        "comisiones-horarios/<int:pk>/editar/",
        ComisionHorarioUpdateWebView.as_view(),
        name="comisiones-horarios-update",
    ),
    path(
        "comisiones-horarios/<int:pk>/eliminar/",
        ComisionHorarioDeleteWebView.as_view(),
        name="comisiones-horarios-delete",
    ),
    path(
        "comisiones-horarios/cursos/nuevo/",
        ComisionCursoHorarioCreateWebView.as_view(),
        name="comisiones-horarios-curso-create",
    ),
    path(
        "comisiones-horarios/cursos/<int:pk>/editar/",
        ComisionCursoHorarioUpdateWebView.as_view(),
        name="comisiones-horarios-curso-update",
    ),
    path(
        "comisiones-horarios/cursos/<int:pk>/eliminar/",
        ComisionCursoHorarioDeleteWebView.as_view(),
        name="comisiones-horarios-curso-delete",
    ),
]

# V06.01 identificadores históricos de institución (vistas nativas).
urlpatterns += [
    path(
        "institucion/identificadores/nuevo/",
        IdentificadorCreateWebView.as_view(),
        name="institucion-identificadores-create",
    ),
    path(
        "institucion/identificadores/<int:pk>/editar/",
        IdentificadorUpdateWebView.as_view(),
        name="institucion-identificadores-update",
    ),
    path(
        "institucion/identificadores/<int:pk>/eliminar/",
        IdentificadorDeleteWebView.as_view(),
        name="institucion-identificadores-delete",
    ),
    path(
        "institucion/identificadores/",
        IdentificadorListWebView.as_view(),
        name="institucion-identificadores-list",
    ),
    path(
        "institucion/identificadores/<int:pk>/",
        IdentificadorDetailWebView.as_view(),
        name="institucion-identificadores-detail",
    ),
]

# V06.01 ubicaciones de institución (vistas nativas).
urlpatterns += [
    path(
        "institucion/ubicaciones/nuevo/",
        UbicacionCreateWebView.as_view(),
        name="institucion-ubicaciones-create",
    ),
    path(
        "institucion/ubicaciones/<int:pk>/editar/",
        UbicacionUpdateWebView.as_view(),
        name="institucion-ubicaciones-update",
    ),
    path(
        "institucion/ubicaciones/<int:pk>/eliminar/",
        UbicacionDeleteWebView.as_view(),
        name="institucion-ubicaciones-delete",
    ),
    path(
        "institucion/ubicaciones/",
        UbicacionListWebView.as_view(),
        name="institucion-ubicaciones-list",
    ),
    path(
        "institucion/ubicaciones/<int:pk>/",
        UbicacionDetailWebView.as_view(),
        name="institucion-ubicaciones-detail",
    ),
]

# V04.02 comisiones de oferta y de curso: alta, edición y baja (vistas nativas).
urlpatterns += [
    path(
        "comisiones-formularios/nueva/",
        ComisionCreateWebView.as_view(),
        name="comisiones-formularios-create",
    ),
    path(
        "comisiones-formularios/<int:pk>/editar/",
        ComisionUpdateWebView.as_view(),
        name="comisiones-formularios-update",
    ),
    path(
        "comisiones-formularios/<int:pk>/eliminar/",
        ComisionDeleteWebView.as_view(),
        name="comisiones-formularios-delete",
    ),
    path(
        "comisiones-formularios/cursos/nueva/",
        ComisionCursoCreateWebView.as_view(),
        name="comisiones-formularios-curso-create",
    ),
    path(
        "comisiones-formularios/cursos/<int:pk>/editar/",
        ComisionCursoUpdateWebView.as_view(),
        name="comisiones-formularios-curso-update",
    ),
    path(
        "comisiones-formularios/cursos/<int:pk>/eliminar/",
        ComisionCursoDeleteWebView.as_view(),
        name="comisiones-formularios-curso-delete",
    ),
]

# V06.01 lista y baja de centros (vistas nativas).
urlpatterns += [
    path(
        "centros-lista/",
        CentroListWebView.as_view(),
        name="centros-lista",
    ),
    path(
        "centros-lista/<int:pk>/eliminar/",
        CentroDeleteWebView.as_view(),
        name="centros-lista-delete",
    ),
]

# V06.02 generar usuario de un centro (vista nativa).
urlpatterns += [
    path(
        "centros-usuarios/<int:pk>/generar/",
        CentroGenerarUsuarioWebView.as_view(),
        name="centros-usuarios-generar",
    ),
]

# V04.02 asistente de alta de comisión de curso (vista nativa del asistente de tres pasos).
urlpatterns += [
    path(
        "comisiones-asistente/cursos/<int:curso_id>/",
        ComisionCursoAsistenteWebView.as_view(),
        name="comisiones-asistente-curso",
    ),
]

# V05.01 ofertas institucionales (lista y detalle) y detalle de curso (vistas nativas).
urlpatterns += [
    path(
        "ofertas-institucionales/",
        OfertaInstitucionalListWebView.as_view(),
        name="ofertas-institucionales-list",
    ),
    path(
        "ofertas-institucionales/<int:pk>/",
        OfertaInstitucionalDetailWebView.as_view(),
        name="ofertas-institucionales-detail",
    ),
    path(
        "cursos-detalle/<int:pk>/",
        CursoDetailWebView.as_view(),
        name="cursos-detalle",
    ),
]

# V05.02 ofertas institucionales y cursos: alta, edición y baja (vistas nativas).
urlpatterns += [
    path(
        "ofertas-institucionales/nueva/",
        OfertaInstitucionalCreateWebView.as_view(),
        name="ofertas-institucionales-create",
    ),
    path(
        "ofertas-institucionales/<int:pk>/editar/",
        OfertaInstitucionalUpdateWebView.as_view(),
        name="ofertas-institucionales-update",
    ),
    path(
        "ofertas-institucionales/<int:pk>/eliminar/",
        OfertaInstitucionalDeleteWebView.as_view(),
        name="ofertas-institucionales-delete",
    ),
    path(
        "cursos-formularios/nuevo/",
        CursoCreateWebView.as_view(),
        name="cursos-formularios-create",
    ),
    path(
        "cursos-formularios/<int:pk>/editar/",
        CursoUpdateWebView.as_view(),
        name="cursos-formularios-update",
    ),
    path(
        "cursos-formularios/<int:pk>/eliminar/",
        CursoDeleteWebView.as_view(),
        name="cursos-formularios-delete",
    ),
]

# V06.01 detalle de un centro y V05.01 su panel de cursos y comisiones (vistas nativas).
urlpatterns += [
    path(
        "centros-detalle/<int:pk>/",
        CentroDetalleWebView.as_view(),
        name="centros-detalle",
    ),
    path(
        "centros-detalle/<int:pk>/cursos/",
        CentroCursosPanelWebView.as_view(),
        name="centros-detalle-cursos",
    ),
]

# V06.01/V05.01 acciones en página del detalle de un centro: modales de contactos, ubicaciones y cursos (vistas nativas).
urlpatterns += [
    path(
        "centros-acciones/contactos/<int:pk>/editar/",
        ContactoEdicionModalWebView.as_view(),
        name="centros-acciones-contactos-editar",
    ),
    path(
        "centros-acciones/ubicaciones/<int:pk>/editar/",
        UbicacionEdicionModalWebView.as_view(),
        name="centros-acciones-ubicaciones-editar",
    ),
    path(
        "centros-acciones/cursos/nuevo/",
        CursoCreateModalWebView.as_view(),
        name="centros-acciones-cursos-nuevo",
    ),
    path(
        "centros-acciones/cursos/<int:pk>/editar/",
        CursoUpdateModalWebView.as_view(),
        name="centros-acciones-cursos-editar",
    ),
]
