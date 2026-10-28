"""Métricas del admin: usuarios y jobs de carga (issue #2789)."""

from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from core.admin_dashboard import Kpi, Seccion, altas_por_mes
from users.models import BulkCredentialsJob, UserImportJob


def metricas():
    hace_30_dias = timezone.now() - timedelta(days=30)
    usuarios = User.objects.all()
    jobs_fallidos = (
        UserImportJob.objects.filter(status=UserImportJob.Status.FAILED).count()
        + BulkCredentialsJob.objects.filter(
            status=BulkCredentialsJob.Status.FAILED
        ).count()
    )
    return [
        Seccion(
            titulo="Usuarios",
            kpis=[
                Kpi("Usuarios activos", usuarios.filter(is_active=True).count()),
                Kpi(
                    "Ingresaron en 30 días",
                    usuarios.filter(last_login__gte=hace_30_dias).count(),
                ),
                Kpi(
                    "Superusuarios",
                    usuarios.filter(is_superuser=True, is_active=True).count(),
                    detalle="Tienen acceso total al admin.",
                ),
                Kpi(
                    "Jobs de carga fallidos",
                    jobs_fallidos,
                    detalle="Importación de usuarios y credenciales masivas.",
                    alerta=jobs_fallidos > 0,
                ),
            ],
            graficos=[altas_por_mes(usuarios, "date_joined", "Altas de usuarios")],
        )
    ]
