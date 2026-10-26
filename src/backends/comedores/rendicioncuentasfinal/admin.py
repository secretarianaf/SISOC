from django.contrib import admin

from core.admin_base import SisocModelAdmin
from rendicioncuentasfinal.models import (
    DocumentoRendicionFinal,
    EstadoDocumentoRendicionFinal,
    RendicionCuentasFinal,
    TipoDocumentoRendicionFinal,
)


admin.site.register(RendicionCuentasFinal, SisocModelAdmin)
admin.site.register(EstadoDocumentoRendicionFinal, SisocModelAdmin)
admin.site.register(TipoDocumentoRendicionFinal, SisocModelAdmin)
admin.site.register(DocumentoRendicionFinal, SisocModelAdmin)
