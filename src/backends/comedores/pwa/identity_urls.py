"""Rutas internas: nunca añadir este prefijo al proxy público de Comedores."""

from django.urls import path
from pwa.identity_services import EspaciosContextView, EspaciosLoginView

urlpatterns = [
    path("login/", EspaciosLoginView.as_view()),
    path("contexto/", EspaciosContextView.as_view()),
]
