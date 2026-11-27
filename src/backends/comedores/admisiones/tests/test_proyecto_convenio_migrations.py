"""El proyecto de convenio continúa la cadena de migraciones de admisiones."""

from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.apps import apps
from django.db import connection, migrations
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder

from admisiones.models.admisiones import Admision, FormularioProyectoDeConvenio
from comedores.models import Comedor


def test_proyecto_convenio_continua_la_migracion_de_variables():
    loader = MigrationLoader(None)

    assert "admisiones" not in loader.detect_conflicts()
    proyecto = loader.graph.node_map[("admisiones", "0085_proyecto_convenio")]
    assert ("admisiones", "0084_variables_if_ultimo_informe_tecnico") in {
        padre.key for padre in proyecto.parents
    }


def test_guardia_cubre_todas_las_columnas_agregadas():
    migracion = import_module("admisiones.migrations.0085_proyecto_convenio")
    columnas = set()
    for operacion in migracion.Migration.operations:
        if isinstance(operacion, migrations.AddField):
            campo = operacion.field.clone()
            campo.set_attributes_from_name(operacion.name)
            columnas.add(campo.column)
    assert columnas == migracion.COLUMNAS_PROYECTO


@pytest.mark.django_db(transaction=True)
def test_migracion_anterior_aplicada_detiene_ddl_y_preserva_datos():
    comedor = Comedor.objects.create(nombre="Comedor sintético")
    admision = Admision.objects.create(comedor=comedor, tipo="incorporacion")
    proyecto = FormularioProyectoDeConvenio.objects.create(
        admision=admision,
        autoridad_nombre="Autoridad sintética",
        autoridad_cargo="Cargo sintético",
        cantidad_espacios="hasta_5",
        memo="Memo sintético",
        archivo="sintetico.pdf",
    )
    MigrationRecorder(connection).record_applied("admisiones", "0084_proyecto_convenio")
    migracion = import_module("admisiones.migrations.0085_proyecto_convenio")
    assert (
        migracion.Migration.operations[0].code is migracion.verificar_migracion_anterior
    )

    with pytest.raises(RuntimeError, match="0084_proyecto_convenio"):
        migracion.verificar_migracion_anterior(
            None, SimpleNamespace(connection=connection)
        )

    proyecto.refresh_from_db()
    assert proyecto.autoridad_nombre == "Autoridad sintética"
    assert proyecto.autoridad_cargo == "Cargo sintético"
    assert proyecto.cantidad_espacios == "hasta_5"
    assert proyecto.memo == "Memo sintético"
    MigrationRecorder(connection).record_unapplied(
        "admisiones", "0084_proyecto_convenio"
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("columna_existente", ["autoridad_nombre", "Autoridad_Nombre"])
def test_columnas_previas_sin_registro_detienen_la_migracion(columna_existente):
    comedor = Comedor.objects.create(nombre="Comedor sintético parcial")
    admision = Admision.objects.create(comedor=comedor, tipo="incorporacion")
    proyecto = FormularioProyectoDeConvenio.objects.create(
        admision=admision, autoridad_nombre="Dato sintético", archivo="sintetico.pdf"
    )
    migracion = import_module("admisiones.migrations.0085_proyecto_convenio")
    descripcion = [SimpleNamespace(name=columna_existente)]

    with patch.object(
        connection.introspection, "get_table_description", return_value=descripcion
    ):
        with pytest.raises(RuntimeError, match=columna_existente):
            migracion.verificar_migracion_anterior(
                apps, SimpleNamespace(connection=connection)
            )

    proyecto.refresh_from_db()
    assert proyecto.autoridad_nombre == "Dato sintético"


@pytest.mark.django_db
def test_esquema_sin_columnas_nuevas_puede_continuar():
    migracion = import_module("admisiones.migrations.0085_proyecto_convenio")
    descripcion = [SimpleNamespace(name="id")]

    with patch.object(
        connection.introspection, "get_table_description", return_value=descripcion
    ):
        migracion.verificar_migracion_anterior(
            apps, SimpleNamespace(connection=connection)
        )
