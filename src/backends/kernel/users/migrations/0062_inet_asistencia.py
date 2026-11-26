"""Perfil docente con permisos mínimos; no concede gestión de inscripciones."""

from django.db import migrations


def crear_grupo_asistencia(apps, schema_editor):
    alias = schema_editor.connection.alias
    group_model = apps.get_model("auth", "Group")
    permission_model = apps.get_model("auth", "Permission")
    content_type_model = apps.get_model("contenttypes", "ContentType")
    group, _ = group_model.objects.using(alias).get_or_create(name="INET Asistencia")
    for app_label, model, codename, name in (
        ("auth", "group", "role_inet_asistencia", "INET Asistencia"),
        ("VAT", "centro", "view_centro", "Can view centro"),
        ("VAT", "curso", "view_curso", "Can view curso"),
        ("VAT", "comisioncurso", "view_comisioncurso", "Can view comision curso"),
    ):
        content_type, _ = content_type_model.objects.using(alias).get_or_create(
            app_label=app_label, model=model
        )
        permission, _ = permission_model.objects.using(alias).get_or_create(
            content_type=content_type, codename=codename, defaults={"name": name}
        )
        group.permissions.add(permission)


class Migration(migrations.Migration):
    dependencies = [("users", "0061_profile_inspecciones_escolares")]
    operations = [
        migrations.RunPython(crear_grupo_asistencia, migrations.RunPython.noop)
    ]
