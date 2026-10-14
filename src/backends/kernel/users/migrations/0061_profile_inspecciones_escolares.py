"""Sección "Inspecciones escolares" del ABM de usuarios.

Agrega el flag ``Profile.es_inspector_escolar`` y el rol
``Profile.inspecciones_rol`` (PWA Sisoc Inspecciones) y el permiso de la
sección ``auth.role_usuarios_seccion_inspecciones_escolares``.

El permiso se otorga a los grupos y usuarios que hoy administran la sección
de administración de accesos: son los perfiles que ya ven todas las secciones.
Los gestores por programa (Comedores, DataCalle, CDI) no la reciben.
"""

from django.db import migrations, models

CODENAME = "role_usuarios_seccion_inspecciones_escolares"
NOMBRE = "Usuarios - Sección Inspecciones escolares"
CODENAME_ADMINISTRACION = "role_usuarios_seccion_administracion"


def asignar(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")
    User = apps.get_model("auth", "User")
    group_ct, _ = ContentType.objects.get_or_create(app_label="auth", model="group")
    permiso, _ = Permission.objects.get_or_create(
        content_type=group_ct,
        codename=CODENAME,
        defaults={"name": NOMBRE},
    )
    filtro = {
        "permissions__content_type__app_label": "auth",
        "permissions__codename": CODENAME_ADMINISTRACION,
    }
    for grupo in Group.objects.filter(**filtro).distinct():
        grupo.permissions.add(permiso)
    usuarios = User.objects.filter(
        is_superuser=False,
        user_permissions__content_type__app_label="auth",
        user_permissions__codename=CODENAME_ADMINISTRACION,
    ).distinct()
    for usuario in usuarios:
        usuario.user_permissions.add(permiso)


def desasignar(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    Permission.objects.filter(
        content_type__app_label="auth", codename=CODENAME
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0060_profile_accesos_siis_web"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="es_inspector_escolar",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Habilita el acceso a la PWA Sisoc Inspecciones. El rol en el "
                    "programa se define en inspecciones_rol."
                ),
                verbose_name="Pertenece a Inspecciones escolares",
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="inspecciones_rol",
            field=models.CharField(
                blank=True,
                choices=[("inspector", "Inspector"), ("coordinacion", "Coordinación")],
                default="",
                help_text=(
                    "Inspector (ve y modifica lo propio) o Coordinación (ve todo). "
                    "Obligatorio cuando es_inspector_escolar esta activo."
                ),
                max_length=20,
                verbose_name="Rol en Inspecciones escolares",
            ),
        ),
        migrations.RunPython(asignar, desasignar),
    ]
