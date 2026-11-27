from django.contrib.auth.decorators import login_required
from django.urls import path

from dashboard.views import (
    DashboardView,
    TableroEmbedView,
    TableroProgresarCursoView,
)
from dashboard.views_datos import AdministracionDatosView
from dashboard.views_audiencias import (
    AudienciasDatosView,
    AudienciaDetalleView,
    BuscarMiembrosAudienciaView,
)
from dashboard.views_selector_cdi import BuscarCDIView, SeleccionarCDIView
from dashboard.views_alcance_celiaquia import AlcanceCeliaquiaView
from dashboard.views_asignaciones import (
    BuscarUsuariosDatosView,
    AsignacionesUsuarioView,
)

urlpatterns = [
    path(
        "dashboard/administracion/datos/cdi/buscar/",
        BuscarCDIView.as_view(),
        name="dashboard_buscar_cdis",
    ),
    path(
        "interno/tableros/celiaquia/alcance/",
        AlcanceCeliaquiaView.as_view(),
        name="dashboard_alcance_celiaquia",
    ),
    path(
        "dashboard/administracion/datos/cdi/<str:tipo>/<int:sujeto_id>/",
        SeleccionarCDIView.as_view(),
        name="dashboard_seleccionar_cdis",
    ),
    path(
        "dashboard/administracion/datos/audiencias/",
        AudienciasDatosView.as_view(),
        name="dashboard_audiencias_datos",
    ),
    path(
        "dashboard/administracion/datos/audiencias/<int:audiencia_id>/",
        AudienciaDetalleView.as_view(),
        name="dashboard_audiencia_detalle",
    ),
    path(
        "dashboard/administracion/datos/audiencias/<int:audiencia_id>/miembros/buscar/",
        BuscarMiembrosAudienciaView.as_view(),
        name="dashboard_buscar_miembros_audiencia",
    ),
    path(
        "dashboard/administracion/datos/usuarios/",
        BuscarUsuariosDatosView.as_view(),
        name="dashboard_buscar_usuarios_datos",
    ),
    path(
        "dashboard/administracion/datos/usuarios/<int:usuario_id>/",
        AsignacionesUsuarioView.as_view(),
        name="dashboard_asignaciones_usuario",
    ),
    path(
        "dashboard/administracion/datos/",
        AdministracionDatosView.as_view(),
        name="dashboard_administracion_datos",
    ),
    path(
        "dashboard/centro-de-familia",
        login_required(DashboardView.as_view()),
        name="dashboard",
    ),
    # Antes que "dashboard/<slug>/": si no, el slug la tomaría como un tablero embebido.
    path(
        "dashboard/progresar-curso-obligatorio/",
        login_required(TableroProgresarCursoView.as_view()),
        name="dashboard_tablero_progresar_curso",
    ),
    path(
        "dashboard/<slug:slug>/",
        login_required(TableroEmbedView.as_view()),
        name="dashboard_tablero",
    ),
]
