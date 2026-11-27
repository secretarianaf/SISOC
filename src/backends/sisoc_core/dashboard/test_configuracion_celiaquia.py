"""Compatibilidad de la migración para políticas de tableros internos."""

from importlib import import_module

import pytest
from django.apps import apps
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.state import ProjectState
from django.db.models import CheckConstraint, Q


@pytest.mark.django_db(transaction=True)
def test_reversion_rechaza_celiaquia_sin_perder_la_restriccion():
    from dashboard.models import ConfiguracionTableroInterno, Tablero

    tablero = Tablero.objects.create(nombre="Celiaquía", slug="celiaquia-rollback")
    config = ConfiguracionTableroInterno.objects.create(
        codigo="celiaquia", tablero=tablero, activa=False
    )
    migracion = import_module(
        "dashboard.migrations.0009_celiaquia_configuracion"
    ).Migration("0009_celiaquia_configuracion", "dashboard")
    estado_anterior = ProjectState.from_apps(apps)
    estado_anterior.remove_constraint(
        "dashboard", "configuraciontablerointerno", "dashboard_interno_codigo_valido"
    )
    estado_anterior.add_constraint(
        "dashboard",
        "configuraciontablerointerno",
        CheckConstraint(
            condition=Q(codigo="progresar_curso"),
            name="dashboard_interno_codigo_valido",
        ),
    )
    with pytest.raises((RuntimeError, IntegrityError)):
        with connection.schema_editor() as editor:
            migracion.unapply(estado_anterior, editor)
    assert ConfiguracionTableroInterno.objects.filter(pk=config.pk).exists()
    otro = Tablero.objects.create(nombre="Otro", slug="otro-rollback")
    with pytest.raises(IntegrityError), transaction.atomic():
        ConfiguracionTableroInterno.objects.create(codigo="otro", tablero=otro)


@pytest.mark.django_db(transaction=True)
def test_operaciones_de_migracion_preservan_configuracion_legacy():
    migracion = import_module(
        "dashboard.migrations.0009_celiaquia_configuracion"
    ).Migration("0009_celiaquia_configuracion", "dashboard")
    estado_anterior = ProjectState.from_apps(apps)
    estado_anterior.remove_constraint(
        "dashboard", "configuraciontablerointerno", "dashboard_interno_codigo_valido"
    )
    estado_anterior.add_constraint(
        "dashboard",
        "configuraciontablerointerno",
        CheckConstraint(
            condition=Q(codigo="progresar_curso"),
            name="dashboard_interno_codigo_valido",
        ),
    )
    with connection.schema_editor() as editor:
        migracion.unapply(estado_anterior, editor)
    modelo_tablero = estado_anterior.apps.get_model("dashboard", "Tablero")
    modelo_config = estado_anterior.apps.get_model(
        "dashboard", "ConfiguracionTableroInterno"
    )
    tablero = modelo_tablero.objects.create(nombre="Progresar", slug="progresar")
    legacy = modelo_config.objects.create(
        codigo="progresar_curso", tablero_id=tablero.pk, activa=True
    )
    try:
        with connection.schema_editor() as editor:
            estado_nuevo = migracion.apply(estado_anterior, editor)
        modelo_tablero = estado_nuevo.apps.get_model("dashboard", "Tablero")
        modelo_config = estado_nuevo.apps.get_model(
            "dashboard", "ConfiguracionTableroInterno"
        )
        assert modelo_config.objects.get(pk=legacy.pk).activa is True
        tablero_celiaquia = modelo_tablero.objects.create(
            nombre="Celiaquía", slug="celiaquia"
        )
        celiaquia = modelo_config.objects.create(
            codigo="celiaquia", tablero_id=tablero_celiaquia.pk
        )
        assert celiaquia.activa is False
        otro = modelo_tablero.objects.create(nombre="Otro", slug="otro")
        with pytest.raises(IntegrityError), transaction.atomic():
            modelo_config.objects.create(codigo="otro", tablero_id=otro.pk)
        celiaquia.delete()
        with connection.schema_editor() as editor:
            migracion.unapply(estado_anterior, editor)
        assert modelo_config.objects.get(pk=legacy.pk).activa is True
    finally:
        with connection.schema_editor() as editor:
            migracion.apply(estado_anterior, editor)


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(
    not connection.settings_dict["TEST"].get("MIGRATE", True),
    reason="La prueba requiere una base creada con migraciones reales.",
)
def test_migracion_conserva_progresar_y_admite_celiaquia_sin_activarla():
    origen = [("dashboard", "0008_tablero_visible_menu_alter_tablero_activo")]
    destino = [("dashboard", "0009_celiaquia_configuracion")]
    executor = MigrationExecutor(connection)
    executor.migrate(origen)
    anteriores = executor.loader.project_state(origen).apps
    tablero_modelo = anteriores.get_model("dashboard", "Tablero")
    config_modelo = anteriores.get_model("dashboard", "ConfiguracionTableroInterno")
    tablero = tablero_modelo.objects.create(nombre="Progresar", slug="progresar")
    configuracion = config_modelo.objects.create(
        codigo="progresar_curso", tablero_id=tablero.pk, activa=True
    )
    try:
        executor = MigrationExecutor(connection)
        executor.migrate(destino)
        nuevos = executor.loader.project_state(destino).apps
        tablero_modelo = nuevos.get_model("dashboard", "Tablero")
        config_modelo = nuevos.get_model("dashboard", "ConfiguracionTableroInterno")
        assert config_modelo.objects.get(pk=configuracion.pk).activa is True
        celiaquia = tablero_modelo.objects.create(nombre="Celiaquía", slug="celiaquia")
        nueva = config_modelo.objects.create(
            codigo="celiaquia", tablero_id=celiaquia.pk
        )
        assert nueva.activa is False
        otro = tablero_modelo.objects.create(nombre="Otro", slug="otro")
        with pytest.raises(IntegrityError), transaction.atomic():
            config_modelo.objects.create(codigo="otro", tablero_id=otro.pk)
        nueva.delete()
        executor = MigrationExecutor(connection)
        executor.migrate(origen)
        anteriores = executor.loader.project_state(origen).apps
        anterior = anteriores.get_model("dashboard", "ConfiguracionTableroInterno")
        assert anterior.objects.get(pk=configuracion.pk).activa is True
    finally:
        MigrationExecutor(connection).migrate(destino)
