from django.contrib import admin

from intervenciones.models.intervenciones import Intervencion

# Intervencion registra actividad de negocio con soft delete y signals que crean
# hitos: no se habilita import/export desde admin. Los catálogos se administran
# desde catalogo_intervenciones (kernel).
admin.site.register(Intervencion)
