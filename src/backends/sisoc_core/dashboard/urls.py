from django.contrib.auth.decorators import login_required
from django.urls import path

from core.decorators import permissions_any_required
from dashboard.models import (
    PERMISO_TABLERO_PROGRESAR_CURSO,
    PERMISO_TABLERO_PROGRESAR_CURSO_NACIONAL,
)
from dashboard.views import (
    DashboardView,
    TableroEmbedView,
    TableroProgresarCursoView,
)

urlpatterns = [
    path(
        "dashboard/centro-de-familia",
        login_required(DashboardView.as_view()),
        name="dashboard",
    ),
    # Antes que "dashboard/<slug>/": si no, el slug la tomaría como un tablero embebido.
    path(
        "dashboard/progresar-curso-obligatorio/",
        login_required(
            permissions_any_required(
                [
                    PERMISO_TABLERO_PROGRESAR_CURSO,
                    PERMISO_TABLERO_PROGRESAR_CURSO_NACIONAL,
                ]
            )(TableroProgresarCursoView.as_view())
        ),
        name="dashboard_tablero_progresar_curso",
    ),
    path(
        "dashboard/<slug:slug>/",
        login_required(TableroEmbedView.as_view()),
        name="dashboard_tablero",
    ),
]
