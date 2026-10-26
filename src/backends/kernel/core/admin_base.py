"""Bases comunes de los ModelAdmin de SISOC sobre Django Unfold (issue #2789).

Todo ``admin.py`` del repo hereda de acá en vez de ``django.contrib.admin``:
así el look, los filtros y las acciones de Unfold quedan iguales en todos los
dominios y en todos los runtimes.
"""

from unfold.admin import ModelAdmin, StackedInline, TabularInline

class SisocModelAdmin(ModelAdmin):
    """ModelAdmin base del admin de desarrollo y soporte."""

    # Los filtros de Unfold (rangos, dropdowns) se aplican con un botón.
    list_filter_submit = True
    # Evita un COUNT(*) sin filtros por cada listado en tablas grandes de PRD.
    show_full_result_count = False


class SisocTabularInline(TabularInline):
    """Inline tabular con estilo Unfold."""


class SisocStackedInline(StackedInline):
    """Inline apilado con estilo Unfold."""
