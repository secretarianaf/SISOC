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
from inspecciones.services.panel import resumen_panel


class GestionInspeccionesMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return puede_gestionar(self.request.user)


def es_parcial(request):
    """Pedido del modal (fetch): responde sólo el fragmento del formulario."""
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


class PanelMixin(GestionInspeccionesMixin):
    """Contexto común: totales arriba, pestañas y miga de pan."""

    pestana = "escuelas"
    titulo = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["resumen"] = resumen_panel()
        # Pestaña activa de ``inspecciones/_pestanas.html``.
        context["pestana"] = self.pestana
        items = [{"text": "Inspecciones escolares"}]
        if self.titulo:
            items[0]["url"] = reverse("inspecciones_panel")
            items.append({"text": self.titulo})
        context["breadcrumb_items"] = items
        return context
