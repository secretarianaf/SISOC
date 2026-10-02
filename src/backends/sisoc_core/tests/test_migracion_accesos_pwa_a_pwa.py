"""Migración de los accesos PWA de ``users`` (kernel) a ``pwa`` (core).

Simula el estado de QA/PRD: los content types ``users.*`` existen y tienen
permisos asignados a grupos. Después de migrar, los mismos registros deben
apuntar a ``pwa`` sin perder permisos.
"""

import importlib

import pytest
from django.apps import apps as django_apps
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

migracion = importlib.import_module("pwa.migrations.0025_accesos_pwa_desde_users")


def _estado_previo():
    """Content types como antes de la migración: en ``users``."""
    ContentType.objects.filter(app_label="pwa", model__in=migracion.MODELOS).delete()
    content_type = ContentType.objects.create(
        app_label="users", model="accesocomedorpwa"
    )
    permiso = Permission.objects.create(
        content_type=content_type,
        codename="view_accesocomedorpwa",
        name="Can view acceso pwa",
    )
    grupo = Group.objects.create(name="Grupo con permiso PWA")
    grupo.permissions.add(permiso)
    return content_type, permiso, grupo


@pytest.mark.django_db
def test_content_types_pasan_a_pwa_conservando_permisos_de_grupos():
    content_type, permiso, grupo = _estado_previo()

    migracion.content_types_a_pwa(django_apps, None)

    content_type.refresh_from_db()
    assert content_type.app_label == "pwa"
    assert grupo.permissions.get(pk=permiso.pk).content_type_id == content_type.pk
    assert not ContentType.objects.filter(
        app_label="users", model__in=migracion.MODELOS
    ).exists()


@pytest.mark.django_db
def test_la_reversa_devuelve_los_content_types_a_users():
    content_type, _, _ = _estado_previo()
    migracion.content_types_a_pwa(django_apps, None)

    migracion.content_types_a_users(django_apps, None)

    content_type.refresh_from_db()
    assert content_type.app_label == "users"


@pytest.mark.django_db
def test_falla_si_existen_content_types_en_ambas_apps():
    _estado_previo()
    ContentType.objects.create(app_label="pwa", model="accesocomedorpwa")

    with pytest.raises(RuntimeError, match="resolver a mano"):
        migracion.content_types_a_pwa(django_apps, None)


def test_los_modelos_conservan_sus_tablas_de_users():
    tablas = {
        "AccesoComedorPWA": "users_accesocomedorpwa",
        "AccesoOrganizacionPWA": "users_accesoorganizacionpwa",
        "AuditAccesoComedorPWA": "users_auditaccesocomedorpwa",
        "CoordinadorEquipoTecnicoPWA": "users_coordinadorequipotecnicopwa",
    }
    for modelo, tabla in tablas.items():
        assert django_apps.get_model("pwa", modelo)._meta.db_table == tabla

    coordinador = django_apps.get_model("pwa", "CoordinadorEquipoTecnicoPWA")
    assert (
        coordinador._meta.get_field("duplas").remote_field.through._meta.db_table
        == "users_coordinadorequipotecnicopwa_duplas"
    )
