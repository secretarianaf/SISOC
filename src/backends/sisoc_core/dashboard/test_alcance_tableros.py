import pytest
from django.core.exceptions import ValidationError

from core.models import Provincia
from dashboard.models import (
    AudienciaTableros,
    MiembroAudienciaTableros,
    ConcesionTablero,
    Tablero,
)
from dashboard.services.alcance import alcance_efectivo


@pytest.mark.django_db
def test_union_de_concesiones_se_limita_al_tablero(django_user_model):
    user = django_user_model.objects.create_user(username="usuaria")
    otro = django_user_model.objects.create_user(username="otro")
    tablero = Tablero.objects.create(nombre="Uno", slug="uno")
    diferente = Tablero.objects.create(nombre="Dos", slug="dos")
    salta = Provincia.objects.create(nombre="Salta")
    jujuy = Provincia.objects.create(nombre="Jujuy")
    audiencia = AudienciaTableros.objects.create(nombre="Audiencia")
    MiembroAudienciaTableros.objects.create(audiencia=audiencia, usuario=user)
    ConcesionTablero.objects.create(
        tablero=tablero, usuario=user, tipo="provincia", provincia=salta
    )
    ConcesionTablero.objects.create(
        tablero=tablero, audiencia=audiencia, tipo="provincia", provincia=jujuy
    )
    ConcesionTablero.objects.create(
        tablero=tablero, audiencia=audiencia, tipo="cdi", cdi_id=9
    )
    ConcesionTablero.objects.create(tablero=diferente, usuario=user, tipo="nacional")
    alcance = alcance_efectivo(user, tablero, validar_cdis=lambda ids: ids)
    assert alcance.puede_ver is True
    assert alcance.nacional is False
    assert alcance.provincias == frozenset({salta.pk, jujuy.pk})
    assert alcance.cdis == frozenset({9})
    assert alcance_efectivo(user, diferente).nacional is True
    assert alcance_efectivo(otro, tablero).puede_ver is False
    assert not user.groups.exists()


@pytest.mark.django_db
def test_concesiones_invalidas_y_duplicadas_no_se_guardan(django_user_model):
    user = django_user_model.objects.create_user(username="usuaria")
    tablero = Tablero.objects.create(nombre="Uno", slug="uno")
    audiencia = AudienciaTableros.objects.create(nombre="Audiencia")
    with pytest.raises(ValidationError):
        ConcesionTablero.objects.create(
            tablero=tablero, usuario=user, audiencia=audiencia, tipo="nacional"
        )
    with pytest.raises(ValidationError):
        ConcesionTablero.objects.create(tablero=tablero, usuario=user, tipo="provincia")
    with pytest.raises(ValidationError):
        ConcesionTablero.objects.create(
            tablero=tablero, usuario=user, tipo="cdi", cdi_id=0
        )
    ConcesionTablero.objects.create(tablero=tablero, usuario=user, tipo="nacional")
    with pytest.raises(ValidationError):
        ConcesionTablero.objects.create(tablero=tablero, usuario=user, tipo="nacional")


@pytest.mark.django_db
def test_sin_acceso_para_usuarios_inactivos(django_user_model):
    user = django_user_model.objects.create_user(username="inactivo", is_active=False)
    tablero = Tablero.objects.create(nombre="Uno", slug="uno")
    ConcesionTablero.objects.create(tablero=tablero, usuario=user, tipo="nacional")
    assert alcance_efectivo(user, tablero).puede_ver is False


@pytest.mark.django_db
def test_revocar_una_concesion_conserva_las_demas(django_user_model):
    user = django_user_model.objects.create_user(username="usuaria")
    tablero = Tablero.objects.create(nombre="Uno", slug="uno")
    audiencia = AudienciaTableros.objects.create(nombre="Audiencia")
    MiembroAudienciaTableros.objects.create(audiencia=audiencia, usuario=user)
    directa = ConcesionTablero.objects.create(
        tablero=tablero, usuario=user, tipo="nacional"
    )
    ConcesionTablero.objects.create(
        tablero=tablero, audiencia=audiencia, tipo="cdi", cdi_id=9
    )
    directa.delete()
    alcance = alcance_efectivo(user, tablero, validar_cdis=lambda ids: ids)
    assert alcance.puede_ver and not alcance.nacional
    assert alcance.cdis == frozenset({9})
    tablero.activo = False
    tablero.save(update_fields=["activo"])
    assert not alcance_efectivo(user, tablero).puede_ver


@pytest.mark.django_db
def test_audita_membresias_y_concesiones_con_actor_y_rollback(django_user_model):
    from auditlog.context import set_actor
    from auditlog.models import LogEntry
    from django.contrib.contenttypes.models import ContentType
    from django.db import transaction

    actor = django_user_model.objects.create_user(username="actor")
    miembro = django_user_model.objects.create_user(username="miembro")
    tablero = Tablero.objects.create(nombre="Uno", slug="uno")
    audiencia = AudienciaTableros.objects.create(nombre="Audiencia")
    with set_actor(actor):
        membresia = MiembroAudienciaTableros.objects.create(
            audiencia=audiencia, usuario=miembro
        )
        concesion = ConcesionTablero.objects.create(
            tablero=tablero, audiencia=audiencia, tipo="nacional"
        )
    for obj in (membresia, concesion):
        tipo = ContentType.objects.get_for_model(obj)
        assert LogEntry.objects.filter(
            content_type=tipo,
            object_pk=str(obj.pk),
            actor=actor,
            action=LogEntry.Action.CREATE,
        ).exists()
    antes = LogEntry.objects.count()
    with pytest.raises(RuntimeError), transaction.atomic(), set_actor(actor):
        ConcesionTablero.objects.create(
            tablero=tablero, usuario=miembro, tipo="nacional"
        )
        raise RuntimeError("rollback")
    assert LogEntry.objects.count() == antes


@pytest.mark.django_db
def test_base_rechaza_cdi_sin_identificador_aun_si_se_omite_save(django_user_model):
    from django.db import IntegrityError, transaction

    user = django_user_model.objects.create_user(username="u")
    tablero = Tablero.objects.create(nombre="Uno", slug="uno")
    with pytest.raises(IntegrityError), transaction.atomic():
        ConcesionTablero.objects.bulk_create(
            [
                ConcesionTablero(
                    tablero=tablero, usuario=user, tipo="cdi", alcance_key="cdi:None"
                )
            ]
        )


@pytest.mark.django_db
def test_concesion_no_admite_guardado_parcial(django_user_model):
    user = django_user_model.objects.create_user(username="u")
    tablero = Tablero.objects.create(nombre="Uno", slug="uno")
    concesion = ConcesionTablero.objects.create(
        tablero=tablero, usuario=user, tipo="nacional"
    )
    concesion.tipo = "cdi"
    concesion.cdi_id = 8
    with pytest.raises(ValueError):
        concesion.save(update_fields=["tipo"])
    concesion.refresh_from_db()
    assert concesion.tipo == "nacional"
    assert concesion.alcance_key == "nacional"


@pytest.mark.django_db
def test_membresia_explicita_se_audita_y_no_expone_add_sin_auditoria(django_user_model):
    from auditlog.models import LogEntry
    from django.contrib.contenttypes.models import ContentType

    user = django_user_model.objects.create_user(username="miembro_auditado")
    audiencia = AudienciaTableros.objects.create(nombre="Grupo auditable")
    membresia = audiencia.agregar_miembro(user)
    assert audiencia.agregar_miembro(user).pk == membresia.pk
    assert not hasattr(audiencia, "miembros")
    assert LogEntry.objects.filter(
        content_type=ContentType.objects.get_for_model(membresia),
        object_pk=str(membresia.pk),
        action=LogEntry.Action.CREATE,
    ).exists()
    from auditlog.context import set_actor

    with set_actor(user):
        audiencia.quitar_miembro(user)
    assert LogEntry.objects.filter(
        content_type=ContentType.objects.get_for_model(membresia),
        object_pk=str(membresia.pk),
        action=LogEntry.Action.DELETE,
        actor=user,
    ).exists()


@pytest.mark.django_db
def test_base_impide_clave_alternativa_que_esconde_duplicado(django_user_model):
    from django.db import IntegrityError, transaction

    user = django_user_model.objects.create_user(username="miembro")
    tablero = Tablero.objects.create(nombre="Uno", slug="uno")
    concesion = ConcesionTablero.objects.create(
        tablero=tablero, usuario=user, tipo="nacional"
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        ConcesionTablero.objects.bulk_create(
            [
                ConcesionTablero(
                    tablero=tablero,
                    usuario=user,
                    tipo="nacional",
                    alcance_key="nacional-alternativo",
                )
            ]
        )
    concesion.delete()
    assert not alcance_efectivo(user, tablero).puede_ver


@pytest.mark.django_db
def test_cdi_no_confiable_no_concede_acceso(django_user_model):
    user = django_user_model.objects.create_user(username="miembro")
    tablero = Tablero.objects.create(nombre="Uno", slug="uno")
    ConcesionTablero.objects.create(
        tablero=tablero, usuario=user, tipo="cdi", cdi_id=999999
    )
    assert not alcance_efectivo(user, tablero).puede_ver
    assert not alcance_efectivo(
        user, tablero, validar_cdis=lambda _ids: set()
    ).puede_ver
    assert alcance_efectivo(
        user, tablero, validar_cdis=lambda ids: ids
    ).cdis == frozenset({999999})
    assert alcance_efectivo(
        user, tablero, validar_cdis=lambda _ids: {999999, 123456}
    ).cdis == frozenset({999999})


@pytest.mark.django_db
@pytest.mark.parametrize("tipo", ["provincia", "cdi"])
def test_base_impide_clave_alternativa_territorial(django_user_model, tipo):
    from django.db import IntegrityError, transaction

    user = django_user_model.objects.create_user(username="miembro_territorial")
    tablero = Tablero.objects.create(nombre="Uno", slug="uno")
    provincia = Provincia.objects.create(nombre="Salta")
    destino = {"provincia": provincia} if tipo == "provincia" else {"cdi_id": 9}
    with pytest.raises(IntegrityError), transaction.atomic():
        ConcesionTablero.objects.bulk_create(
            [
                ConcesionTablero(
                    tablero=tablero,
                    usuario=user,
                    tipo=tipo,
                    alcance_key="alternativa",
                    **destino,
                )
            ]
        )
