"""Módulo de reportes de Centro de Infancia (issue #2508)."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView, View

from centrodeinfancia.services_reportes import (
    COLUMNAS_RESUMEN,
    REPORTE_COMPLETO,
    VARIANTES_REPORTE,
    filas_resumen,
    generar_reporte_cdi_xlsx,
    provincias_en_alcance,
    resolver_variante,
    variantes_disponibles,
)
from iam.services import user_has_permission_code


# Permiso propio del módulo y no `auth.role_exportar_a_csv`: ese es global y
# habilitaría a los roles SIMEPI a exportar comedores, usuarios y los demás
# listados. Custodia tanto la pantalla como la descarga.
PERMISO_REPORTES = "auth.role_reportes_cdi"
XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def puede_ver_reportes(user):
    if getattr(user, "is_superuser", False):
        return True
    return user_has_permission_code(user, PERMISO_REPORTES)


class ReportesCDIView(LoginRequiredMixin, TemplateView):
    """Pantalla del módulo, con la vista previa de la hoja Resumen."""

    template_name = "centrodeinfancia/reportes.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        provincia_id = self.request.GET.get("provincia") or ""
        context["provincias"] = provincias_en_alcance(self.request.user)
        context["provincia_seleccionada"] = provincia_id
        context["variantes"] = [
            (codigo, VARIANTES_REPORTE[codigo])
            for codigo in variantes_disponibles(self.request.user)
        ]
        # La vista previa es exactamente la primera hoja del archivo.
        context["resumen_columnas"] = COLUMNAS_RESUMEN
        context["resumen_filas"] = filas_resumen(self.request.user, provincia_id)
        context["breadcrumb_items"] = [
            {
                "text": "Centro de Desarrollo Infantil",
                "url": reverse("centrodeinfancia"),
            },
            {"text": "Reportes", "active": True},
        ]
        return context


class ReporteCDIDescargaView(LoginRequiredMixin, View):
    """Descarga el XLSX con lo que el usuario puede ver, nunca más que eso."""

    def get(self, request, *args, **kwargs):
        if not puede_ver_reportes(request.user):
            raise PermissionDenied("No tiene permiso para descargar reportes de CDI.")

        # El filtro solo acota: el alcance del usuario se aplica igual.
        provincia_id = request.GET.get("provincia") or None
        # La variante pedida solo se respeta si el rol la tiene: quien no puede
        # ver el reporte completo recibe el reducido aunque edite la URL.
        variante = resolver_variante(request.user, request.GET.get("variante"))
        contenido = generar_reporte_cdi_xlsx(request.user, provincia_id, variante)
        sufijo = "" if variante == REPORTE_COMPLETO else f"-{variante}"
        nombre = f"reporte-cdi{sufijo}-{timezone.localdate():%Y%m%d}.xlsx"
        response = HttpResponse(contenido, content_type=XLSX_CONTENT_TYPE)
        response["Content-Disposition"] = f'attachment; filename="{nombre}"'
        # El archivo contiene datos personales de niños, niñas y responsables.
        response["Cache-Control"] = "private, no-store"
        response["Pragma"] = "no-cache"
        return response
