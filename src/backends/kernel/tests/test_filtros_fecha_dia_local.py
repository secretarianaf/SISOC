"""Filtros por día sobre DateTimeField sin depender de las zonas horarias de MySQL (#2750).

En PRD ``CONVERT_TZ`` devuelve NULL porque MySQL no tiene las tablas de zonas
horarias, y ``campo__date`` filtraba todo a vacío sin error. Los datos de estos
tests caen a las 23:30 del 30/04 y a las 00:30 del 01/05, hora argentina: en UTC
los dos son el 01/05, así que solo un cálculo en hora local los separa.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from auditlog.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from audittrail.services.query_service import apply_filters
from ciudadanos.models import Ciudadano
from core.services.advanced_filters import AdvancedFilterEngine
from core.trash_views import _apply_deleted_date_range_filter
from core.utils import rango_del_dia_local

ARGENTINA = ZoneInfo("America/Argentina/Buenos_Aires")
NOCHE_30_ABRIL = datetime(2026, 4, 30, 23, 30, tzinfo=ARGENTINA)
MADRUGADA_1_MAYO = datetime(2026, 5, 1, 0, 30, tzinfo=ARGENTINA)

User = get_user_model()


def test_rango_del_dia_local_va_de_medianoche_a_medianoche_local():
    inicio, fin = rango_del_dia_local(date(2026, 4, 30))

    assert inicio == datetime(2026, 4, 30, 0, 0, tzinfo=ARGENTINA)
    assert fin == datetime(2026, 5, 1, 0, 0, tzinfo=ARGENTINA)
    assert timezone.is_aware(inicio) and timezone.is_aware(fin)


def _engine():
    return AdvancedFilterEngine(
        field_map={"alta": "date_joined__date"},
        field_types={"alta": "date"},
    )


@pytest.fixture
def usuarios_en_bordes():
    User.objects.create_user(username="noche", date_joined=NOCHE_30_ABRIL)
    User.objects.create_user(username="madrugada", date_joined=MADRUGADA_1_MAYO)


def _filtrar(op, valor):
    payload = {"filters": {"items": [{"field": "alta", "op": op, "value": valor}]}}
    return set(
        _engine()
        .filter_queryset(User.objects.all(), payload)
        .values_list("username", flat=True)
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("op", "valor", "esperados"),
    [
        ("eq", "2026-04-30", {"noche"}),
        ("eq", "2026-05-01", {"madrugada"}),
        ("ne", "2026-04-30", {"madrugada"}),
        ("gt", "2026-04-30", {"madrugada"}),
        ("lt", "2026-05-01", {"noche"}),
        ("gte", "2026-05-01", {"madrugada"}),
        ("lte", "2026-04-30", {"noche"}),
    ],
)
def test_engine_filtra_datetime_por_dia_local(usuarios_en_bordes, op, valor, esperados):
    assert _filtrar(op, valor) == esperados


def test_engine_vacio_sobre_datetime_no_usa_date():
    q = _engine().build_q({"filters": {"items": [{"field": "alta", "op": "empty"}]}})

    assert q.children == [("date_joined__isnull", True)]


@pytest.mark.django_db
@pytest.mark.mysql_compat
def test_engine_no_usa_convert_tz_en_mysql(usuarios_en_bordes):
    if connection.vendor != "mysql":
        pytest.skip("Requiere MySQL real.")

    with CaptureQueriesContext(connection) as queries:
        assert _filtrar("eq", "2026-04-30") == {"noche"}

    assert not [q for q in queries if "CONVERT_TZ" in q["sql"]]


@pytest.mark.django_db
def test_papelera_filtra_borrado_por_dia_local():
    for documento, borrado in (
        (30111001, NOCHE_30_ABRIL),
        (30111002, MADRUGADA_1_MAYO),
    ):
        ciudadano = Ciudadano.objects.create(
            apellido="Papelera",
            nombre=str(documento),
            tipo_documento=Ciudadano.DOCUMENTO_DNI,
            documento=documento,
        )
        Ciudadano.all_objects.filter(pk=ciudadano.pk).update(deleted_at=borrado)

    resultado = _apply_deleted_date_range_filter(
        Ciudadano.all_objects.filter(apellido="Papelera"),
        deleted_from=date(2026, 4, 30),
        deleted_to=date(2026, 4, 30),
    )

    assert list(resultado.values_list("documento", flat=True)) == [30111001]


@pytest.mark.django_db
def test_auditoria_fecha_desde_incluye_el_dia_local_completo():
    content_type = ContentType.objects.get_for_model(User)
    for pk, momento in (("1", NOCHE_30_ABRIL), ("2", MADRUGADA_1_MAYO)):
        entrada = LogEntry.objects.create(
            content_type=content_type,
            object_pk=pk,
            object_repr=pk,
            action=LogEntry.Action.UPDATE,
        )
        LogEntry.objects.filter(pk=entrada.pk).update(timestamp=momento)

    resultado = apply_filters(
        LogEntry.objects.filter(content_type=content_type),
        {"start_date": date(2026, 5, 1)},
    )

    assert list(resultado.values_list("object_pk", flat=True)) == ["2"]
