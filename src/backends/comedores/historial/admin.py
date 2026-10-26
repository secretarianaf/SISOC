from django.contrib import admin

from core.admin_base import SisocModelAdmin
from historial.models import Historial

admin.site.register(Historial, SisocModelAdmin)
