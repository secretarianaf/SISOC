"""Rutas internas same-origin de INET React."""

from django.urls import path
from VAT import api_inet_views as views
from VAT.services.inet_forms import FORM_CLASSES
from VAT.services.inet_queries import RESOURCES

app_name = "inet_api"
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
