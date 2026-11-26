"""Usuario revisor de estados de rendiciones (issue #2728, punto 1)."""

from datetime import date

import pytest
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from comedores.models import Comedor
from organizaciones.models import Organizacion, ProyectoOrganizacion
from rendicioncuentasmensual.models import (
    DocumentacionAdjunta,
    RendicionCuentaMensual,
)
from rendicioncuentasmensual.services import RendicionProcesoService

TERRITORIAL = RendicionCuentaMensual.ETAPA_REVISION_DOCUMENTACION
CARGA = RendicionCuentaMensual.ETAPA_REVISION_AUDITORIA
PENDIENTE = RendicionCuentaMensual.SUBESTADO_PENDIENTE
EN_CURSO = RendicionCuentaMensual.SUBESTADO_EN_CURSO
SUBSANADO = RendicionCuentaMensual.SUBESTADO_SUBSANADO
CORRECCIONES = RendicionCuentaMensual.SUBESTADO_PENDIENTE_CORRECCIONES


@pytest.fixture
def proyecto(db):
    organizacion = Organizacion.objects.create(nombre="Organizacion revisor")
    proyecto = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo="PROY-REV"
    )
    Comedor.objects.create(
        nombre="Comedor revisor", organizacion=organizacion, proyecto=proyecto
    )
    return proyecto


def _crear_rendicion(proyecto, etapa, subestado, *, numero=1, **extra):
    return RendicionCuentaMensual.objects.create(
        comedor=Comedor.objects.filter(proyecto=proyecto).first(),
        proyecto=proyecto,
        mes=numero,
        anio=2026,
        convenio="P01",
        numero_rendicion=numero,
        periodo_inicio=date(2026, numero, 1),
        periodo_fin=date(2026, numero, 28),
        estado=RendicionCuentaMensual.ESTADO_REVISION,
        etapa_proceso=etapa,
        subestado_proceso=subestado,
        **extra,
    )


def _usuario(django_user_model, username, *codenames):
    user = django_user_model.objects.create_user(username=username)
    group = Group.objects.create(name=f"Grupo {username}")
    group.permissions.add(
        *Permission.objects.filter(
            content_type__app_label="rendicioncuentasmensual",
            codename__in=codenames,
        )
    )
    user.groups.add(group)
    return user


def _detalle_url(rendicion):
    return reverse("rendicioncuentasmensual_detail", kwargs={"pk": rendicion.pk})


def test_destinos_excluyen_pendiente_de_correcciones_y_el_estado_actual(proyecto):
    rendicion = _crear_rendicion(proyecto, CARGA, EN_CURSO)

    destinos = RendicionProcesoService.estados_revision_disponibles(rendicion)

    assert destinos == [
        (f"{TERRITORIAL}:{PENDIENTE}", "Revisión Territorial pendiente"),
        (f"{TERRITORIAL}:{EN_CURSO}", "Revisión Territorial en curso"),
        (f"{TERRITORIAL}:{SUBSANADO}", "Revisión Territorial subsanado"),
        (f"{CARGA}:{PENDIENTE}", "Revisión para Carga pendiente"),
        (f"{CARGA}:{SUBSANADO}", "Revisión para Carga subsanado"),
    ]


@pytest.mark.parametrize(
    "etapa",
    [
        RendicionCuentaMensual.ETAPA_CARGA_DOCUMENTACION,
        RendicionCuentaMensual.ETAPA_AUDITORIA,
        RendicionCuentaMensual.ETAPA_REGULARIZACION,
    ],
)
def test_fuera_de_las_etapas_de_revision_no_hay_destinos_ni_cambio(proyecto, etapa):
    rendicion = _crear_rendicion(proyecto, etapa, PENDIENTE)

    assert RendicionProcesoService.estados_revision_disponibles(rendicion) == []
    with pytest.raises(ValidationError, match="Revisión Territorial o Revisión"):
        RendicionProcesoService.cambiar_estado_revision(
            rendicion=rendicion, etapa=TERRITORIAL, subestado=EN_CURSO
        )

    rendicion.refresh_from_db()
    assert rendicion.etapa_proceso == etapa
    assert rendicion.subestado_proceso == PENDIENTE


def test_retrotrae_de_revision_para_carga_a_territorial_en_curso(
    proyecto, django_user_model
):
    revisor = django_user_model.objects.create_user(username="revisor-servicio")
    rendicion = _crear_rendicion(
        proyecto, CARGA, EN_CURSO, fecha_validacion_territorial=timezone.now()
    )
    documento = DocumentacionAdjunta.objects.create(
        nombre="doc.pdf",
        archivo="doc.pdf",
        rendicion_cuenta_mensual=rendicion,
        visualizacion_etapa=CARGA,
        visualizacion_fecha=timezone.now(),
    )

    RendicionProcesoService.cambiar_estado_revision(
        rendicion=rendicion, etapa=TERRITORIAL, subestado=EN_CURSO, actor=revisor
    )

    rendicion.refresh_from_db()
    documento.refresh_from_db()
    assert rendicion.etapa_proceso == TERRITORIAL
    assert rendicion.subestado_proceso == EN_CURSO
    assert rendicion.estado_proceso_display == "Revisión Territorial en curso"
    assert rendicion.fecha_validacion_territorial is None
    assert rendicion.validacion_territorial_finalizada is False
    assert rendicion.usuario_ultima_modificacion == revisor
    # La confirmación de lectura es por etapa: se vuelve a pedir.
    assert documento.visualizacion_fecha is None


def test_sale_de_pendiente_de_correcciones_y_deja_la_rendicion_en_revision(proyecto):
    rendicion = _crear_rendicion(proyecto, TERRITORIAL, CORRECCIONES)
    rendicion.estado = RendicionCuentaMensual.ESTADO_SUBSANAR
    rendicion.save()

    RendicionProcesoService.cambiar_estado_revision(
        rendicion=rendicion, etapa=TERRITORIAL, subestado=EN_CURSO
    )

    rendicion.refresh_from_db()
    assert rendicion.subestado_proceso == EN_CURSO
    assert rendicion.estado == RendicionCuentaMensual.ESTADO_REVISION


def test_avanzar_a_revision_para_carga_registra_la_validacion_territorial(proyecto):
    rendicion = _crear_rendicion(proyecto, TERRITORIAL, EN_CURSO)

    RendicionProcesoService.cambiar_estado_revision(
        rendicion=rendicion, etapa=CARGA, subestado=PENDIENTE
    )

    rendicion.refresh_from_db()
    assert rendicion.estado_proceso_display == "Revisión para Carga pendiente"
    assert rendicion.fecha_validacion_territorial is not None


@pytest.mark.parametrize(
    ("etapa", "subestado", "mensaje"),
    [
        (TERRITORIAL, CORRECCIONES, "no es válido"),
        (RendicionCuentaMensual.ETAPA_AUDITORIA, PENDIENTE, "no es válido"),
        (CARGA, "inexistente", "no es válido"),
        (CARGA, EN_CURSO, "ya se encuentra"),
    ],
)
def test_rechaza_destinos_no_permitidos(proyecto, etapa, subestado, mensaje):
    rendicion = _crear_rendicion(proyecto, CARGA, EN_CURSO)

    with pytest.raises(ValidationError, match=mensaje):
        RendicionProcesoService.cambiar_estado_revision(
            rendicion=rendicion, etapa=etapa, subestado=subestado
        )

    rendicion.refresh_from_db()
    assert (rendicion.etapa_proceso, rendicion.subestado_proceso) == (CARGA, EN_CURSO)


def test_respeta_el_cupo_territorial_del_proyecto(proyecto):
    ocupa = _crear_rendicion(proyecto, TERRITORIAL, EN_CURSO)
    rendicion = _crear_rendicion(proyecto, CARGA, EN_CURSO, numero=2)

    with pytest.raises(ValidationError, match=f"#{ocupa.pk} del mismo proyecto"):
        RendicionProcesoService.cambiar_estado_revision(
            rendicion=rendicion, etapa=TERRITORIAL, subestado=EN_CURSO
        )
    # «Pendiente» no ocupa cupo: se puede retrotraer igual.
    RendicionProcesoService.cambiar_estado_revision(
        rendicion=rendicion, etapa=TERRITORIAL, subestado=PENDIENTE
    )

    rendicion.refresh_from_db()
    assert (rendicion.etapa_proceso, rendicion.subestado_proceso) == (
        TERRITORIAL,
        PENDIENTE,
    )


def test_el_selector_solo_se_muestra_con_el_permiso(
    client, django_user_model, proyecto
):
    rendicion = _crear_rendicion(proyecto, CARGA, EN_CURSO)
    sin_permiso = _usuario(
        django_user_model, "sin-permiso", "manage_auditoria_review_stage"
    )
    revisor = _usuario(
        django_user_model,
        "revisor",
        "view_rendicioncuentamensual",
        "change_review_stage_state",
    )

    client.force_login(sin_permiso)
    assert (
        'name="estado_revision"'
        not in client.get(_detalle_url(rendicion)).content.decode()
    )

    client.force_login(revisor)
    html = client.get(_detalle_url(rendicion)).content.decode()
    assert 'name="estado_revision"' in html
    assert "Revisión Territorial en curso" in html
    assert f'value="{TERRITORIAL}:{CORRECCIONES}"' not in html


def test_el_selector_no_aparece_en_auditoria(client, django_user_model, proyecto):
    rendicion = _crear_rendicion(
        proyecto, RendicionCuentaMensual.ETAPA_AUDITORIA, PENDIENTE
    )
    revisor = _usuario(
        django_user_model,
        "revisor-auditoria",
        "view_rendicioncuentamensual",
        "change_review_stage_state",
    )
    client.force_login(revisor)

    html = client.get(_detalle_url(rendicion)).content.decode()

    assert 'name="estado_revision"' not in html


def test_post_sin_permiso_devuelve_403_y_no_cambia_el_estado(
    client, django_user_model, proyecto
):
    rendicion = _crear_rendicion(proyecto, CARGA, EN_CURSO)
    client.force_login(
        _usuario(
            django_user_model,
            "etapas-sin-revisor",
            "manage_territorial_stage",
            "manage_auditoria_review_stage",
        )
    )

    response = client.post(
        _detalle_url(rendicion), {"estado_revision": f"{TERRITORIAL}:{EN_CURSO}"}
    )

    rendicion.refresh_from_db()
    assert response.status_code == 403
    assert (rendicion.etapa_proceso, rendicion.subestado_proceso) == (CARGA, EN_CURSO)


def test_post_del_revisor_habilita_la_gestion_de_la_etapa_destino(
    client, django_user_model, proyecto
):
    rendicion = _crear_rendicion(proyecto, CARGA, EN_CURSO)
    revisor = _usuario(
        django_user_model,
        "revisor-post",
        "view_rendicioncuentamensual",
        "change_review_stage_state",
    )
    territorial = _usuario(
        django_user_model, "territorial-post", "manage_territorial_stage"
    )
    client.force_login(revisor)

    response = client.post(
        _detalle_url(rendicion), {"estado_revision": f"{TERRITORIAL}:{EN_CURSO}"}
    )

    rendicion.refresh_from_db()
    assert response.status_code == 302
    assert (rendicion.etapa_proceso, rendicion.subestado_proceso) == (
        TERRITORIAL,
        EN_CURSO,
    )
    client.force_login(territorial)
    html = client.get(_detalle_url(rendicion)).content.decode()
    assert "Finalizar revisión territorial" in html
    assert "Finalizar revisión para Carga" not in html


def test_post_con_destino_invalido_informa_el_error_sin_cambiar(
    client, django_user_model, proyecto
):
    rendicion = _crear_rendicion(proyecto, CARGA, EN_CURSO)
    client.force_login(
        _usuario(
            django_user_model,
            "revisor-invalido",
            "view_rendicioncuentamensual",
            "change_review_stage_state",
        )
    )

    response = client.post(
        _detalle_url(rendicion),
        {"estado_revision": f"{TERRITORIAL}:{CORRECCIONES}"},
        follow=True,
    )

    rendicion.refresh_from_db()
    assert (rendicion.etapa_proceso, rendicion.subestado_proceso) == (CARGA, EN_CURSO)
    assert "El estado seleccionado no es válido." in response.content.decode()
