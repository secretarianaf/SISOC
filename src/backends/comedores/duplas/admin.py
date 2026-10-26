from django.contrib import admin
from core.admin_base import SisocModelAdmin
from duplas.models import Dupla

admin.site.register(Dupla, SisocModelAdmin)
