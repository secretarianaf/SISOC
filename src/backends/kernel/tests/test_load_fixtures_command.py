"""Tests de regresión para el comando load_fixtures."""

import json
from argparse import ArgumentParser
from io import StringIO

import pytest
from django.apps import apps
from django.db import transaction
from django.db.models.signals import post_save
from unittest.mock import patch

from core.management.commands.load_fixtures import Command

pytestmark = pytest.mark.django_db


def test_upsert_fixture_reintenta_fk_hijo_antes_de_padre(tmp_path):
    """Debe guardar ambos registros aunque el hijo aparezca antes que el padre."""
    tipo_pk = 99001
    sub_pk = 99002
    fixture_path = tmp_path / "intervenciones_desordenadas.json"
    fixture_data = [
        {
            "model": "catalogo_intervenciones.subintervencion",
            "pk": sub_pk,
            "fields": {
                "nombre": "Sub intervención de prueba",
                "tipo_intervencion": tipo_pk,
            },
        },
        {
            "model": "catalogo_intervenciones.tipointervencion",
            "pk": tipo_pk,
            "fields": {"nombre": "Tipo intervención de prueba", "programa": "cdi"},
        },
    ]

    fixture_path.write_text(
        json.dumps(fixture_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    Command().upsert_fixture(str(fixture_path))

    tipo_model = apps.get_model("catalogo_intervenciones", "TipoIntervencion")
    sub_model = apps.get_model("catalogo_intervenciones", "SubIntervencion")
    tipo = tipo_model.objects.get(pk=tipo_pk)
    sub = sub_model.objects.get(pk=sub_pk)

    assert sub.tipo_intervencion_id == tipo.pk


def test_handle_sincroniza_catalogo_cdi_despues_de_cargar():
    command = Command()

    with (
        patch.object(command, "load_fixtures") as load_mock,
        patch(
            "core.management.commands.load_fixtures.ejecutar_fixture_post_load_handlers",
            return_value=("✅ Catálogo de intervenciones sincronizado",),
        ) as handlers_mock,
        patch(
            "core.management.commands.load_fixtures.sync_territorio_desde_fixture",
            return_value={
                "provincias_creadas": 0,
                "municipios_creadas": 0,
                "localidades_creadas": 0,
                "saltadas_por_integridad": 0,
            },
        ) as territorio_mock,
    ):
        command.handle(force=False)

    load_mock.assert_called_once_with()
    handlers_mock.assert_called_once_with()
    territorio_mock.assert_called_once_with()


def test_add_arguments_reconoce_overwrite():
    parser = ArgumentParser()
    Command().add_arguments(parser)

    options = parser.parse_args(["--overwrite"])

    assert options.force is True


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("force", [False, True])
def test_load_fixtures_reintenta_fk_entre_archivos_sin_repetir_exitos(
    tmp_path, monkeypatch, force
):
    """Una carga resuelve la cadena inversa, incluso con un archivo parcial."""
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    entries = {
        "a_localidades.json": [
            {
                "model": "core.localidad",
                "pk": 99003,
                "fields": {"nombre": "Pendiente", "municipio": 99002},
            },
            {
                "model": "core.localidad",
                "pk": 99004,
                "fields": {"nombre": "Independiente", "municipio": None},
            },
        ],
        "b_municipios.json": [
            {
                "model": "core.municipio",
                "pk": 99002,
                "fields": {"nombre": "Municipio sintético", "provincia": 99001},
            }
        ],
        "c_provincias.json": [
            {
                "model": "core.provincia",
                "pk": 99001,
                "fields": {"nombre": "Provincia sintética"},
            }
        ],
    }
    for name, data in entries.items():
        (fixtures / name).write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    localidad = apps.get_model("core", "Localidad")
    saved = []

    def track_save(sender, instance, **kwargs):
        transaction.on_commit(lambda pk=instance.pk: saved.append(pk))

    post_save.connect(track_save, sender=localidad)
    errors = StringIO()
    command = Command(stdout=StringIO(), stderr=errors)
    command.force = force
    try:
        command.load_fixtures()
    finally:
        post_save.disconnect(track_save, sender=localidad)

    assert localidad.objects.get(pk=99003).municipio.provincia_id == 99001
    assert localidad.objects.get(pk=99004).municipio_id is None
    assert sorted(saved) == [99003, 99004]
    assert errors.getvalue() == ""


@pytest.mark.django_db(transaction=True)
def test_load_fixtures_reporta_fk_irresoluble_y_conserva_exitos(tmp_path, monkeypatch):
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "parcial.json").write_text(
        json.dumps(
            [
                {
                    "model": "core.municipio",
                    "pk": 99002,
                    "fields": {"nombre": "Sin padre", "provincia": 99001},
                },
                {
                    "model": "core.localidad",
                    "pk": 99004,
                    "fields": {"nombre": "Independiente", "municipio": None},
                },
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    errors = StringIO()
    command = Command(stdout=StringIO(), stderr=errors)
    command.force = False

    command.load_fixtures()

    assert not apps.get_model("core", "Municipio").objects.filter(pk=99002).exists()
    assert apps.get_model("core", "Localidad").objects.filter(pk=99004).exists()
    assert errors.getvalue().count("Falló guardar registro") == 1
    assert "core.municipio(pk=99002)" in errors.getvalue()


@pytest.mark.parametrize("force", [False, True])
def test_load_fixtures_conserva_criterio_de_tabla_ocupada(tmp_path, monkeypatch, force):
    provincia = apps.get_model("core", "Provincia")
    provincia.objects.create(pk=99001, nombre="Nombre orgánico")
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "provincia.json").write_text(
        json.dumps(
            [
                {
                    "model": "core.provincia",
                    "pk": 99001,
                    "fields": {"nombre": "Nombre de fixture"},
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    command = Command(stdout=StringIO(), stderr=StringIO())
    command.force = force

    command.load_fixtures()

    expected = "Nombre de fixture" if force else "Nombre orgánico"
    assert provincia.objects.get(pk=99001).nombre == expected
