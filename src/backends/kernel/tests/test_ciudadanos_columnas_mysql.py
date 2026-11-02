"""Columnas de ciudadanos alineadas con el modelo en MySQL real (#2750)."""

import pytest
from django.db import connection

from ciudadanos.models import Ciudadano, GrupoFamiliar

pytestmark = [pytest.mark.django_db, pytest.mark.mysql_compat]


def _tipo_columna(tabla, columna):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT column_type FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = %s "
            "AND column_name = %s",
            [tabla, columna],
        )
        return cursor.fetchone()[0].lower()


@pytest.fixture(autouse=True)
def _solo_mysql():
    if connection.vendor != "mysql":
        pytest.skip("Requiere MySQL real.")


@pytest.mark.parametrize(
    ("modelo", "columna", "tipo"),
    [
        (Ciudadano, "altura", "varchar(10)"),
        (Ciudadano, "codigo_postal", "varchar(12)"),
        (Ciudadano, "observaciones", "longtext"),
        (GrupoFamiliar, "observaciones", "longtext"),
    ],
)
def test_columnas_de_ciudadanos_coinciden_con_el_modelo(modelo, columna, tipo):
    assert _tipo_columna(modelo._meta.db_table, columna) == tipo


def test_ciudadano_guarda_codigo_postal_alfanumerico_y_altura_con_texto():
    ciudadano = Ciudadano.objects.create(
        apellido="Prueba",
        nombre="Columnas",
        tipo_documento=Ciudadano.DOCUMENTO_DNI,
        documento=30111222,
        codigo_postal="B1636ABC",
        altura="c 14",
        observaciones="x" * 600,
    )

    ciudadano.refresh_from_db()
    assert ciudadano.codigo_postal == "B1636ABC"
    assert ciudadano.altura == "c 14"
    assert len(ciudadano.observaciones) == 600
