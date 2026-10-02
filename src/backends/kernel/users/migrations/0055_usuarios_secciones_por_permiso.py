"""Permisos por sección del ABM de usuarios.

Hasta ahora cualquiera con ``auth.add_user``/``auth.change_user`` veía todas las
secciones del formulario (Mobile Comedores, Territorial comedor, DataCalle,
equipos técnicos y administración de accesos), salvo los gestores CDI/SIMEPI,
que tenían una restricción fija en el formulario. Ahora cada sección tiene su
permiso ``auth.role_usuarios_seccion_*`` (ver ``users.secciones_usuario``).

Para no cambiar lo que ve cada perfil al desplegar, los grupos y usuarios que
hoy administran usuarios reciben todas las secciones, con dos excepciones:

- Grupos CDI/SIMEPI: ninguna, igual que su restricción anterior (que además no
  cubría Territorial comedor ni DataCalle; ahora quedan cerradas).
- Grupos DataCalle: sólo la sección DataCalle, que es la que administran.
"""

from django.db import migrations


SECCIONES = {
    "role_usuarios_seccion_mobile_comedores": (
        "Usuarios - Sección Acceso SISOC Mobile (Comedores)"
    ),
    "role_usuarios_seccion_territorial_comedor": (
        "Usuarios - Sección Mobile Territorial comedor"
    ),
    "role_usuarios_seccion_equipos_tecnicos": (
        "Usuarios - Sección Equipos técnicos (Comedores)"
    ),
    "role_usuarios_seccion_datacalle": (
        "Usuarios - Sección Acceso SISOC Mobile DataCalle"
    ),
    "role_usuarios_seccion_administracion": (
        "Usuarios - Sección Administración de accesos"
    ),
}

GRUPOS_SIN_SECCIONES = (
    "SIMEPI - Administrador",
    "SIMEPI - Equipo Nacional",
    "SIMEPI - EGP",
    "CDI - Referente centro",
)

GRUPOS_DATACALLE = ("Coordinador DataCalle", "Administrador DataCalle")
PERMISOS_ABM_USUARIOS = ("add_user", "change_user")


def _crear_permisos(apps):
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    group_ct, _ = ContentType.objects.get_or_create(app_label="auth", model="group")
    permisos = {}
    for codename, nombre in SECCIONES.items():
        permiso, _ = Permission.objects.get_or_create(
            content_type=group_ct,
            codename=codename,
            defaults={"name": nombre},
        )
        permisos[codename] = permiso
    return permisos


def asignar(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    User = apps.get_model("auth", "User")
    permisos = _crear_permisos(apps)
    todas = list(permisos.values())
    solo_datacalle = [permisos["role_usuarios_seccion_datacalle"]]

    filtro_abm = {
        "permissions__content_type__app_label": "auth",
        "permissions__codename__in": PERMISOS_ABM_USUARIOS,
    }
    for grupo in Group.objects.filter(**filtro_abm).distinct():
        if grupo.name in GRUPOS_SIN_SECCIONES:
            continue
        if grupo.name in GRUPOS_DATACALLE:
            grupo.permissions.add(*solo_datacalle)
            continue
        grupo.permissions.add(*todas)

    usuarios_directos = (
        User.objects.filter(
            is_superuser=False,
            user_permissions__content_type__app_label="auth",
            user_permissions__codename__in=PERMISOS_ABM_USUARIOS,
        )
        .exclude(groups__name__in=(*GRUPOS_SIN_SECCIONES, *GRUPOS_DATACALLE))
        .distinct()
    )
    for usuario in usuarios_directos:
        usuario.user_permissions.add(*todas)


def desasignar(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    Permission.objects.filter(
        content_type__app_label="auth",
        codename__in=tuple(SECCIONES),
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0054_relevador_calle_provincia_unica"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(asignar, desasignar),
    ]
