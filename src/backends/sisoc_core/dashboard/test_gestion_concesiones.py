"""Gestión aditiva y auditada de asignaciones individuales."""

import pytest
from unittest.mock import patch
from auditlog.context import set_actor
from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from core.models import Provincia
from dashboard.models import AudienciaTableros, ConcesionTablero, Tablero
from dashboard.services.gestion_concesiones import (
    agregar_concesiones,
    agregar_concesiones_audiencia,
    agregar_cdis_usuario,
    revocar_concesion,
    revocar_concesion_audiencia,
)

pytestmark = pytest.mark.django_db


def test_gestion_aditiva_y_revocacion_auditada(django_user_model):
    actor = django_user_model.objects.create_user(username="actor")
    usuario = django_user_model.objects.create_user(username="usuario")
    tablero = Tablero.objects.create(nombre="Tablero", slug="tablero")
    p1 = Provincia.objects.create(nombre="Salta")
    p2 = Provincia.objects.create(nombre="Jujuy")
    audiencia = AudienciaTableros.objects.create(nombre="Audiencia")
    grant_audiencia = ConcesionTablero.objects.create(
        tablero=tablero, audiencia=audiencia, tipo="nacional"
    )
    with set_actor(actor):
        agregar_concesiones(usuario, tablero, "provincia", [p1.pk, p2.pk])
        agregar_concesiones(usuario, tablero, "nacional", [])
        directa = ConcesionTablero.objects.get(usuario=usuario, tipo="nacional")
        revocar_concesion(usuario, tablero, directa.pk)
    assert set(
        ConcesionTablero.objects.filter(usuario=usuario).values_list(
            "provincia_id", flat=True
        )
    ) == {p1.pk, p2.pk}
    assert ConcesionTablero.objects.filter(pk=grant_audiencia.pk).exists()
    assert not usuario.groups.exists()
    tipo = ContentType.objects.get_for_model(ConcesionTablero)
    assert LogEntry.objects.filter(
        content_type=tipo,
        object_pk=str(directa.pk),
        actor=actor,
        action=LogEntry.Action.DELETE,
    ).exists()


def test_se_rechaza_lote_invalido_sin_cambios(django_user_model):
    usuario = django_user_model.objects.create_user(username="usuario")
    tablero = Tablero.objects.create(nombre="Tablero", slug="tablero")
    provincia = Provincia.objects.create(nombre="Salta")
    with pytest.raises(ValidationError):
        agregar_concesiones(usuario, tablero, "provincia", [provincia.pk, 999999])
    with pytest.raises(ValidationError):
        agregar_concesiones(usuario, tablero, "cdi", [1])
    assert not ConcesionTablero.objects.exists()


def test_duplicados_no_guardan_parcial_y_no_revocan_otro_usuario(django_user_model):
    usuario = django_user_model.objects.create_user(username="usuario")
    otro = django_user_model.objects.create_user(username="otro")
    tablero = Tablero.objects.create(nombre="Tablero", slug="tablero")
    p1 = Provincia.objects.create(nombre="Salta")
    p2 = Provincia.objects.create(nombre="Jujuy")
    agregar_concesiones(usuario, tablero, "provincia", [p2.pk])
    con_otra = ConcesionTablero.objects.create(
        tablero=tablero, usuario=otro, tipo="nacional"
    )
    antes = LogEntry.objects.count()
    with pytest.raises(ValidationError):
        agregar_concesiones(usuario, tablero, "provincia", [p1.pk, p2.pk])
    assert set(
        ConcesionTablero.objects.filter(usuario=usuario).values_list(
            "provincia_id", flat=True
        )
    ) == {p2.pk}
    assert LogEntry.objects.count() == antes
    with pytest.raises(ValidationError):
        revocar_concesion(usuario, tablero, con_otra.pk)
    assert ConcesionTablero.objects.filter(pk=con_otra.pk).exists()


def test_concesiones_audiencia_no_modifican_las_individuales(django_user_model):
    usuario = django_user_model.objects.create_user(username="usuario")
    tablero = Tablero.objects.create(nombre="Tablero", slug="tablero")
    provincia = Provincia.objects.create(nombre="Salta")
    audiencia = AudienciaTableros.objects.create(nombre="Audiencia")
    otra = AudienciaTableros.objects.create(nombre="Otra")
    personal = ConcesionTablero.objects.create(
        usuario=usuario, tablero=tablero, tipo="nacional"
    )
    agregar_concesiones_audiencia(audiencia, tablero, "provincia", [provincia.pk])
    grant = ConcesionTablero.objects.get(audiencia=audiencia, tablero=tablero)
    with pytest.raises(ValidationError):
        revocar_concesion_audiencia(otra, tablero, grant.pk)
    assert ConcesionTablero.objects.filter(pk=grant.pk).exists()
    revocar_concesion_audiencia(audiencia, tablero, grant.pk)
    assert not ConcesionTablero.objects.filter(pk=grant.pk).exists()
    assert ConcesionTablero.objects.filter(pk=personal.pk).exists()


def test_lote_audiencia_duplicado_revierte_tambien_auditoria(django_user_model):
    actor = django_user_model.objects.create_user(username="actor")
    audiencia = AudienciaTableros.objects.create(nombre="Audiencia")
    tablero = Tablero.objects.create(nombre="Tablero", slug="tablero")
    primera = Provincia.objects.create(nombre="Primera")
    segunda = Provincia.objects.create(nombre="Segunda")
    with set_actor(actor):
        agregar_concesiones_audiencia(audiencia, tablero, "provincia", [segunda.pk])
    antes = LogEntry.objects.count()
    with pytest.raises(ValidationError), set_actor(actor):
        agregar_concesiones_audiencia(
            audiencia, tablero, "provincia", [primera.pk, segunda.pk]
        )
    assert list(
        ConcesionTablero.objects.filter(audiencia=audiencia).values_list(
            "provincia_id", flat=True
        )
    ) == [segunda.pk]
    assert LogEntry.objects.count() == antes


def test_cdi_requiere_validacion_completa_y_no_guarda_si_falla(django_user_model):
    usuario = django_user_model.objects.create_user(username="usuario")
    tablero = Tablero.objects.create(nombre="Tablero", slug="tablero")
    request = object()
    with patch(
        "dashboard.services.gestion_concesiones.validar_centros",
        side_effect=ValidationError("CDI no disponible"),
    ):
        with pytest.raises(ValidationError):
            agregar_cdis_usuario(request, usuario, tablero, [1, 2])
    assert not ConcesionTablero.objects.exists()
    with patch(
        "dashboard.services.gestion_concesiones.validar_centros",
        return_value=frozenset({1, 2}),
    ):
        agregar_cdis_usuario(request, usuario, tablero, [1, 2])
    assert set(
        ConcesionTablero.objects.filter(usuario=usuario).values_list(
            "cdi_id", flat=True
        )
    ) == {1, 2}
