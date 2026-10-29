"""Upgrade/reversa de estado sobre la misma tabla, IDs y asignaciones."""

import importlib

import pytest
from django.apps import apps
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import override_settings

from audittrail.models import AuditoriaSesionPWA

PREVIOUS = [
    ("audittrail", "0001_squashed_0003"),
    ("pwa", "0026_inicializar_acceso_web"),
]
NEXT = [
    ("audittrail", "0002_auditoria_sesion_desde_pwa"),
    ("pwa", "0027_auditoria_sesion_a_kernel"),
]


def _migrate_auditoria(targets):
    """Ejecuta el traslado también sobre el esquema SQLite creado por syncdb.

    Esa DB no tiene historial: MigrationExecutor intentaría crear de nuevo
    todas sus tablas. Sólo en ese caso se aplican/revierten las operaciones
    reales del traslado con sus estados históricos, sin inventar registros.
    MySQL y las DB migradas conservan el recorrido completo del executor.
    """
    executor = MigrationExecutor(connection)
    if connection.vendor != "sqlite" or executor.loader.applied_migrations:
        executor.migrate(targets)
        return

    state = executor.loader.project_state(PREVIOUS)
    transitions = []
    for key in NEXT:
        migration = executor.loader.get_migration(*key)
        transitions.append((migration, state))
        state = migration.mutate_state(state)
    backwards = targets == PREVIOUS
    for migration, before in reversed(transitions) if backwards else transitions:
        with connection.schema_editor(atomic=False) as schema_editor:
            if backwards:
                migration.unapply(before.clone(), schema_editor)
            else:
                migration.apply(before.clone(), schema_editor)


@pytest.mark.django_db(transaction=True)
@override_settings(MIGRATION_MODULES={})
def test_upgrade_y_reversa_conservan_filas_permisos_y_asignaciones():
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    try:
        _migrate_auditoria(PREVIOUS)
        old_apps = executor.loader.project_state(PREVIOUS).apps
        old_model = old_apps.get_model("pwa", "AuditoriaSesionPWA")
        user = User.objects.create_user(username="migracion_auditoria")
        group = Group.objects.create(name="Auditoria trasladada")
        content_type = ContentType.objects.get(
            app_label="pwa", model="auditoriasesionpwa"
        )
        permissions = list(
            Permission.objects.filter(content_type=content_type).order_by("id")
        )
        assert len(permissions) == 4
        operational_permissions = list(
            Permission.objects.filter(
                content_type__app_label="pwa", codename__startswith="manage_"
            )
            .order_by("id")
            .values_list("id", "content_type_id", "codename")
        )
        ids = [permission.pk for permission in permissions]
        group.permissions.add(*permissions)
        user.user_permissions.add(*permissions)
        user.groups.add(group)
        event = old_model.objects.create(
            user_id=user.pk,
            evento="login_ok",
            resultado="ok",
            path="/api/users/login/",
            metodo_http="POST",
            rol_pwa_snapshot=["representante"],
            comedor_ids_snapshot=[17],
        )
        group_permission_ids = set(group.permissions.values_list("id", flat=True))
        user_permission_ids = set(user.user_permissions.values_list("id", flat=True))
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(
                cursor, "pwa_auditoriasesionpwa"
            )
        ct_id, event_id = content_type.pk, event.pk
        _migrate_auditoria(NEXT)
        content_type.refresh_from_db()
        assert content_type.pk == ct_id
        assert content_type.app_label == "audittrail"
        assert not ContentType.objects.filter(
            app_label="pwa", model="auditoriasesionpwa"
        ).exists()
        assert (
            list(
                Permission.objects.filter(content_type_id=ct_id)
                .order_by("id")
                .values_list("id", flat=True)
            )
            == ids
        )
        assert (
            set(user.user_permissions.values_list("id", flat=True))
            == user_permission_ids
        )
        assert (
            set(group.permissions.values_list("id", flat=True)) == group_permission_ids
        )
        saved = AuditoriaSesionPWA.objects.get(pk=event_id)
        with connection.cursor() as cursor:
            assert (
                connection.introspection.get_constraints(
                    cursor, "pwa_auditoriasesionpwa"
                )
                == constraints
            )
        assert (
            "audittrail_auditoriasesionpwa"
            not in connection.introspection.table_names()
        )
        assert saved.user_id == user.pk
        assert saved.comedor_ids_snapshot == [17]
        assert saved.rol_pwa_snapshot == ["representante"]
        user = User.objects.get(pk=user.pk)
        assert "audittrail.view_auditoriasesionpwa" in user.get_all_permissions()
        assert "pwa.view_auditoriasesionpwa" not in user.get_all_permissions()
        assert (
            list(
                Permission.objects.filter(
                    content_type__app_label="pwa", codename__startswith="manage_"
                )
                .order_by("id")
                .values_list("id", "content_type_id", "codename")
            )
            == operational_permissions
        )
        _migrate_auditoria(PREVIOUS)
        content_type.refresh_from_db()
        assert content_type.app_label == "pwa"
        assert content_type.pk == ct_id
        assert old_model.objects.get(pk=event_id).user_id == user.pk
        assert (
            list(
                Permission.objects.filter(content_type_id=ct_id)
                .order_by("id")
                .values_list("id", flat=True)
            )
            == ids
        )
        assert (
            set(group.permissions.values_list("id", flat=True)) == group_permission_ids
        )
    finally:
        _migrate_auditoria(latest)
        ContentType.objects.clear_cache()


@pytest.mark.django_db(transaction=True)
def test_dos_content_types_se_rechazan_sin_borrar_ni_fusionar():
    migration = importlib.import_module(
        "audittrail.migrations.0002_auditoria_sesion_desde_pwa"
    )
    current = ContentType.objects.get(
        app_label="audittrail", model="auditoriasesionpwa"
    )
    duplicate = ContentType.objects.create(app_label="pwa", model="auditoriasesionpwa")
    with connection.schema_editor(atomic=False) as schema_editor:
        with pytest.raises(RuntimeError, match="Existen ambos content types"):
            migration.forwards(apps, schema_editor)
    assert ContentType.objects.filter(pk__in=[current.pk, duplicate.pk]).count() == 2


def test_migraciones_de_traslado_no_contienen_ddl_de_tabla():
    destination = importlib.import_module(
        "audittrail.migrations.0002_auditoria_sesion_desde_pwa"
    )
    source = importlib.import_module("pwa.migrations.0027_auditoria_sesion_a_kernel")
    assert destination.Migration.operations[0].database_operations == []
    assert source.Migration.operations[0].database_operations == []
    assert AuditoriaSesionPWA._meta.db_table == "pwa_auditoriasesionpwa"


@pytest.mark.django_db
def test_enlaces_admin_antiguos_redirigen_y_no_reenvian_posts(client):
    user = User.objects.create_superuser(
        username="admin_auditoria_legacy", password="AuditoriaSegura123!"
    )
    client.force_login(user)
    response = client.get("/admin/pwa/auditoriasesionpwa/?evento=login_ok")
    assert response.status_code == 302
    assert (
        response["Location"] == "/admin/audittrail/auditoriasesionpwa/?evento=login_ok"
    )
    assert client.get(response["Location"]).status_code == 200
    assert (
        client.post(
            "/admin/pwa/auditoriasesionpwa/", {"action": "delete_selected"}
        ).status_code
        == 405
    )
