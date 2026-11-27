"""Modelo de la Encuesta de satisfacción de CDI (210SatisfaccionCDI).

Restricciones de dominio, inmutabilidad en la aplicación y el contrato con el
área. Los triggers de MySQL y la vista ``v_210SatisfaccionCDI_descarga`` se
prueban al final, solo contra MySQL real (``mysql_compat``).
"""

from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth.models import User
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.utils import timezone

from centrodeinfancia.encuesta_satisfaccion_schema import (
    CAMPOS_PREGUNTAS,
    PREGUNTAS,
    SALA_DESDE_NOMINA,
    Escala,
    EstadoRegistro,
    MotivoRechazo,
    Sala,
    SalaOrigen,
)
from centrodeinfancia.forms import NOMINA_SALA_CHOICES
from centrodeinfancia.models import (
    CentroDeInfancia,
    EncuestaSatisfaccionRechazo,
    EncuestaSatisfaccionRespuesta,
    EncuestaSatisfaccionToken,
)
from centrodeinfancia.models_encuesta_satisfaccion import RespuestaInmutableError

pytestmark = pytest.mark.django_db

TABLA = EncuestaSatisfaccionRespuesta._meta.db_table
VISTA = "v_210SatisfaccionCDI_descarga"


@pytest.fixture
def centro():
    return CentroDeInfancia.objects.create(nombre="CDI Los Horneritos")


def _token():
    ahora = timezone.now()
    return EncuestaSatisfaccionToken.objects.create(
        token_hash=uuid4().hex * 2,
        emitido_en=ahora,
        expira_en=ahora + timedelta(minutes=60),
        canal_ingreso=1,
    )


def _respuesta(centro, token=None, **cambios):
    ahora = timezone.now()
    datos = {
        "version_instrumento": "1.0",
        "canal_ingreso": 1,
        "centro": centro,
        "jurisdiccion": "Salta",
        "departamento": "Capital",
        "institucion": centro.nombre,
        "codigo_institucion": "CDI-000001",
        "sala": Sala.DOS_ANOS,
        "sala_origen": SalaOrigen.NOMINA,
        "fecha_carga": ahora,
        "ts_inicio": ahora - timedelta(minutes=5),
        "ts_envio": ahora,
        "duracion_seg": 300,
        "token": token or _token(),
        "ip_hash": "f" * 64,
        "captcha_proveedor": "turnstile",
        "dispositivo_tipo": 1,
        "app_version": "1.0.0",
        "hash_integridad": "0" * 64,
        **{campo: Escala.SIEMPRE for campo in CAMPOS_PREGUNTAS},
    }
    datos.update(cambios)
    return EncuestaSatisfaccionRespuesta.objects.create(**datos)


def _rechaza_la_base(crear):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            crear()


# --------------------------------------------------------------- contrato


def test_las_15_preguntas_son_columnas_del_modelo_en_orden():
    campos = [f.name for f in EncuestaSatisfaccionRespuesta._meta.get_fields()]
    assert [c for c in campos if c in CAMPOS_PREGUNTAS] == list(CAMPOS_PREGUNTAS)
    assert [codigo for codigo, *_ in PREGUNTAS] == [f"P{n:02d}" for n in range(1, 16)]
    assert [campo for _, campo, _, _, admite in PREGUNTAS if admite] == [
        "p13_alimentacion"
    ]


def test_cada_sala_de_la_nomina_tiene_su_codigo_en_la_encuesta():
    """Las claves del formulario de nómina son las que hay en producción."""
    assert set(SALA_DESDE_NOMINA) == {clave for clave, _ in NOMINA_SALA_CHOICES}
    assert set(SALA_DESDE_NOMINA.values()) == set(Sala)


def test_p13_usa_la_etiqueta_aprobada_por_el_area():
    assert Escala(9).label == "No brinda alimentación"


# --------------------------------------------------------------- dominio


def test_respuesta_valida_se_guarda_con_comprobante_de_8_caracteres(centro):
    respuesta = _respuesta(centro)

    respuesta.refresh_from_db()
    assert respuesta.estado_registro == EstadoRegistro.VALIDO
    assert len(respuesta.comprobante) == 8
    assert respuesta.comprobante == respuesta.uuid_respuesta.hex[:8]
    assert centro.encuestas_satisfaccion.get() == respuesta


def test_p13_admite_no_brinda_alimentacion(centro):
    respuesta = _respuesta(centro, p13_alimentacion=Escala.NO_BRINDA_ALIMENTACION)

    respuesta.refresh_from_db()
    assert respuesta.p13_alimentacion == 9


@pytest.mark.parametrize(
    "cambios",
    [
        {"p12_limpieza_orden": 9},
        {"p01_informacion_avances": 6},
        {"p15_horario_adecuado": 0},
        {"sala": 7},
        {"sala_origen": 3},
        {"canal_ingreso": 5},
        {"dispositivo_tipo": 4},
        {"estado_registro": 3},
        {"captcha_score": Decimal("1.5")},
    ],
    ids=lambda cambios: next(iter(cambios)),
)
def test_la_base_rechaza_valores_fuera_de_dominio(centro, cambios):
    _rechaza_la_base(lambda: _respuesta(centro, **cambios))

    assert not EncuestaSatisfaccionRespuesta.objects.exists()


def test_la_base_rechaza_envio_anterior_a_la_apertura(centro):
    ahora = timezone.now()

    _rechaza_la_base(
        lambda: _respuesta(centro, ts_inicio=ahora, ts_envio=ahora - timedelta(1))
    )


def test_la_base_rechaza_una_anulacion_sin_motivo(centro):
    _rechaza_la_base(lambda: _respuesta(centro, estado_registro=EstadoRegistro.ANULADO))


def test_un_token_registra_una_sola_respuesta(centro):
    token = _token()
    _respuesta(centro, token=token)

    _rechaza_la_base(lambda: _respuesta(centro, token=token))
    assert EncuestaSatisfaccionRespuesta.objects.count() == 1


def test_token_y_rechazo_validan_sus_codigos():
    ahora = timezone.now()
    _rechaza_la_base(
        lambda: EncuestaSatisfaccionToken.objects.create(
            token_hash="b" * 64, emitido_en=ahora, expira_en=ahora, canal_ingreso=3
        )
    )
    _rechaza_la_base(
        lambda: EncuestaSatisfaccionRechazo.objects.create(ts=ahora, motivo=6)
    )

    rechazo = EncuestaSatisfaccionRechazo.objects.create(
        ts=ahora, motivo=MotivoRechazo.CDI_NO_DISPONIBLE, cdi_id=99999
    )
    assert rechazo.get_motivo_display() == "CDI inexistente o dado de baja"


# --------------------------------------------------------------- inmutabilidad


def test_no_se_puede_editar_el_contenido_con_save(centro):
    respuesta = _respuesta(centro)
    respuesta.p01_informacion_avances = Escala.NUNCA

    with pytest.raises(RespuestaInmutableError):
        respuesta.save()
    with pytest.raises(RespuestaInmutableError):
        respuesta.save(update_fields=["p01_informacion_avances"])

    respuesta.refresh_from_db()
    assert respuesta.p01_informacion_avances == Escala.SIEMPRE


def test_no_se_puede_editar_el_contenido_con_update(centro):
    _respuesta(centro)

    with pytest.raises(RespuestaInmutableError):
        EncuestaSatisfaccionRespuesta.objects.update(comentarios="otro texto")
    with pytest.raises(RespuestaInmutableError):
        EncuestaSatisfaccionRespuesta.objects.update(ip_hash="e" * 64)

    assert EncuestaSatisfaccionRespuesta.objects.get().comentarios is None


def test_no_se_puede_borrar_una_respuesta(centro):
    respuesta = _respuesta(centro)

    with pytest.raises(RespuestaInmutableError):
        respuesta.delete()
    with pytest.raises(RespuestaInmutableError):
        EncuestaSatisfaccionRespuesta.objects.all().delete()

    assert EncuestaSatisfaccionRespuesta.objects.filter(pk=respuesta.pk).exists()


def test_la_purga_de_ip_hash_esta_permitida(centro):
    respuesta = _respuesta(centro)
    antes = EncuestaSatisfaccionRespuesta.objects.get().updated_at

    filas = EncuestaSatisfaccionRespuesta.objects.filter(pk=respuesta.pk).update(
        ip_hash=None
    )

    respuesta.refresh_from_db()
    assert filas == 1
    assert respuesta.ip_hash is None
    assert respuesta.updated_at >= antes


def test_save_solo_purga_ip_hash_no_lo_reescribe(centro):
    respuesta = _respuesta(centro)
    respuesta.ip_hash = "e" * 64

    with pytest.raises(RespuestaInmutableError):
        respuesta.save(update_fields=["ip_hash"])

    respuesta.ip_hash = None
    respuesta.save(update_fields=["ip_hash"])
    respuesta.refresh_from_db()
    assert respuesta.ip_hash is None


def test_la_anulacion_logica_con_motivo_se_guarda(centro):
    respuesta = _respuesta(centro)
    auditor = User.objects.create_user(username="auditoria")
    respuesta.estado_registro = EstadoRegistro.ANULADO
    respuesta.motivo_anulacion = "Respuesta de prueba"
    respuesta.anulado_por = auditor
    respuesta.fecha_anulacion = timezone.now()

    respuesta.save(
        update_fields=[
            "estado_registro",
            "motivo_anulacion",
            "anulado_por",
            "fecha_anulacion",
        ]
    )

    respuesta.refresh_from_db()
    assert respuesta.estado_registro == EstadoRegistro.ANULADO
    assert respuesta.anulado_por == auditor


# --------------------------------------------------------------- MySQL real


def _sql(sentencia, parametros=()):
    with connection.cursor() as cursor:
        cursor.execute(sentencia, parametros)
        return cursor.rowcount


def _rechaza_el_trigger(sentencia, parametros=()):
    with pytest.raises(DatabaseError) as error:
        with transaction.atomic():
            _sql(sentencia, parametros)
    return str(error.value)


@pytest.mark.mysql_compat
def test_mysql_los_triggers_impiden_editar_y_borrar_respuestas(centro):
    if connection.vendor != "mysql":
        pytest.skip("Los triggers existen solo en MySQL.")
    respuesta = _respuesta(centro)

    mensaje = _rechaza_el_trigger(
        f"UPDATE `{TABLA}` SET p01_informacion_avances = 1 WHERE id = %s",
        [respuesta.pk],
    )
    assert "no puede modificarse" in mensaje
    assert "no se eliminan" in _rechaza_el_trigger(
        f"DELETE FROM `{TABLA}` WHERE id = %s", [respuesta.pk]
    )
    assert "solo puede purgarse" in _rechaza_el_trigger(
        f"UPDATE `{TABLA}` SET ip_hash = REPEAT('e', 64) WHERE id = %s",
        [respuesta.pk],
    )

    assert _sql(f"UPDATE `{TABLA}` SET ip_hash = NULL WHERE id = %s", [respuesta.pk])
    respuesta.refresh_from_db()
    assert respuesta.p01_informacion_avances == Escala.SIEMPRE
    assert respuesta.ip_hash is None


@pytest.mark.mysql_compat
def test_mysql_una_anulacion_no_se_revierte_ni_se_edita(centro):
    if connection.vendor != "mysql":
        pytest.skip("Los triggers existen solo en MySQL.")
    respuesta = _respuesta(centro)
    auditor = User.objects.create_user(username="auditoria")
    _sql(
        f"UPDATE `{TABLA}` SET estado_registro = 2, motivo_anulacion = 'Prueba', "
        "anulado_por_id = %s, fecha_anulacion = NOW() WHERE id = %s",
        [auditor.pk, respuesta.pk],
    )

    assert "no puede revertirse" in _rechaza_el_trigger(
        f"UPDATE `{TABLA}` SET estado_registro = 1, motivo_anulacion = NULL, "
        "anulado_por_id = NULL, fecha_anulacion = NULL WHERE id = %s",
        [respuesta.pk],
    )
    assert "no puede revertirse" in _rechaza_el_trigger(
        f"UPDATE `{TABLA}` SET motivo_anulacion = 'Otro' WHERE id = %s",
        [respuesta.pk],
    )
    respuesta.refresh_from_db()
    assert respuesta.motivo_anulacion == "Prueba"


@pytest.mark.mysql_compat
def test_mysql_la_vista_del_area_trae_etiquetas_sin_datos_tecnicos(centro):
    if connection.vendor != "mysql":
        pytest.skip("La vista existe solo en MySQL.")
    carga = datetime(2026, 11, 27, 15, 0, tzinfo=dt_timezone.utc)
    respuesta = _respuesta(
        centro,
        fecha_carga=carga,
        ts_inicio=carga - timedelta(minutes=4),
        ts_envio=carga,
        sala=Sala.MULTIEDAD,
        sala_origen=SalaOrigen.LISTA_COMPLETA,
        p13_alimentacion=Escala.NO_BRINDA_ALIMENTACION,
        comentarios="Muy contentos.",
    )

    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT * FROM `{VISTA}` WHERE id_respuesta = %s", [respuesta.pk]
        )
        columnas = [col[0] for col in cursor.description]
        fila = dict(zip(columnas, cursor.fetchone()))

    sensibles = {"token_id", "ip_hash", "captcha_proveedor", "captcha_score"}
    assert not sensibles & set(columnas)
    assert "hash_integridad" not in columnas
    assert fila["comprobante"] == respuesta.comprobante
    assert fila["cdi_id"] == centro.pk
    assert fila["sala_etiqueta"] == "Multiedad"
    assert fila["sala_origen_etiqueta"] == "Lista completa (CDI sin nómina activa)"
    assert fila["p13_alimentacion"] == 9
    assert fila["p13_alimentacion_etiqueta"] == "No brinda alimentación"
    assert fila["p01_informacion_avances_etiqueta"] == "Siempre"
    assert fila["canal_ingreso_etiqueta"] == "QR"
    assert fila["estado_registro_etiqueta"] == "Válido"
    assert fila["comentarios"] == "Muy contentos."
    # 15:00 UTC = 12:00 en Argentina.
    assert fila["fecha_carga"].replace(tzinfo=None) == datetime(2026, 11, 27, 12, 0)
