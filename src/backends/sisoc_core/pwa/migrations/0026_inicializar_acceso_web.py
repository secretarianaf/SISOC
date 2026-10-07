"""Congela la habilitación web anterior; luego solo decide acceso_web."""

from django.db import migrations
from django.db.models import Exists, F, OuterRef, Q


def initialize_web_access(apps, schema_editor):
    alias = schema_editor.connection.alias
    Profile = apps.get_model("users", "Profile")
    Access = apps.get_model("pwa", "AccesoComedorPWA")
    Membership = apps.get_model("pwa", "AccesoOrganizacionPWA")
    Coordinator = apps.get_model("pwa", "CoordinadorEquipoTecnicoPWA")
    membership = Membership.objects.using(alias).filter(
        user_id=OuterRef("user_id"),
        organizacion_id=OuterRef("organizacion_id"),
        activo=True,
    )
    pwa_users = (
        Access.objects.using(alias)
        .filter(
            activo=True,
            comedor__deleted_at__isnull=True,
        )
        .annotate(active_membership=Exists(membership))
        .filter(
            Q(tipo_asociacion="espacio")
            | Q(
                tipo_asociacion="organizacion",
                organizacion_id=F("comedor__organizacion_id"),
                active_membership=True,
            )
        )
        .values("user_id")
    )
    profiles = Profile.objects.using(alias)
    profiles.update(acceso_web=True)
    profiles.filter(
        Q(user_id__in=pwa_users)
        | Q(
            user_id__in=Coordinator.objects.using(alias)
            .filter(activo=True)
            .values("user_id")
        )
        | Q(configuracion_mobile__es_coordinador_equipo_tecnico_pwa=True)
        | Q(datacalle_rol="entrevistador")
    ).update(acceso_web=False)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0060_profile_accesos_siis_web"),
        ("pwa", "0025_accesos_pwa_desde_users"),
    ]
    # Deshacer no recalcula habilitaciones explícitas ni borra decisiones nuevas.
    operations = [
        migrations.RunPython(initialize_web_access, migrations.RunPython.noop)
    ]
