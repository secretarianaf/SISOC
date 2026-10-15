"""Panel de Inspecciones escolares en el backoffice: base común de las vistas.

Todas las vistas del panel (pantallas, AJAX, imágenes y PDF) exigen sesión y
``puede_gestionar`` (coordinación, permiso ``gestionar_inspecciones`` o
superusuario); sin permiso responden 403. Las vistas no tienen lógica:
delegan en ``inspecciones.services``.

- Escuelas: ``views_escuelas``; importaciones: ``views_importacion``.
- Asignaciones: ``views_asignaciones``; actas: ``views_actas``.
- Búsquedas de Select2: ``views_ajax``.
"""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse

from inspecciones.access import puede_gestionar
from inspecciones.services.formato import iniciales
from inspecciones.services.panel import resumen_panel


class GestionInspeccionesMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return puede_gestionar(self.request.user)


def es_parcial(request):
    """Pedido del modal (fetch): responde sólo el fragmento del formulario."""
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _parametros_sin(parametros, *claves):
    """Querystring sin esas claves, con ``&`` final para encadenar ``page=``."""
    copia = parametros.copy()
    for clave in claves:
        copia.pop(clave, None)
    texto = copia.urlencode()
    return f"{texto}&" if texto else ""


class LayoutInspeccionesMixin:
    """Contexto de ``inspecciones/base_layout.html``: breadcrumb desde Inicio,
    iniciales del usuario para la cabecera y sin el botón "Volver" de SISOC."""

    titulo = ""

    def migas(self):
        items = [
            {"text": "Inicio", "url": reverse("inicio")},
            {"text": "Inspecciones escolares"},
        ]
        if self.titulo:
            items[1]["url"] = reverse("inspecciones_panel")
            items.append({"text": self.titulo})
        return items

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = self.request.user
        context["breadcrumb_items"] = self.migas()
        context["iniciales_usuario"] = iniciales(
            usuario.get_full_name() or usuario.get_username()
        )
        perfil = getattr(usuario, "profile", None)
        mostrar_rol = getattr(perfil, "get_inspecciones_rol_display", None)
        context["rol_usuario"] = (
            mostrar_rol() if mostrar_rol and perfil.inspecciones_rol else ""
        )
        context["ocultar_volver"] = True
        return context


class PanelMixin(LayoutInspeccionesMixin, GestionInspeccionesMixin):
    """Contexto común del panel: totales (solo en Escuelas), pestañas y paginación."""

    pestana = "escuelas"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pestana"] = self.pestana
        context["mostrar_totales"] = self.pestana == "escuelas"
        if context["mostrar_totales"]:
            context["totales_panel"] = resumen_panel()
        context["parametros_sin_pagina"] = _parametros_sin(self.request.GET, "page")
        return context
