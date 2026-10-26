from django.urls import path
from core.decorators import permissions_all_required, permissions_any_required
from dispositivos.views import (
    DispositivoCreateView,
    DispositivoUpdateView,
    DispositivoDeleteView,
    DispositivoListView,
    DispositivoMapView,
    DispositivoLocationView,
    DispositivoLocationPreviewView,
    DispositivoDetailView,
)

MAPA_PERMISSIONS = [
    "dispositivos.view_dispositivo",
    "dispositivos.ver_mapa_dispositivo",
]


urlpatterns = [
    path(
        "dispositivos/ubicacion/previsualizar/",
        permissions_any_required(
            ["dispositivos.add_dispositivo", "dispositivos.change_dispositivo"]
        )(DispositivoLocationPreviewView.as_view()),
        name="dispositivos_previsualizar_ubicacion",
    ),
    path(
        "dispositivos/mapa/",
        permissions_all_required(MAPA_PERMISSIONS)(DispositivoMapView.as_view()),
        name="dispositivos_mapa",
    ),
    path(
        "dispositivos/<int:pk>/ubicacion/",
        permissions_all_required(MAPA_PERMISSIONS)(DispositivoLocationView.as_view()),
        name="dispositivos_ubicacion",
    ),
    path(
        "dispositivos/crear",
        permissions_any_required(["dispositivos.add_dispositivo"])(
            DispositivoCreateView.as_view()
        ),
        name="dispositivos_crear",
    ),
    path(
        "dispositivos/<int:pk>/",
        permissions_any_required(["dispositivos.view_dispositivo"])(
            DispositivoDetailView.as_view()
        ),
        name="dispositivos_detalle",
    ),
    path(
        "dispositivos/<int:pk>/editar",
        permissions_any_required(["dispositivos.change_dispositivo"])(
            DispositivoUpdateView.as_view()
        ),
        name="dispositivos_editar",
    ),
    path(
        "dispositivos/<int:pk>/eliminar",
        permissions_any_required(["dispositivos.delete_dispositivo"])(
            DispositivoDeleteView.as_view()
        ),
        name="dispositivos_eliminar",
    ),
    path(
        "dispositivos/",
        permissions_any_required(["dispositivos.view_dispositivo"])(
            DispositivoListView.as_view()
        ),
        name="dispositivos_listar",
    ),
]
