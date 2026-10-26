from django.contrib import admin
from core.admin_base import SisocModelAdmin
from expedientespagos.models import ExpedientePago

admin.site.register(ExpedientePago, SisocModelAdmin)
