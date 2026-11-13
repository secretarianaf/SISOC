"""Rutas same-origin del frontend INET bajo ``/api/web/vat/`` (G1 v1).

Ver ``docs/plans/2026-T4/2026-11-10-2785-vat-api-web-m2.md``.
"""

from django.urls import path
from ciudadanos.web_aportes import AporteCiudadanoWebView
from VAT import api_inet_views as views
from VAT.services.inet_forms import FORM_CLASSES
from VAT.services.inet_queries import RESOURCES
from VAT.web_api_asistencia import (
    AsistenciaSesionCursoWebView,
    AsistenciaSesionOfertaWebView,
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
