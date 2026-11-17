"""Pase automático a Pendiente al cumplir 4 años (#2925)."""

from datetime import date, timedelta

import pytest
from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django.urls import reverse
from django.utils import timezone

from centrodeinfancia.models import CentroDeInfancia, NominaCentroInfancia
from centrodeinfancia.services import (
    fecha_nacimiento_limite_nomina,
    pasar_nomina_a_pendiente_por_edad,
)
from ciudadanos.models import Ciudadano
from core.models import Provincia

HOY = date(2026, 11, 16)


def _ficha(centro, documento, nacimiento, *, en_ficha=True, **extra):
    ciudadano = Ciudadano.objects.create(
        apellido="Gómez",
        nombre=f"Niño {documento}",
        fecha_nacimiento=nacimiento,
        documento=documento,
    )
    extra.setdefault("estado", NominaCentroInfancia.ESTADO_ACTIVO)
    return NominaCentroInfancia.objects.create(
        centro=centro,
        ciudadano=ciudadano,
        fecha_nacimiento=nacimiento if en_ficha else None,
        **extra,
    )


def _estado(ficha):
    ficha.refresh_from_db()
    return ficha.estado


@pytest.fixture
def centro():
    provincia = Provincia.objects.create(nombre="Provincia Pase Edad")
    return CentroDeInfancia.objects.create(nombre="CDI Pase Edad", provincia=provincia)


@pytest.mark.parametrize(
    ("hoy", "limite"),
    [
        (date(2026, 11, 16), date(2022, 11, 16)),
        (date(2026, 3, 31), date(2022, 3, 31)),
        (date(2026, 1, 5), date(2022, 1, 5)),
        (date(2028, 2, 29), date(2024, 2, 29)),
    ],
)
def test_fecha_limite_es_el_cumpleanios_numero_4(hoy, limite):
    assert fecha_nacimiento_limite_nomina(hoy) == limite


@pytest.mark.django_db
def test_pasa_a_pendiente_desde_el_dia_que_cumple_4_anios(centro):
    cumple_hoy = _ficha(centro, 50000001, date(2022, 11, 16))
    cumple_manana = _ficha(centro, 50000002, date(2022, 11, 17))
    solo_ciudadano = _ficha(centro, 50000003, date(2021, 5, 2), en_ficha=False)
    de_baja = _ficha(
        centro, 50000004, date(2020, 1, 1), estado=NominaCentroInfancia.ESTADO_BAJA
    )

    actualizadas = pasar_nomina_a_pendiente_por_edad(hoy=HOY)

    assert actualizadas == 2
    assert _estado(cumple_hoy) == NominaCentroInfancia.ESTADO_PENDIENTE
    assert cumple_hoy.control_edad_maxima_en == HOY
    assert _estado(solo_ciudadano) == NominaCentroInfancia.ESTADO_PENDIENTE
    assert _estado(cumple_manana) == NominaCentroInfancia.ESTADO_ACTIVO
    assert cumple_manana.control_edad_maxima_en is None
    assert _estado(de_baja) == NominaCentroInfancia.ESTADO_BAJA


@pytest.mark.django_db
def test_respeta_la_reactivacion_de_un_administrador(centro):
    ficha = _ficha(centro, 50000011, date(2022, 11, 16))
    pasar_nomina_a_pendiente_por_edad(hoy=HOY)
    # Un Administrador la vuelve a Activo: la marca de control queda.
    NominaCentroInfancia.objects.filter(pk=ficha.pk).update(
        estado=NominaCentroInfancia.ESTADO_ACTIVO
    )

    actualizadas = pasar_nomina_a_pendiente_por_edad(hoy=HOY + timedelta(days=1))

    assert actualizadas == 0
    assert _estado(ficha) == NominaCentroInfancia.ESTADO_ACTIVO


@pytest.mark.django_db
def test_se_puede_acotar_a_un_centro_o_provincia(centro):
    otra_provincia = Provincia.objects.create(nombre="Otra Provincia Pase")
    otro_centro = CentroDeInfancia.objects.create(
        nombre="Otro CDI", provincia=otra_provincia
    )
    propia = _ficha(centro, 50000021, date(2020, 6, 1))
    ajena = _ficha(otro_centro, 50000022, date(2020, 6, 1))

    assert pasar_nomina_a_pendiente_por_edad(hoy=HOY, centro_id=centro.pk) == 1
    assert _estado(ajena) == NominaCentroInfancia.ESTADO_ACTIVO
    assert (
        pasar_nomina_a_pendiente_por_edad(hoy=HOY, provincia_id=otra_provincia.pk)
        == 1
    )
    assert _estado(propia) == NominaCentroInfancia.ESTADO_PENDIENTE
    assert _estado(ajena) == NominaCentroInfancia.ESTADO_PENDIENTE


@pytest.mark.django_db
def test_comando_aplica_el_pase_con_la_fecha_indicada(centro, capsys):
    ficha = _ficha(centro, 50000031, date(2022, 11, 16))

    call_command("pasar_nomina_cdi_a_pendiente_por_edad", "--fecha", "2026-11-15")
    assert _estado(ficha) == NominaCentroInfancia.ESTADO_ACTIVO

    call_command("pasar_nomina_cdi_a_pendiente_por_edad", "--fecha", "2026-11-16")
    assert _estado(ficha) == NominaCentroInfancia.ESTADO_PENDIENTE
    assert "Fichas pasadas a Pendiente por edad: 1" in capsys.readouterr().out


def test_comando_rechaza_fecha_invalida():
    with pytest.raises(CommandError, match="AAAA-MM-DD"):
        call_command("pasar_nomina_cdi_a_pendiente_por_edad", "--fecha", "16/11/2026")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_name",
    [
        "centrodeinfancia_detalle",
        "centrodeinfancia_nomina_ver",
        "centrodeinfancia_nomina_asistencia",
    ],
)
def test_pantallas_del_cdi_aplican_el_pase_al_consultar(client, centro, url_name):
    ficha = _ficha(
        centro, 50000041, fecha_nacimiento_limite_nomina(timezone.localdate())
    )
    client.force_login(
        User.objects.create_superuser(username=f"super-{url_name}", password="x")
    )

    response = client.get(reverse(url_name, kwargs={"pk": centro.pk}))

    assert response.status_code == 200
    assert _estado(ficha) == NominaCentroInfancia.ESTADO_PENDIENTE


@pytest.mark.django_db
def test_nomina_sin_sexo_cargado_muestra_guion(client, centro):
    """Antes daba error 500 si ni la ficha ni el ciudadano tenían sexo."""
    _ficha(centro, 50000061, date(2024, 3, 1))
    client.force_login(
        User.objects.create_superuser(username="super-nomina-sin-sexo", password="x")
    )

    response = client.get(
        reverse("centrodeinfancia_nomina_ver", kwargs={"pk": centro.pk})
    )

    assert response.status_code == 200
    assert "<td>-</td>" in response.content.decode("utf-8")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_name", ["centrodeinfancia_reportes", "centrodeinfancia_reportes_descargar"]
)
def test_reportes_aplican_el_pase_antes_de_contar(client, centro, url_name):
    ficha = _ficha(
        centro, 50000051, fecha_nacimiento_limite_nomina(timezone.localdate())
    )
    client.force_login(
        User.objects.create_superuser(username=f"super-{url_name}", password="x")
    )

    response = client.get(reverse(url_name))

    assert response.status_code == 200
    assert _estado(ficha) == NominaCentroInfancia.ESTADO_PENDIENTE
