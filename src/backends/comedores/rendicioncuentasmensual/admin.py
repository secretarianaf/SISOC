from django.contrib import admin
from core.admin_base import SisocModelAdmin
from rendicioncuentasmensual.models import RendicionCuentaMensual

admin.site.register(RendicionCuentaMensual, SisocModelAdmin)
