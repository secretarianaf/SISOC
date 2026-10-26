from django.contrib import admin
from core.admin_base import SisocModelAdmin
from acompanamientos.models.acompanamiento import (
    Acompanamiento,
    InformacionRelevante,
    Prestacion,
)
from acompanamientos.models.hitos import Hitos, HitosIntervenciones

# acompañamientos
admin.site.register(Acompanamiento, SisocModelAdmin)
admin.site.register(InformacionRelevante, SisocModelAdmin)
admin.site.register(Prestacion, SisocModelAdmin)

# hitos
admin.site.register(Hitos, SisocModelAdmin)
admin.site.register(HitosIntervenciones, SisocModelAdmin)
